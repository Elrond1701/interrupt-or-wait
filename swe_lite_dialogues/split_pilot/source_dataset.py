"""Small source-to-dataset workflow with explicit review boundaries.

extract -> contract review -> balanced generation -> wording review -> export.
Extraction reads the source issue and optionally a reviewed endpoint and scope
hints. Gold/tests stay in author-side exports, never in construction prompts.
This development adapter does not claim Docker or intermediate test validation.
"""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from balanced_generation import inventory, quotas
from dialogue_options import build_menu
from benchmark_data import candidate_from_run, load_candidates, write_jsonl
from model_pilot import ROOT, digest, encoded, read_json, save, schema_check
from pipeline import test_names
from planned_generation import (REVIEW_CHECKS, assemble, call_json, validate_plan,
                                wording_context)
from stage_plan_options import enumerate_options, selection_schema
from trajectory_labels import TYPES, distribution, label_record

CONTRACT_CHECKS = ("source_requirements_complete", "requirements_are_separable",
                   "compiled_goal_matches_source", "temporary_target_plausible",
                   "official_test_alignment_checked", "no_unresolved_test_conflict")
PROGRESSIVE_CHECKS = ("public_context_has_no_future_answer", "clarification_questions_are_meaningful")
REFINEMENT_CHECKS = ("partial_goal_entailed_by_final", "refinement_adds_meaningful_information")


def object_schema(properties):
    return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}


def contract_schema(version="1", three_first=False, allow_refinement=False):
    text = {"type": "string", "minLength": 1, "maxLength": 1800}
    rid = {"type": "string", "enum": ["r1", "r2", "r3", "r4"]}
    schema = object_schema({
        "decision": {"type": "string", "enum": ["propose_contract", "defer"]},
        "reason": text, "context_en": {"type": "string", "maxLength": 600},
        "final_summary_en": {"type": "string", "maxLength": 2400},
        "requirements": {"type": "array", "maxItems": 4, "items": object_schema({
            "id": rid, "text_en": text, "source_quote": text})},
        "temporary_requirements": {"type": "array", "maxItems": 1, "items": object_schema({
            "id": {"type": "string", "enum": ["t1"]}, "text_en": text,
            "replaced_by": {"type": "array", "minItems": 1, "maxItems": 4, "items": rid},
            "rationale": text})}})
    if version == "2":
        schema["properties"].update({
            "schema_version": {"type": "string", "enum": ["2"]},
            "dialogue_assessment": object_schema({
                "three_messages": {"type": "string", "enum": ["natural", "not_natural"]}, "reason": text}),
            "clarifications": {"type": "array", "maxItems": 2, "items": object_schema({
                "id": {"type": "string", "enum": ["c1", "c2"]}, "question_en": text,
                "resolves_to": {"type": "array", "minItems": 1, "maxItems": 4, "items": rid}})}})
        schema["required"] = list(schema["properties"])
    elif version != "1":
        raise ValueError("Unsupported source contract version")
    if three_first:
        if version != "2":
            raise ValueError("Three-first design requires a progressive contract")
        update_ids = {"type": "array", "maxItems": 4, "items": {"type": "string", "enum": ["r1", "r2", "r3", "r4", "t1"]}}
        # New extra evidence is opt-in by field presence when replaying old runs.
        # Emit actual atoms/questions before judging update capacity. Earlier
        # design-first drafts contained phantom IDs and premature commitments.
        assessment = schema["properties"].pop("dialogue_assessment")
        schema["properties"]["dialogue_assessment"] = assessment
        schema["properties"]["length_design"] = object_schema({
            "route": {"type": "string", "enum": ["separate_scopes", "clarify_then_revise", "two_message_fallback"]},
            "u1_adds": update_ids, "u2_adds": update_ids,
            "scope_route_reason": text, "revision_route_reason": text,
        })
        schema["required"] = list(schema["properties"])
    if allow_refinement:
        if not three_first:
            raise ValueError("Refinement requires a length design")
        schema["properties"]["length_design"]["properties"]["route"]["enum"].append("progressive_refinement")
        schema["properties"]["refinement_evidence"] = {"type": "array", "maxItems": 1, "items": object_schema({
            "temporary_id": {"type": "string", "enum": ["t1"]},
            "source_quote": text, "detail_added_at_u2": text})}
        schema["required"] = list(schema["properties"])
    return schema


def rows_by_id():
    return {r["instance_id"]: r for r in read_json(ROOT / "data/lite_snapshot.json.gz")["instances"]}


def validate_contract(draft, row):
    schema_check(draft, contract_schema(draft.get("schema_version", "1"), "length_design" in draft,
                                        "refinement_evidence" in draft))
    if draft["decision"] == "defer":
        if draft["requirements"] or draft["temporary_requirements"] or draft.get("clarifications") or draft.get("refinement_evidence"):
            raise ValueError("Deferred contract must not contain requirements")
        design = draft.get("length_design")
        if design and (design["route"] != "two_message_fallback" or design["u1_adds"] or design["u2_adds"]):
            raise ValueError("Deferred contract cannot claim an update design")
        return
    requirements = draft["requirements"]
    if not 1 <= len(requirements) <= 4 or [r["id"] for r in requirements] != ["r" + str(i + 1) for i in range(len(requirements))]:
        raise ValueError("Expected 1-4 ordered source requirements")
    if not draft["context_en"].strip() or not draft["final_summary_en"].strip():
        raise ValueError("Missing task context or final summary")
    for requirement in requirements:
        if requirement["source_quote"] not in row["problem_statement"]:
            raise ValueError("Requirement quote does not occur in the source issue")
    ids = {r["id"] for r in requirements}
    dimensions, assigned = draft.get("clarifications", []), set()
    if [d["id"] for d in dimensions] != ["c" + str(i + 1) for i in range(len(dimensions))]:
        raise ValueError("Expected ordered clarification IDs")
    for dimension in dimensions:
        targets = dimension["resolves_to"]
        if len(set(targets)) != len(targets) or not set(targets) <= ids or assigned & set(targets):
            raise ValueError("Clarification targets must be distinct, disjoint source requirements")
        assigned.update(targets)
    for temporary in draft["temporary_requirements"]:
        replacements = temporary["replaced_by"]
        if len(set(replacements)) != len(replacements) or not set(replacements) <= ids:
            raise ValueError("Invalid temporary replacement IDs")
    if "length_design" in draft:
        validate_length_design(draft)
    evidence = draft.get("refinement_evidence", [])
    refining = draft.get("length_design", {}).get("route") == "progressive_refinement"
    if bool(evidence) != refining:
        raise ValueError("Refinement evidence must match the selected route")
    for item in evidence:
        if item["source_quote"] not in row["problem_statement"]:
            raise ValueError("Refinement quote does not occur in the source issue")
        partial = draft["temporary_requirements"][0]
        if partial["id"] != item["temporary_id"] or partial["text_en"] in [r["text_en"] for r in requirements]:
            raise ValueError("Refinement must identify a partial, not identical, requirement")


def validate_length_design(draft):
    """Check claimed update capacity, not naturalness or semantic equivalence."""
    design = draft["length_design"]
    first, second = design["u1_adds"], design["u2_adds"]
    ids = {r["id"] for r in draft["requirements"]}
    if any(len(v) != len(set(v)) for v in (first, second)) or not first:
        raise ValueError("Length design needs distinct nonempty U1 additions")
    route = design["route"]
    if route == "separate_scopes":
        valid = bool(second) and set(first + second) <= ids and not set(first) & set(second)
    elif route in ("clarify_then_revise", "progressive_refinement"):
        temporary = draft["temporary_requirements"]
        valid = (first == ["t1"] and len(temporary) == 1
                 and set(second) == set(temporary[0]["replaced_by"])
                 and any(set(c["resolves_to"]) == set(second) for c in draft["clarifications"]))
    else:
        valid = not second and set(first) <= ids
    expected = "not_natural" if route == "two_message_fallback" else "natural"
    if not valid or draft["dialogue_assessment"]["three_messages"] != expected:
        raise ValueError("Length design does not support its claimed updates")


def snapshot(folder):
    files = ["source_dataset.py", "dialogue_options.py", "progressive_stages.py", "balanced_generation.py", "balance_config.json", "planned_generation.py",
             "stage_plan_options.py", "trajectory_labels.py", "multistage_trajectory.py", "codex_pilot.py",
             "codex_config.json", "phrasing_schema_v6.json", "prompts/extract_contract_v1.4.txt",
             "prompts/select_stage_plan_v2.txt", "prompts/propose_trajectory_v6.1.txt",
             "prompts/extract_contract_v2.3.txt", "prompts/extract_contract_v2.4.txt", "prompts/extract_contract_v2.5.txt",
             "prompts/adapt_three_messages_v1.txt", "prompts/partition_reviewed_scopes_v1.txt",
             "prompts/select_stage_plan_v3.txt", "prompts/select_stage_plan_v4.txt", "prompts/propose_trajectory_v7.txt",
             "prompts/propose_trajectory_v8.txt", "prompts/three_first_design_v1.txt",
             "prompts/three_first_design_v1.1.txt", "prompts/select_stage_plan_v5.txt",
             "prompts/three_first_design_v1.2.txt", "prompts/three_first_design_v1.3.txt",
             "prompts/refine_goal_v1.txt", "prompts/refine_goal_v1.1.txt",
             "prompts/select_stage_plan_v6.txt", "prompts/propose_trajectory_v9.txt",
             "prompts/extract_category_v1.txt", "prompts/extract_category_v2.txt", "prompts/extract_category_v3.txt",
             "prompts/propose_trajectory_v10.txt", "prompts/extract_endpoint_v1.txt"]
    hashes = {}
    for name in files:
        source = ROOT / name
        dest = folder / "inputs" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())
        hashes[name] = digest(source)
    save(folder / "manifest.json", {"input_hashes": hashes, "snapshot_sha256": digest(ROOT / "data/lite_snapshot.json.gz"),
                                   "visibility": "author_only", "experiment_ready": False})


def extraction_source(row, seed_folder=None, partition_scopes=False, scope_hints=None):
    source = {"repo": row["repo"], "problem_statement": row["problem_statement"]}
    if scope_hints is not None and (not partition_scopes or not isinstance(scope_hints, list)
            or not 2 <= len(scope_hints) <= 4
            or any(not isinstance(s, str) or not s.strip() or len(s) > 400 for s in scope_hints)):
        raise ValueError("Use 2-4 short scope hints only with reviewed scope partitioning")
    if seed_folder is None:
        if partition_scopes:
            raise ValueError("Scope partitioning requires a reviewed seed contract")
        return source, None
    seed_folder = Path(seed_folder).resolve()
    if not seed_folder.is_relative_to(ROOT / "source_runs") or (seed_folder / "seed_link.json").exists():
        raise ValueError("Use an original reviewed extraction as seed; no chained adaptations")
    seed_row, seed, _ = reviewed_contract(seed_folder)
    if seed_row != row:
        raise ValueError("Seed must belong to the same original task")
    # Only issue-derived requirements/preferences enter the model, never tests,
    # patches, test mappings, review conclusions or author filesystem paths.
    source.update(reviewed_final_requirements=seed["requirements"],
                  optional_earlier_preferences=seed["temporary_requirements"])
    link = {"directory": str(seed_folder.relative_to(ROOT)),
            "contract_sha256": digest(seed_folder / "contract.json"),
            "review_sha256": digest(seed_folder / "contract_review.json")}
    if partition_scopes:
        link["mode"] = "scope_partition"
    if scope_hints is not None:
        source["scope_hints"] = list(scope_hints)
        link["scope_hints"] = list(scope_hints)
    return source, link


def category_instructions(preferred_type, prompt):
    if preferred_type not in TYPES:
        raise ValueError("Unknown preferred trajectory type")
    return "Preferred trajectory type for this attempt: " + preferred_type + ".\n\n" + prompt


def extract(row, folder, live=False, provider=call_json, seed_folder=None, partition_scopes=False, scope_hints=None,
            allow_refinement=False, preferred_type=None, endpoint_only=False, category_prompt_version="1"):
    if category_prompt_version not in ("1", "2", "3") or (category_prompt_version != "1" and preferred_type is None):
        raise ValueError("Category prompt version requires a supported explicit category preference")
    if endpoint_only and (seed_folder or partition_scopes or preferred_type or allow_refinement):
        raise ValueError("Endpoint-only extraction has no category, seed, partition or refinement preference")
    if allow_refinement and partition_scopes:
        raise ValueError("Use refinement or scope partitioning, not both in one attempt")
    if preferred_type is not None and (preferred_type not in TYPES or partition_scopes):
        raise ValueError("Use a known preferred type without scope partitioning")
    source, seed_link = extraction_source(row, seed_folder, partition_scopes, scope_hints)
    folder.mkdir(parents=True, exist_ok=False)
    snapshot(folder)
    save(folder / "source.json", row)
    if seed_link:
        save(folder / "seed_link.json", seed_link)
    if preferred_type is not None:
        save(folder / "category_policy.json", {"version": "category_v" + category_prompt_version, "preferred_type": preferred_type})
    if endpoint_only:
        save(folder / "endpoint_only.json", {"purpose": "reviewed_seed_not_a_dialogue"})
    save(folder / "extraction_input.json", source)
    save(folder / "status.json", {"status": "dry_run", "model_calls": 0})
    if not live:
        return
    try:
        prompt = "adapt_three_messages_v1.txt" if seed_link else "extract_contract_v2.5.txt"
        if partition_scopes:
            prompt = "partition_reviewed_scopes_v1.txt"
        instructions = (ROOT / "prompts/three_first_design_v1.3.txt").read_text() + "\n\n" + (ROOT / "prompts" / prompt).read_text()
        if allow_refinement:
            instructions = (ROOT / "prompts/refine_goal_v1.1.txt").read_text()
        if preferred_type is not None:
            instructions = category_instructions(preferred_type, (ROOT / ("prompts/extract_category_v" + category_prompt_version + ".txt")).read_text())
        if endpoint_only:
            instructions = (ROOT / "prompts/extract_endpoint_v1.txt").read_text()
        draft = provider(source, instructions, contract_schema("2", three_first=True, allow_refinement=allow_refinement), folder / "extraction")
        save(folder / "contract.json", draft)
        validate_contract(draft, row)
        if endpoint_only and (draft["temporary_requirements"] or draft.get("clarifications")):
            raise ValueError("Endpoint-only extraction must not design temporary policies or questions")
        if seed_link and not partition_scopes and draft["decision"] == "propose_contract" and draft["requirements"] != source["reviewed_final_requirements"]:
            raise ValueError("Adaptation changed the locked final requirements")
        save(folder / "status.json", {"status": "deferred_by_model" if draft["decision"] == "defer" else "contract_requires_review",
                                       "model_calls": 1})
    except Exception as exc:
        save(folder / "status.json", {"status": "failed_or_rejected", "model_calls_attempted": 1, "error": str(exc)})
        raise


def check_review(path, bindings, required):
    review = read_json(path)
    if review.get("verdict") != "accept_for_development" or not review.get("reviewer"):
        raise ValueError("An accepting development review is required")
    if not all(review.get("checks", {}).get(k) is True for k in required):
        raise ValueError("Review has incomplete checks")
    if any(review.get(key) != digest(file) for key, file in bindings.items()):
        raise ValueError("Review does not match current artifacts")
    return review


def reviewed_contract(folder):
    row, draft = read_json(folder / "source.json"), read_json(folder / "contract.json")
    if rows_by_id().get(row["instance_id"]) != row:
        raise ValueError("Source differs from the pinned original row")
    if draft["decision"] != "propose_contract":
        raise ValueError("No proposed contract")
    if draft != read_json(folder / "extraction/answer.json"):
        raise ValueError("Extracted contract was edited; use a separately versioned correction workflow")
    bindings = {"contract_sha256": folder / "contract.json", "source_sha256": folder / "source.json"}
    if ("endpoint_only_sha256" in read_json(folder / "contract_review.json")) != (folder / "endpoint_only.json").exists():
        raise ValueError("Endpoint-only marker is missing or not bound to its review")
    if (folder / "endpoint_only.json").exists():
        if read_json(folder / "endpoint_only.json") != {"purpose": "reviewed_seed_not_a_dialogue"}:
            raise ValueError("Invalid endpoint-only marker")
        if draft["temporary_requirements"] or draft.get("clarifications"):
            raise ValueError("Endpoint-only contract contains dialogue policy")
        if read_json(folder / "extraction/request.json")["developer_instructions"] != (folder / "inputs/prompts/extract_endpoint_v1.txt").read_text():
            raise ValueError("Endpoint-only prompt differs from its saved request")
        bindings["endpoint_only_sha256"] = folder / "endpoint_only.json"
    if ("category_policy_sha256" in read_json(folder / "contract_review.json")) != (folder / "category_policy.json").exists():
        raise ValueError("Category policy is missing or not bound to its review")
    if (folder / "category_policy.json").exists():
        policy = read_json(folder / "category_policy.json")
        if set(policy) != {"version", "preferred_type"} or policy["version"] not in ("category_v1", "category_v2", "category_v3"):
            raise ValueError("Invalid extraction category policy")
        prompt_name = "extract_" + policy["version"] + ".txt"
        expected_prompt = category_instructions(policy["preferred_type"], (folder / "inputs/prompts" / prompt_name).read_text())
        if read_json(folder / "extraction/request.json")["developer_instructions"] != expected_prompt:
            raise ValueError("Category policy differs from the saved model request")
        bindings["category_policy_sha256"] = folder / "category_policy.json"
    review = check_review(folder / "contract_review.json", bindings,
        CONTRACT_CHECKS + (PROGRESSIVE_CHECKS if draft.get("schema_version") == "2" else ())
        + (REFINEMENT_CHECKS if draft.get("refinement_evidence") else ()))
    # An author may repair a citation without rewriting the model's task.
    # Keep the raw answer intact and bind the correction to the saved review.
    corrections = review.get("source_quote_corrections", {})
    if not isinstance(corrections, dict) or not set(corrections) <= {r["id"] for r in draft["requirements"]}:
        raise ValueError("Quote corrections must name existing requirement IDs")
    draft = deepcopy(draft)
    for requirement in draft["requirements"]:
        if requirement["id"] in corrections:
            requirement["source_quote"] = corrections[requirement["id"]]
    validate_contract(draft, row)
    if (folder / "seed_link.json").exists():
        link = read_json(folder / "seed_link.json")
        partition = link.get("mode") == "scope_partition"
        source, expected_link = extraction_source(row, ROOT / link["directory"], partition, link.get("scope_hints"))
        if link != expected_link or read_json(folder / "extraction_input.json") != source or read_json(folder / "extraction/request.json")["input"] != source:
            raise ValueError("Adaptation seed or input changed")
        if partition:
            # ID coverage is mechanical; behavioral equivalence remains an
            # explicit, hash-bound semantic review, never an automatic proof.
            mapping = review.get("scope_partition_mapping", {})
            parents = {r["id"] for r in source["reviewed_final_requirements"]}
            children = {r["id"] for r in draft["requirements"]}
            if (review.get("checks", {}).get("scope_partition_preserves_complete_endpoint") is not True
                    or not review.get("scope_partition_explanation", "").strip()
                    or set(mapping) != children
                    or any(not isinstance(ids, list) or not ids or len(ids) != len(set(ids))
                           or not set(ids) <= parents for ids in mapping.values())
                    or set().union(*(set(ids) for ids in mapping.values())) != parents):
                raise ValueError("Scope partition needs complete parent mapping and endpoint-equivalence review")
        elif draft["requirements"] != source["reviewed_final_requirements"]:
            raise ValueError("Adaptation changed the locked final requirements")
    mapping = review.get("official_test_mapping", {})
    if set(mapping) != {r["id"] for r in draft["requirements"]} or any(
            not isinstance(names, list) or not names or not set(names) <= set(test_names(row, "FAIL_TO_PASS")) for names in mapping.values()):
        raise ValueError("Each source requirement needs a reviewed original target-test mapping")
    if set().union(*(set(names) for names in mapping.values())) != set(test_names(row, "FAIL_TO_PASS")):
        raise ValueError("Original target tests remain unmapped; review the source/evaluator mismatch")
    return row, draft, review


def context_for(row, draft, kind, length, rendering_version=None):
    if rendering_version not in (None, "2", "3") or (rendering_version and draft.get("schema_version") != "2"):
        raise ValueError("Unsupported source rendering version")
    invariant = {"id": "preserve_unrelated", "text_en": "Preserve existing behavior outside the changes currently requested."}
    temporary = [{k: t[k] for k in ("id", "text_en", "replaced_by")} for t in draft["temporary_requirements"]]
    # Compile the released endpoint from the reviewed atoms, not the model's
    # separate summary, which may omit an atom or refer to an unseen issue.
    final_summary = "Update the supplied " + row["repo"] + " repository to meet these requirements:\n"
    final_summary += "\n".join("- " + r["text_en"] for r in draft["requirements"])
    final_summary += "\nPreserve unrelated existing behavior."
    context = {"repo": row["repo"], "context_en": "Work in the supplied " + row["repo"] + " repository.",
            "final_requirements": [{"id": r["id"], "text_en": r["text_en"]} for r in draft["requirements"]] + [invariant],
            "temporary_requirements": temporary,
            "uncertainty_choices": {"temporary_scope": [[temporary[0]["id"]], temporary[0]["replaced_by"]]} if temporary else {},
            "final_summary_en": final_summary,
            "invariant_ids": [invariant["id"]], "requested_trajectory_type": kind, "n_messages": length}
    if draft.get("schema_version") == "2":
        context.update(planning_version="2", context_en=context["context_en"] + " " + draft["context_en"],
                       clarification_questions={d["id"]: d["question_en"] for d in draft["clarifications"]})
        if rendering_version in ("2", "3"):
            # This invariant is already active in every legal U0. Render it
            # deterministically; never pull future source atoms into the prefix.
            context["rendering_version"] = rendering_version
            context["context_en"] += "\n" + invariant["text_en"]
        if rendering_version == "3":
            # Category-guided drafts may start with a definite temporary policy.
            # An empty question list must not create a legacy implicit question.
            context["uncertainty_choices"] = {}
        if draft["clarifications"]:
            context["uncertainty_choices"] = {}
            for dimension in draft["clarifications"]:
                choices = [dimension["resolves_to"]]
                choices += [[t["id"]] for t in temporary if set(t["replaced_by"]) == set(dimension["resolves_to"])]
                context["uncertainty_choices"][dimension["id"]] = choices
        if draft.get("refinement_evidence"):
            context["refinement_ids"] = [e["temporary_id"] for e in draft["refinement_evidence"]]
    return context


def choose_context(row, draft, records, total, config, requested_type=None, requested_length=None, rendering_version=None):
    # Quotas count the selected original tasks, not all development variants.
    records, _ = select_primary(records)
    targets, current = quotas(total, config), inventory(records)
    counts = current["counted_original_class_pairs"]
    existing = current["existing_classes_by_original"].get(row["instance_id"], [])
    report = {"targets": targets, "counts": counts, "selected": None, "skipped": []}
    if existing:
        report["status"] = "need_other_original_source_limit"
        return None, [], report
    kinds = sorted(TYPES, key=lambda k: (-(targets[k] - counts[k]) / targets[k], -(targets[k] - counts[k]), TYPES.index(k)))
    if draft.get("schema_version") == "2":
        # Class targets rank attempts; they must not hide a natural U2 plan
        # merely because its class has already reached a development target.
        kinds = [k for k in kinds if not requested_type or k == requested_type]
        # The extraction assessment is advice, not a hard early rejection.
        # Check actual update capacity; the selector can still prefer two.
        lengths = [3, 2]
        if requested_length:
            lengths = [n for n in lengths if n == requested_length]
        elif "length_design" in draft:
            # A reviewed upfront design commits this attempt to three. Do not
            # let a later selector shorten it solely for concision. Explicit
            # fallback contracts (or a separately requested retry) use two.
            lengths = [2] if draft["length_design"]["route"] == "two_message_fallback" else [3]
        options, feasibility = build_menu(lambda k, n: context_for(row, draft, k, n, rendering_version), kinds, lengths)
        report.update(menu_types=kinds, menu_lengths=lengths, feasibility=feasibility,
                      quota_policy="soft_class_preference_not_a_cap",
                      upfront_assessment=draft["dialogue_assessment"],
                      length_preference="Prefer a natural three-message plan; retain two-message fallbacks in the same model call.")
        if "length_design" in draft:
            report.update(length_policy="upfront_three_first_v1",
                          length_preference="Use the reviewed upfront length; explicit two-message fallback or override is allowed. Selector can defer an incoherent plan.")
        if options:
            first = options[0]
            report.update(status="menu_requires_naturalness_selection",
                          selected={"trajectory_type": first["trajectory_type"], "n_messages": first["n_messages"]})
            return context_for(row, draft, first["trajectory_type"], first["n_messages"], rendering_version), options, report
        report["status"] = "no_eligible_plan_keep_deficits"
        return None, [], report
    for kind in kinds:
        if kind in existing or counts[kind] >= targets[kind] or (requested_type and kind != requested_type):
            continue
        # Three explicit scopes can support U2 without adding a recap-only turn.
        lengths = [3, 2] if len(draft["requirements"]) >= 3 else [2, 3]
        for length in ([requested_length] if requested_length else lengths):
            if kind == "mixed" and length == 2:
                continue
            context = context_for(row, draft, kind, length)
            options = enumerate_options(context, validate_plan)
            if options:
                report.update(status="one_attempt_selected", selected={"trajectory_type": kind, "n_messages": length})
                return context, options, report
            report["skipped"].append({"trajectory_type": kind, "n_messages": length, "reason": "no_legal_plan"})
    report["status"] = "no_eligible_plan_keep_deficits"
    return None, [], report


def stage_test_plan(trace, mapping, refinement_ids=()):
    by_test = {}
    for requirement, names in mapping.items():
        for name in names:
            by_test.setdefault(name, set()).add(requirement)
    result = []
    for state in trace:
        active = set(state["active_ids"])
        temporary = active - set(mapping) - {"preserve_unrelated"}
        # A combined test cannot be assigned early if it covers future atoms.
        # Temporary targets need their own checks, not the final original oracle.
        eligible = sorted(name for name, requirements in by_test.items() if requirements <= active and not temporary)
        result.append({"stage_id": state["id"], "active_source_requirement_ids": sorted(active & set(mapping)),
                       "active_temporary_ids": sorted(temporary), "unresolved": state["unresolved"],
                       "original_target_test_candidates": eligible,
                       "status": "custom_checks_needed" if temporary else "mapped_not_executed",
                       "note": "Test-code mapping only; intermediate/regression validation is still required."})
        if refinement_ids:
            partial = temporary & set(refinement_ids)
            result[-1].update(active_partial_requirement_ids=sorted(partial),
                              active_temporary_ids=sorted(temporary - partial))
            if partial:
                result[-1].update(status="partial_goal_checks_needed",
                                 note="A weaker compatible goal is active; final tests may require unreleased details. Stage checks are not implemented.")
    return result


def candidate(wording, context, validated, row, folder, contract_folder):
    rendered = deepcopy(wording)
    progressive = context.get("planning_version") == "2"
    if progressive and rendered["decision"] == "propose_split" and rendered["messages"]:
        rendered["messages"][0]["content"] = context["context_en"] + "\n\n" + rendered["messages"][0]["content"]
    result = assemble(rendered, context, validated, row, str(folder.relative_to(ROOT)))
    if result is None:
        return None
    result["scenario_id"] = result["scenario_id"].replace(".planned.v1.", ".source.v1.")
    result["provenance"].update(final_contract_origin="issue_only_model_extraction_with_author_review",
                                 final_summary_origin="compiled_from_reviewed_requirement_text",
                                 contract_run=str(contract_folder.relative_to(ROOT)),
                                 contract_sha256=digest(contract_folder / "contract.json"),
                                 contract_review_sha256=digest(contract_folder / "contract_review.json"))
    review = read_json(contract_folder / "contract_review.json")
    if review.get("source_quote_corrections"):
        result["provenance"]["source_quote_correction_count"] = len(review["source_quote_corrections"])
    result["evaluation"]["requirement_to_original_tests"] = review["official_test_mapping"]
    result["evaluation"]["mapping_status"] = "author_inspected_test_code_not_executed"
    result["evaluation"]["stage_test_plan"] = stage_test_plan(validated["state_trace"], review["official_test_mapping"], context.get("refinement_ids", []))
    if context.get("refinement_ids"):
        result["provenance"]["dialogue_mechanism"] = "progressive_refinement"
    if progressive:
        result["provenance"]["initial_context_origin"] = "program_prepended_reviewed_model_context"
        result["provenance"]["dialogue_contract_version"] = "2"
        if context.get("rendering_version") in ("2", "3"):
            result["provenance"].update(rendering_version=context["rendering_version"], initial_invariant_origin="program_rendered_active_preserve_unrelated")
        initial = result["evaluation"]["stage_test_plan"][0]
        if (not initial["active_source_requirement_ids"] and not initial["active_temporary_ids"]
                and not initial.get("active_partial_requirement_ids")):
            initial.update(status="intent_only_no_behavioral_gt",
                           note="Only component intent and open questions are released. Inspection or clarification is valid; no initial code edit or interruption opportunity is guaranteed.")
    return result


def generate_source(contract_folder, folder, records, total=20, live=False, requested_type=None, requested_length=None, provider=call_json, replace_existing=False, precise_wording=False):
    if (contract_folder / "endpoint_only.json").exists():
        raise ValueError("Endpoint-only contracts require reviewed dialogue adaptation before generation")
    row, draft, _ = reviewed_contract(contract_folder)
    replaced = []
    if replace_existing:
        replaced = [r["scenario_id"] for r in records if r["source"]["instance_id"] == row["instance_id"]]
        records = [r for r in records if r["source"]["instance_id"] != row["instance_id"]]
    rendering_version = "2" if draft.get("schema_version") == "2" else None
    if (contract_folder / "category_policy.json").exists():
        rendering_version = "3"
    context, options, allocation = choose_context(row, draft, records, total, read_json(ROOT / "balance_config.json"), requested_type, requested_length, rendering_version)
    if replace_existing:
        allocation["explicit_replacement_candidates"] = replaced
    folder.mkdir(parents=True, exist_ok=False)
    snapshot(folder)
    save(folder / "allocation.json", allocation)
    save(folder / "source.json", row)
    save(folder / "contract_link.json", {"directory": str(contract_folder.relative_to(ROOT)),
                                       "contract_sha256": digest(contract_folder / "contract.json"),
                                       "review_sha256": digest(contract_folder / "contract_review.json")})
    if not context:
        save(folder / "status.json", {"status": allocation["status"], "model_calls": 0})
        return
    save(folder / "context.json", context)
    save(folder / "plan_options.json", options)
    save(folder / "status.json", {"status": "dry_run", "model_calls": 0})
    if not live:
        return
    calls = 0
    try:
        calls += 1
        progressive = draft.get("schema_version") == "2"
        planning_input = dict(context, valid_plans=options)
        if progressive:
            planning_input.update(dialogue_assessment=draft["dialogue_assessment"], class_preference=allocation["menu_types"])
            if "length_design" in draft:
                planning_input["length_design"] = draft["length_design"]
        select_prompt = ("select_stage_plan_v5.txt" if "length_design" in draft else
                         "select_stage_plan_v4.txt" if progressive else "select_stage_plan_v2.txt")
        if context.get("refinement_ids"):
            select_prompt = "select_stage_plan_v6.txt"
        selection = provider(planning_input, (ROOT / "prompts" / select_prompt).read_text(),
                             selection_schema(options), folder / "planning")
        schema_check(selection, selection_schema(options))
        save(folder / "selection.json", selection)
        if selection["plan_id"] == "none":
            save(folder / "status.json", {"status": "deferred_by_model", "model_calls": calls})
            return
        plan = deepcopy(next(o["plan"] for o in options if o["plan_id"] == selection["plan_id"]))
        plan["reason"] = selection["reason"]
        if progressive:
            context = context_for(row, draft, plan["trajectory_type"], len(plan["stages"]), rendering_version)
            save(folder / "context.json", context)
            allocation["selected"] = {"trajectory_type": plan["trajectory_type"], "n_messages": len(plan["stages"])}
            allocation["selection_reason"] = selection["reason"]
            save(folder / "allocation.json", allocation)
        validated = validate_plan(plan, context)
        save(folder / "stage_plan.json", plan)
        save(folder / "plan_validation.json", validated)
        calls += 1
        wording_prompt = "propose_trajectory_v8.txt" if progressive else "propose_trajectory_v6.1.txt"
        if context.get("refinement_ids"):
            wording_prompt = "propose_trajectory_v9.txt"
        if precise_wording:
            wording_prompt = "propose_trajectory_v10.txt"
            save(folder / "wording_policy.json", {"prompt": wording_prompt,
                 "sha256": digest(folder / "inputs/prompts" / wording_prompt)})
        wording = provider(wording_context(context, validated), (ROOT / "prompts" / wording_prompt).read_text(),
                           read_json(ROOT / "phrasing_schema_v6.json"), folder / "wording")
        save(folder / "wording.json", wording)
        record = candidate(wording, context, validated, row, folder, contract_folder)
        if record:
            save(folder / "draft_candidate.json", record)
        save(folder / "status.json", {"status": "draft_requires_semantic_review" if record else "wording_deferred", "model_calls": calls})
    except Exception as exc:
        save(folder / "status.json", {"status": "failed_or_rejected", "model_calls_attempted": calls, "error": str(exc)})
        raise


def reviewed_candidate(folder):
    link = read_json(folder / "contract_link.json")
    contract_folder = (ROOT / link["directory"]).resolve()
    if not contract_folder.is_relative_to(ROOT / "source_runs"):
        raise ValueError("Contract must be in author-side source_runs")
    row, draft, _ = reviewed_contract(contract_folder)
    if (digest(contract_folder / "contract.json") != link["contract_sha256"]
            or digest(contract_folder / "contract_review.json") != link["review_sha256"]):
        raise ValueError("Reviewed contract changed since generation")
    context = read_json(folder / "context.json")
    rendering_version = context.get("rendering_version")
    if context != context_for(row, draft, context["requested_trajectory_type"], context["n_messages"], rendering_version):
        raise ValueError("Generation context changed")
    if draft.get("schema_version") == "2":
        allocation = read_json(folder / "allocation.json")
        kinds, lengths = allocation["menu_types"], allocation["menu_lengths"]
        if not set(kinds) <= set(TYPES) or not set(lengths) <= {2, 3}:
            raise ValueError("Invalid saved menu dimensions")
        options, feasibility = build_menu(lambda k, n: context_for(row, draft, k, n, rendering_version), kinds, lengths)
        if allocation["feasibility"] != feasibility:
            raise ValueError("Saved feasibility assessment changed")
    else:
        options = enumerate_options(context, validate_plan)
    if options != read_json(folder / "plan_options.json"):
        raise ValueError("Legal plan menu changed")
    selection, wording = read_json(folder / "selection.json"), read_json(folder / "wording.json")
    if (folder / "wording_policy.json").exists():
        policy = read_json(folder / "wording_policy.json")
        if policy.get("prompt") != "propose_trajectory_v10.txt":
            raise ValueError("Unknown wording policy")
        prompt_path = folder / "inputs/prompts" / policy["prompt"]
        if (digest(prompt_path) != policy.get("sha256") or
                read_json(folder / "wording/request.json")["developer_instructions"] != prompt_path.read_text()):
            raise ValueError("Wording policy differs from saved model request")
    if selection != read_json(folder / "planning/answer.json") or wording != read_json(folder / "wording/answer.json"):
        raise ValueError("Generation output differs from saved model answers")
    plan = deepcopy(next(o["plan"] for o in options if o["plan_id"] == selection["plan_id"]))
    plan["reason"] = selection["reason"]
    if plan != read_json(folder / "stage_plan.json"):
        raise ValueError("Selected plan changed")
    result = candidate(wording, context, validate_plan(plan, context), row, folder, contract_folder)
    if result != read_json(folder / "draft_candidate.json"):
        raise ValueError("Saved candidate changed")
    review = check_review(folder / "semantic_review.json", {
        "candidate_sha256": folder / "draft_candidate.json", "plan_sha256": folder / "stage_plan.json",
        "wording_sha256": folder / "wording.json"}, REVIEW_CHECKS)
    result["validation"].update(status="semantic_reviewed_pending_new_stage_validation", semantic_review=review["reviewer"])
    result["provenance"]["review_sha256"] = digest(folder / "semantic_review.json")
    return result


def select_primary(records):
    """Keep one reviewed conversation per original; never infer runtime success.

    Recheck saved construction evidence before admitting a candidate. Old local
    pilots without complete final-test alignment remain development variants.
    Ranking uses task-validation evidence, then length, then a stable ID;
    solver performance and class deficits never choose a variant.
    """
    originals = rows_by_id()
    selected, excluded, seen_sources, seen_scenarios = [], [], set(), set()
    ordered = sorted((label_record(r) for r in records), key=lambda r: (
        r["source"]["instance_id"], not r["evaluation"].get("full_environment_validated", False),
        -r["n_messages"], r["scenario_id"]))
    for record in ordered:
        scenario, source = record["scenario_id"], record["source"]["instance_id"]
        if scenario in seen_scenarios:
            continue
        seen_scenarios.add(scenario)
        if source in seen_sources:
            excluded.append({"scenario_id": scenario, "instance_id": source,
                             "status": "alternate_variant", "reason": "One conversation already selected for this original."})
            continue
        try:
            run = (ROOT / record["provenance"]["run"]).resolve()
            if run.is_relative_to(ROOT / "source_runs"):
                checked = reviewed_candidate(run)
            elif run.is_relative_to(ROOT / "codex_runs") and record["evaluation"].get("full_environment_validated"):
                checked = candidate_from_run(run, originals)
            else:
                raise ValueError("Legacy candidate lacks complete final-test alignment evidence; retain for development review.")
            if label_record(checked) != record:
                raise ValueError("Candidate differs from its reviewed construction evidence")
            if record["group_id"] != source or record["evaluation"]["original_instance_id"] != source:
                raise ValueError("Original task identity must be preserved")
            final = record["stage_annotations"][-1]
            if final["unresolved"] or set(final["active_ids"]) != set(record["final_requirement_ids"]):
                raise ValueError("Final effective requirements must match the reviewed original contract")
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            excluded.append({"scenario_id": scenario, "instance_id": source,
                             "status": "needs_review", "reason": str(exc)})
            continue
        selected.append(record)
        seen_sources.add(source)
    return selected, excluded


def apply_quality_holds(records, review_path):
    """Exclude exact reviewed records while retaining frozen historical packages."""
    review = read_json(review_path)
    holds = review.get("holds", [])
    indexed = {r["scenario_id"]: r for r in records}
    excluded, seen = [], set()
    for hold in holds:
        scenario = hold["scenario_id"]
        record = indexed.get(scenario)
        if (record is None or scenario in seen or not hold.get("reason", "").strip()
                or hold.get("record_sha256") != hashlib.sha256(encoded(record)).hexdigest()):
            raise ValueError("Quality hold is unknown, duplicate, stale, or lacks a reason")
        seen.add(scenario)
        excluded.append({"scenario_id": scenario, "instance_id": record["group_id"],
                         "status": "explicit_quality_hold", "reason": hold["reason"],
                         "review_sha256": digest(review_path)})
    if not holds:
        raise ValueError("Quality review has no explicit holds")
    return [r for r in records if r["scenario_id"] not in seen], excluded


def export_dataset(runs, existing, output, keep_variants=False, replace_existing=False, quality_review=None):
    if replace_existing and keep_variants:
        raise ValueError("Explicit replacement keeps one primary per original")
    records, excluded, seen = [], [], set()
    for folder in existing:
        records.extend(label_record(r) for r in load_candidates(folder))
    replacements = []
    for folder in runs:
        try:
            replacements.append(reviewed_candidate(folder))
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            excluded.append({"run": str(folder.relative_to(ROOT)), "reason": str(exc)})
    if replace_existing:
        ids = [r["source"]["instance_id"] for r in replacements]
        if excluded or not ids or len(ids) != len(set(ids)):
            raise ValueError("Replacement requires one accepted new dialogue per requested original")
        removed = [r for r in records if r["source"]["instance_id"] in ids]
        if any(r["evaluation"].get("full_environment_validated") for r in removed):
            raise ValueError("Do not replace an environment-validated primary with an unvalidated dialogue")
        records = [r for r in records if r["source"]["instance_id"] not in ids]
        excluded.extend({"scenario_id": r["scenario_id"], "instance_id": r["source"]["instance_id"],
                         "status": "explicitly_replaced", "reason": "Explicit reviewed replacement; prior frozen package retained."}
                        for r in removed)
    records.extend(replacements)
    originals = rows_by_id()
    unique = []
    for record in records:
        if record["scenario_id"] in seen:
            continue
        row = originals[record["source"]["instance_id"]]
        if record["source"]["row_sha256"] != hashlib.sha256(encoded(row)).hexdigest():
            raise ValueError("Candidate source hash differs from original snapshot")
        seen.add(record["scenario_id"])
        unique.append(record)
    input_count = len(unique)
    if not keep_variants:
        unique, selection_excluded = select_primary(unique)
        excluded.extend(selection_excluded)
    if quality_review is not None:
        unique, quality_excluded = apply_quality_holds(unique, quality_review)
        excluded.extend(quality_excluded)
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output / "candidates.jsonl", unique)
    ids = sorted({r["source"]["instance_id"] for r in unique})
    write_jsonl(output / "evaluation_sources.jsonl", [originals[i] for i in ids])
    manifest = {"visibility": "author_controller_and_external_evaluator_only", "candidate_count": len(unique),
                "selection_policy": "development_variants" if keep_variants else "one_conversation_per_original",
                "input_candidate_count": input_count,
                "original_task_count": len(ids), "trajectory_type_distribution": distribution(unique),
                "message_count_distribution": {str(n): sum(r["n_messages"] == n for r in unique) for n in (2, 3)},
                "repository_count": len({r["source"]["repo"] for r in unique}),
                "environment_validated_original_task_count": len({r["group_id"] for r in unique if r["evaluation"]["full_environment_validated"]}),
                "experiment_ready_count": 0, "excluded": excluded,
                "files": {name: digest(output / name) for name in ("candidates.jsonl", "evaluation_sources.jsonl")},
                "note": "Development dataset. Source test mapping is not test execution or proof of complete semantic coverage."}
    save(output / "manifest.json", manifest)
    save(output / "coverage.json", inventory(unique))
    lines = ["# Development dataset examples", "", "Stage validation varies by record; this is not a benchmark release.", ""]
    for record in unique:
        lines += ["## " + record["scenario_id"], "", "Class: `" + record["trajectory_type"] + "`; updates: `" + " -> ".join(record["update_types"]) + "`.", ""]
        for message in record["messages"]:
            lines += ["**" + message["id"] + "**", "", message["content"], ""]
    (output / "examples.md").write_text("\n".join(lines))
    return manifest


def summarize_runs(folders, output):
    entries = []
    totals = {"completed_model_calls": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for folder in folders:
        state = read_json(folder / "status.json")
        entry = {"run": str(folder.relative_to(ROOT)), "instance_id": read_json(folder / "source.json")["instance_id"],
                 "status": state["status"], "reported_usage": dict.fromkeys(totals, 0)}
        for stage in ("extraction", "planning", "wording"):
            result_path = folder / stage / "result.json"
            if not result_path.exists():
                continue
            for usage in read_json(result_path).get("reported_usages", []):
                entry["reported_usage"]["completed_model_calls"] += 1
                for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
                    entry["reported_usage"][key] += usage.get(key, 0)
        for name in ("contract_review.json", "semantic_review.json"):
            if (folder / name).exists():
                review = read_json(folder / name)
                entry[name] = {"verdict": review["verdict"], "reason": review.get("reason", "See saved review notes.")}
        for key in totals:
            totals[key] += entry["reported_usage"][key]
        entries.append(entry)
    report = {"runs": entries, "totals": totals, "original_task_count": len({e["instance_id"] for e in entries}),
              "note": "Construction calibration only. Deferred/held attempts are retained. Reported completed-call usage is not weekly allowance or solver cost."}
    save(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    ext = sub.add_parser("extract")
    ext.add_argument("--instance", required=True)
    ext.add_argument("--seed-contract", type=Path, help="Try a three-message adaptation while locking reviewed final requirements")
    ext.add_argument("--partition-scopes", action="store_true", help="With a seed, repartition its complete endpoint; requires explicit semantic equivalence review")
    ext.add_argument("--scope-hints", type=Path, help="Optional JSON list of author-reviewed source scope names; only with --partition-scopes")
    ext.add_argument("--allow-refinement", action="store_true", help="Try a compatible partial goal followed by precise original requirements")
    ext.add_argument("--prefer-type", choices=TYPES, help="Design a scarce class before wording; a soft preference, not a label override")
    ext.add_argument("--category-prompt-version", choices=("1", "2", "3"), default="1", help="v2 prefers meaningful three-message histories; v3 protects a scarce class")
    ext.add_argument("--endpoint-only", action="store_true", help="Extract a neutral final task for review before class-aware adaptation")
    gen = sub.add_parser("generate")
    gen.add_argument("--contract", type=Path, required=True)
    gen.add_argument("--existing", type=Path, nargs="*", default=[])
    gen.add_argument("--target-total", type=int, default=20)
    gen.add_argument("--trajectory-type", choices=TYPES)
    gen.add_argument("--messages", type=int, choices=(2, 3))
    gen.add_argument("--replace-existing", action="store_true", help="Explicit calibration of an existing original; export still selects one")
    for cmd in (ext, gen):
        cmd.add_argument("--live", action="store_true")
    exp = sub.add_parser("export")
    exp.add_argument("--runs", type=Path, nargs="*", default=[])
    exp.add_argument("--existing", type=Path, nargs="*", default=[])
    exp.add_argument("--keep-variants", action="store_true", help="Archive development variants instead of selecting one per original")
    exp.add_argument("--replace-existing", action="store_true", help="Explicitly select reviewed new dialogues for the same original IDs; preserve old packages")
    exp.add_argument("--quality-review", type=Path, help="Hash-bound author review excluding known flawed records from this export")
    report = sub.add_parser("report")
    report.add_argument("--runs", type=Path, nargs="+", required=True)
    for cmd in (ext, gen, exp, report):
        cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.operation in ("extract", "generate") and not output.is_relative_to(ROOT / "source_runs"):
        raise ValueError("Keep source construction artifacts in author-side source_runs")
    if args.operation == "extract":
        extract(rows_by_id()[args.instance], output, args.live, seed_folder=args.seed_contract, partition_scopes=args.partition_scopes,
                scope_hints=read_json(args.scope_hints) if args.scope_hints else None, allow_refinement=args.allow_refinement,
                preferred_type=args.prefer_type, endpoint_only=args.endpoint_only, category_prompt_version=args.category_prompt_version)
    elif args.operation == "generate":
        records = [r for f in args.existing for r in load_candidates(f)]
        generate_source(args.contract.resolve(), output, records, args.target_total, args.live, args.trajectory_type, args.messages,
                        replace_existing=args.replace_existing)
    elif args.operation == "export":
        print(json.dumps(export_dataset([p.resolve() for p in args.runs], args.existing, output, args.keep_variants, args.replace_existing, args.quality_review)))
        return
    else:
        print(json.dumps(summarize_runs([p.resolve() for p in args.runs], output)["totals"]))
        return
    print(json.dumps(read_json(output / "status.json")))


if __name__ == "__main__":
    main()
