"""Two-call pilot: legal plan menu -> LLM selection -> natural English messages.

Dry-run by default. Initially limited to the prepared slugify requirement pool.
Unreviewed drafts stay outside candidate packages; export requires a saved review.
Original gold/tests remain in external author-side evaluation_sources.jsonl.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

from benchmark_data import write_jsonl
from codex_pilot import child_environment, command_for, inspect_events
from fixed_trajectory import contract_for
from model_pilot import ROOT, digest, encoded, read_json, save, schema_check
from multistage_trajectory import validate_stages
from progressive_stages import validate_progressive_stages
from stage_plan_options import enumerate_options, selection_schema
from trajectory_labels import TYPES, VERSION, classify, distribution, label_record

INSTANCE = "django__django-12983"
REVIEW_CHECKS = ("plan_is_meaningful", "wording_matches_stages", "final_goal_preserved",
                 "no_future_leakage", "explicit_revisions", "natural_english")


def planning_context(row, requested_type="mixed", n_messages=3):
    if row["instance_id"] != INSTANCE:
        raise ValueError("Stage planning currently supports the prepared slugify contract only")
    if requested_type not in TYPES or n_messages not in (2, 3):
        raise ValueError("Unknown trajectory type or message count")
    if requested_type == "mixed" and n_messages == 2:
        raise ValueError("One operation per update: mixed needs three messages in this pilot")
    contract = contract_for(row, "clarification")
    catalog = read_json(ROOT / "multistage_plans.json")
    if digest(ROOT / "fixed_contracts.json") != catalog["contract_sha256"]:
        raise ValueError("Prepared contract changed")
    # Deliberately exclude authored stage sequences, implementation references,
    # source test patches, gold, witnesses, and previous model answers.
    return {"repo": row["repo"], "context_en": contract["context_en"],
            "final_requirements": [{"id": r["id"], "text_en": r["text_en"]} for r in contract["requirements"]],
            "temporary_requirements": deepcopy(contract["temporary_requirements"]),
            "uncertainty_choices": deepcopy(catalog["uncertainty_choices"]),
            "final_summary_en": contract["final_summary_en"], "invariant_ids": ["keep_normalization"],
            "requested_trajectory_type": requested_type, "n_messages": n_messages}


def plan_schema(context):
    def text(max_length=600):
        return {"type": "string", "minLength": 1, "maxLength": max_length}
    def obj(properties):
        return {"type": "object", "additionalProperties": False,
                "required": list(properties), "properties": properties}
    def array(item, maximum):
        return {"type": "array", "maxItems": maximum, "items": item}
    ids = [r["id"] for r in context["final_requirements"] + context["temporary_requirements"]]
    requirement = {"type": "string", "enum": ids}
    dimension = {"type": "string", "enum": list(context["uncertainty_choices"])}
    stage = obj({"id": {"type": "string", "enum": ["U0", "U1", "U2"]},
                 "type": {"type": "string", "enum": ["initial", "addition", "clarification", "revision"]},
                 "add": array(requirement, len(ids)), "remove": array(requirement, len(ids)),
                 "unknown": array(dimension, len(context["uncertainty_choices"])),
                 "resolves": array(obj({"dimension": dimension, "requirement_ids": array(requirement, len(ids))}),
                                   len(context["uncertainty_choices"])), "rationale": text()})
    return obj({"decision": {"type": "string", "enum": ["propose_plan", "defer"]},
                "trajectory_type": {"type": "string", "enum": list(TYPES)},
                "reason": text(), "stages": array(stage, 3)})


def validate_plan(draft, context):
    schema_check(draft, plan_schema(context))
    if draft["decision"] == "defer":
        if draft["stages"]:
            raise ValueError("Deferred plan must have no stages")
        return {"status": "deferred_by_model"}
    if len(draft["stages"]) != context["n_messages"]:
        raise ValueError("Wrong requested message count")
    stages = []
    for item in draft["stages"]:
        stage = deepcopy(item)
        resolutions = {r["dimension"]: r["requirement_ids"] for r in stage["resolves"]}
        if len(resolutions) != len(stage["resolves"]):
            raise ValueError("Duplicate resolution dimension")
        stage["resolves"] = resolutions
        stages.append(stage)
    contract = {"requirements": context["final_requirements"],
                "temporary_requirements": context["temporary_requirements"],
                "uncertainties": [{"id": uid} for uid in context["uncertainty_choices"]]}
    if context.get("refinement_ids"):
        contract["refinement_ids"] = context["refinement_ids"]
    progressive = context.get("planning_version") == "2"
    validate_state = validate_progressive_stages if progressive else validate_stages
    trace = validate_state(contract, stages, context["uncertainty_choices"])
    invariants = set(context["invariant_ids"])
    if any(not invariants <= set(s["active_ids"]) for s in trace):
        raise ValueError("Every stage must retain the supplied invariant requirements")
    if not set(trace[0]["active_ids"]) - invariants and not (
            progressive and context["context_en"].strip() and trace[0]["unresolved"]):
        raise ValueError("U0 must request actionable work beyond unchanged invariants")
    updates = [s["type"] for s in stages[1:]]
    kind = classify(updates)
    if kind != draft["trajectory_type"] or kind != context["requested_trajectory_type"]:
        raise ValueError("Claimed/requested class differs from the actual update sequence")
    return {"status": "plan_requires_semantic_review", "trajectory_type": kind,
            "update_types": updates, "stages": stages, "state_trace": trace}


def wording_context(context, validated):
    by_id = {r["id"]: r for r in context["final_requirements"] + context["temporary_requirements"]}
    def select(ids):
        return [{"id": rid, "text_en": by_id[rid]["text_en"]} for rid in ids]
    def uncertainty(uid):
        if uid in context.get("clarification_questions", {}):
            # The answer is author-side; U0 gets only the open question.
            return {"id": uid, "question_en": context["clarification_questions"][uid]}
        return {"id": uid, "alternatives": [select(ids) for ids in context["uncertainty_choices"][uid]]}
    result = {"draft_mode": "validated_model_plan", "repo": context["repo"],
            "context_en": context["context_en"], "n_messages": context["n_messages"],
            "stages": [{"id": s["id"], "type": s["type"], "active_requirements": select(t["active_ids"]),
                        "add": select(s["add"]), "remove": select(s["remove"]),
                        "resolves": {uid: select(ids) for uid, ids in s["resolves"].items()},
                        "uncertainties": [uncertainty(uid) for uid in t["unresolved"]]}
                       for s, t in zip(validated["stages"], validated["state_trace"])],
            "final_summary_en": context["final_summary_en"]}
    if context.get("refinement_ids"):
        result["refinement_ids"] = context["refinement_ids"]
        for item, trace in zip(result["stages"], validated["state_trace"]):
            item["refines"] = select(trace["refined_ids"])
            item["pending_refinement_ids"] = trace["pending_refinement_ids"]
    return result


def assemble(wording, context, validated, row, run_name):
    schema_check(wording, read_json(ROOT / "phrasing_schema_v6.json"))
    if wording["decision"] == "defer":
        if wording["messages"]:
            raise ValueError("Deferred wording must have no messages")
        return None
    messages = deepcopy(wording["messages"])
    if [m["id"] for m in messages] != [s["id"] for s in validated["stages"]]:
        raise ValueError("Wording message order differs from the validated plan")
    process = r'\b(?:program|script|pipeline)\s+will\s+(?:append|attach|insert)\b|\bfinal_summary_en\b|\b(?:benchmark|hidden tests)\b'
    for message in messages:
        if context["final_summary_en"] in message["content"] or re.search(process, message["content"], re.IGNORECASE):
            raise ValueError("Final summary or author process text leaked into model wording")
    messages[-1]["content"] = messages[-1]["content"].strip() + "\n\n" + context["final_summary_en"]
    source_id = row["instance_id"]
    fingerprint = hashlib.sha256(encoded({"plan": validated, "messages": messages})).hexdigest()[:10]
    updates = validated["update_types"]
    record = {"schema_version": "0.4", "visibility": "author_controller_only", "split": "development",
              "scenario_id": source_id + ".planned.v1." + fingerprint, "group_id": source_id,
              "update_type": updates[0] if len(set(updates)) == 1 else "mixed", "update_types": updates,
              "messages": messages, "stage_annotations": validated["state_trace"],
              "final_requirement_ids": validated["state_trace"][-1]["active_ids"],
              "full_prompt": context["final_summary_en"],
              "source": {"dataset": "princeton-nlp/SWE-bench_Lite", "split": "test", "instance_id": source_id,
                         "repo": row["repo"], "base_commit": row["base_commit"],
                         "snapshot_sha256": digest(ROOT / "data/lite_snapshot.json.gz"),
                         "row_sha256": hashlib.sha256(encoded(row)).hexdigest()},
              "evaluation": {"kind": "swebench_original_tests", "original_instance_id": source_id,
                             "harness_package": "swebench==4.1.0", "source_file": "evaluation_sources.jsonl",
                             "full_environment_validated": False, "stage_checks_status": "not_linked_for_this_new_plan"},
              "validation": {"status": "draft_requires_semantic_review", "local_probes": "not_run_for_new_plan",
                             "independent_human_review": False, "experiment_ready": False},
              "provenance": {"run": run_name, "annotation_origin": "model_selected_rule_enumerated_plan",
                             "wording_origin": "codex_unedited", "wording_edits": 0,
                             "final_contract_origin": "existing_author_prepared_contract"}}
    return label_record(record)


def call_json(source, prompt, schema, folder, config=None):
    """Reuse the existing ChatGPT-authenticated, tool-free Codex CLI interface."""
    config = deepcopy(config if config is not None else read_json(ROOT / "codex_config.json"))
    if ((config["model"], config["reasoning_effort"]) not in
            (("gpt-6-luna", "low"), ("gpt-6.1-sol", "medium"))
            or config["cli_overrides"].get("forced_login_method") != "chatgpt"):
        raise ValueError("Use an approved Luna/low or Sol/medium ChatGPT construction profile")
    folder.mkdir()
    binary = shutil.which("codex")
    if not binary:
        raise ValueError("Codex CLI unavailable")
    request = {"input": source, "developer_instructions": prompt, "schema": schema, "config": config}
    if len(encoded(request)) > config["max_input_bytes"]:
        raise ValueError("Request too large; no silent truncation")
    save(folder / "request.json", request)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="pj-stage-plan-") as tmp:
        workspace = Path(tmp)
        save(workspace / "schema.json", schema)
        args = command_for({"request": request}, binary, workspace)
        save(folder / "command.json", args)
        process = subprocess.Popen(args, cwd=workspace, env=child_environment(os.environ), text=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(json.dumps(source, ensure_ascii=False), timeout=config["timeout_seconds"])
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            timed_out = True
        (folder / "events.jsonl").write_text(stdout)
        (folder / "stderr.txt").write_text(stderr)
        answer = workspace / "answer.json"
        if answer.exists():
            shutil.copyfile(answer, folder / "answer.json")
        events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
        save(folder / "result.json", {"exit_code": process.returncode, "timed_out": timed_out,
             "elapsed_seconds": round(time.monotonic() - started, 2),
             "reported_usages": [e.get("usage") for e in events if e.get("type") == "turn.completed"]})
        if process.returncode or timed_out:
            raise RuntimeError("Codex call failed; inspect saved events")
        inspect_events(events)  # Reject unexpected native tool use or missing usage.
        value = read_json(answer)
        schema_check(value, schema)
        return value


def generate(row, requested_type, n_messages, output, live=False, provider=call_json):
    output = Path(output).resolve()
    context = planning_context(row, requested_type, n_messages)
    output.mkdir(parents=True, exist_ok=False)
    save(output / "planning_input.json", context)
    files = ["planned_generation.py", "stage_plan_options.py", "trajectory_labels.py", "multistage_trajectory.py", "fixed_contracts.json",
             "multistage_plans.json", "codex_pilot.py", "codex_config.json", "phrasing_schema_v6.json",
             "prompts/select_stage_plan_v2.txt", "prompts/propose_trajectory_v6.1.txt", "data/lite_snapshot.json.gz"]
    save(output / "manifest.json", {"created_at": datetime.now(timezone.utc).isoformat(), "instance_id": row["instance_id"],
         "mode": "live" if live else "dry_run", "max_model_calls": 2, "model": "gpt-6-luna", "reasoning_effort": "low",
         "effective_model_note": "Requested CLI model; no independent model attestation",
         "input_hashes": {name: digest(ROOT / name) for name in files}, "experiment_ready": False})
    options = enumerate_options(context, validate_plan)
    save(output / "plan_options.json", options)
    if not options:
        save(output / "status.json", {"status": "no_legal_plan", "model_calls": 0})
        return
    if not live:
        save(output / "status.json", {"status": "dry_run", "model_calls": 0})
        return
    copies = output / "inputs"
    copies.mkdir()
    for name in files:
        if name != "data/lite_snapshot.json.gz":
            shutil.copyfile(ROOT / name, copies / Path(name).name)
    calls = 0
    try:
        calls += 1
        selection = provider(dict(context, valid_plans=options), (ROOT / "prompts/select_stage_plan_v2.txt").read_text(),
                             selection_schema(options), output / "planning")
        schema_check(selection, selection_schema(options))
        save(output / "plan_selection.json", selection)
        if selection["plan_id"] == "none":
            save(output / "status.json", {"status": "deferred_by_model", "model_calls": calls})
            return
        draft = deepcopy(next(o["plan"] for o in options if o["plan_id"] == selection["plan_id"]))
        draft["reason"] = selection["reason"]
        save(output / "stage_plan.json", draft)
        validated = validate_plan(draft, context)
        save(output / "plan_validation.json", validated)
        if validated["status"] == "deferred_by_model":
            save(output / "status.json", {"status": "deferred_by_model", "model_calls": calls})
            return
        calls += 1
        wording = provider(wording_context(context, validated), (ROOT / "prompts/propose_trajectory_v6.1.txt").read_text(),
                           read_json(ROOT / "phrasing_schema_v6.json"), output / "wording")
        save(output / "wording.json", wording)
        candidate = assemble(wording, context, validated, row, str(output.relative_to(ROOT)))
        if candidate is not None:
            save(output / "draft_candidate.json", candidate)
            write_jsonl(output / "evaluation_sources.jsonl", [row])
        save(output / "status.json", {"status": "draft_requires_semantic_review" if candidate else "wording_deferred",
                                       "model_calls": calls, "experiment_ready": False})
    except Exception as exc:
        save(output / "status.json", {"status": "failed_or_rejected", "model_calls_attempted": calls,
                                       "error": str(exc), "experiment_ready": False})
        raise


def export_reviewed(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    review = read_json(run / "semantic_review.json")
    for key, name in (("candidate_sha256", "draft_candidate.json"), ("plan_sha256", "stage_plan.json"),
                      ("wording_sha256", "wording.json")):
        if review.get(key) != digest(run / name):
            raise ValueError("Review does not match saved " + name)
    if (review.get("verdict") != "accept_for_development" or not review.get("reviewer")
            or not all(review.get("checks", {}).get(k) is True for k in REVIEW_CHECKS)):
        raise ValueError("Draft needs a complete accepting semantic review")
    row = read_json(run / "evaluation_sources.jsonl")
    context = planning_context(row, read_json(run / "planning_input.json")["requested_trajectory_type"],
                               read_json(run / "planning_input.json")["n_messages"])
    if context != read_json(run / "planning_input.json"):
        raise ValueError("Prepared source context changed")
    options = enumerate_options(context, validate_plan)
    if options != read_json(run / "plan_options.json"):
        raise ValueError("Saved legal plan menu changed")
    selection = read_json(run / "plan_selection.json")
    schema_check(selection, selection_schema(options))
    if selection != read_json(run / "planning/answer.json") or selection["plan_id"] == "none":
        raise ValueError("Saved selection differs from the model answer or was deferred")
    selected_plan = deepcopy(next(o["plan"] for o in options if o["plan_id"] == selection["plan_id"]))
    selected_plan["reason"] = selection["reason"]
    if selected_plan != read_json(run / "stage_plan.json"):
        raise ValueError("Stage plan differs from the selected option")
    if read_json(run / "wording.json") != read_json(run / "wording/answer.json"):
        raise ValueError("Unedited wording differs from the model answer")
    validated = validate_plan(read_json(run / "stage_plan.json"), context)
    record = assemble(read_json(run / "wording.json"), context, validated, row, str(run.relative_to(ROOT)))
    if record != read_json(run / "draft_candidate.json"):
        raise ValueError("Saved candidate differs from checked plan/wording")
    record["validation"].update(status="semantic_reviewed_pending_new_stage_validation", semantic_review=review["reviewer"])
    record["provenance"]["review_sha256"] = digest(run / "semantic_review.json")
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output / "candidates.jsonl", [record])
    shutil.copyfile(run / "evaluation_sources.jsonl", output / "evaluation_sources.jsonl")
    manifest = {"visibility": "author_controller_and_external_evaluator_only", "candidate_count": 1, "original_task_count": 1,
                "classification_version": VERSION, "trajectory_type_distribution": distribution([record]),
                "message_count_distribution": {str(n): int(record["n_messages"] == n) for n in (2, 3)},
                "environment_validated_original_task_count": 0, "experiment_ready_count": 0,
                "files": {name: digest(output / name) for name in ("candidates.jsonl", "evaluation_sources.jsonl")},
                "note": "New model-planned development candidate. Original evaluator linked; new stage validation not claimed."}
    save(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--instance", default=INSTANCE)
    gen.add_argument("--trajectory-type", choices=TYPES, default="mixed")
    gen.add_argument("--messages", type=int, choices=(2, 3), default=3)
    gen.add_argument("--output", type=Path, required=True)
    gen.add_argument("--live", action="store_true")
    exp = sub.add_parser("export")
    exp.add_argument("--run", type=Path, required=True)
    exp.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "generate":
        output = args.output.resolve()
        if not output.is_relative_to(ROOT / "planned_runs"):
            raise ValueError("Keep generation artifacts in author-side planned_runs")
        row = next(r for r in read_json(ROOT / "data/lite_snapshot.json.gz")["instances"] if r["instance_id"] == args.instance)
        generate(row, args.trajectory_type, args.messages, output, args.live)
        print(json.dumps(read_json(output / "status.json")))
    else:
        print(json.dumps(export_reviewed(args.run, args.output)))


if __name__ == "__main__":
    main()
