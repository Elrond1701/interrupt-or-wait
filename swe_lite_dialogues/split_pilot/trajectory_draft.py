"""Contract-guided two-message drafting; no generation or solver execution here."""

from model_pilot import ROOT, check_draft, digest, read_json, schema_check
import hashlib

TYPES = ("addition", "clarification", "revision")


def load_contract(row):
    catalog = read_json(ROOT / "draft_contracts.json")
    if catalog["requirements_sha256"] != digest(ROOT / "requirements.json"):
        raise ValueError("Contract source annotations changed; review before generating")
    contract = next((c for c in catalog["contracts"] if c["instance_id"] == row["instance_id"]), None)
    if contract is None:
        raise ValueError("No frozen drafting contract for this instance")
    if (contract["base_commit"] != row["base_commit"] or contract["problem_sha256"] !=
            hashlib.sha256(row["problem_statement"].encode()).hexdigest()):
        raise ValueError("Contract source identity changed")
    return contract


def drafting_input(row, update_type=None):
    source = {"repo": row["repo"], "problem_statement": row["problem_statement"]}
    if update_type is not None:
        if update_type not in TYPES:
            raise ValueError("Unsupported update type")
        c = load_contract(row)
        # The drafting model sees behavioral specifications, not test code,
        # patches, private evidence paths, or validation/review outcomes.
        source.update(update_type=update_type, final_contract={
            k: c[k] for k in ("context_en", "requirements", "final_summary_en",
                             "temporary_requirements", "uncertainties")})
    return source


def check_trajectory(draft, source, schema):
    schema_check(draft, schema)
    if draft["update_type"] != source["update_type"]:
        raise ValueError("Draft type differs from the requested type")
    if draft["decision"] == "defer":
        fields = ("initial_message_en", "initial_requirement_ids", "unresolved_dimensions",
                  "update_transition_en", "add_requirement_ids", "remove_requirement_ids",
                  "change_explanation")
        if any(draft[k] for k in fields) or any(draft["contrast_case"].values()):
            raise ValueError("A deferred draft must not contain a proposed scenario")
        return {"status": "deferred_by_model", "experiment_ready": False}

    c = source["final_contract"]
    final = {r["id"] for r in c["requirements"]}
    temporary = {r["id"] for r in c["temporary_requirements"]}
    uncertainty = {u["id"]: u for u in c["uncertainties"]}
    if final & temporary:
        raise ValueError("Contract final and temporary IDs overlap")
    sets = {}
    for field in ("initial_requirement_ids", "add_requirement_ids", "remove_requirement_ids",
                  "unresolved_dimensions"):
        ids = draft[field]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate annotation IDs")
        sets[field] = set(ids)
    active, added, removed, unknown = (sets[k] for k in (
        "initial_requirement_ids", "add_requirement_ids", "remove_requirement_ids",
        "unresolved_dimensions"))
    if not active or not active <= final | temporary or not added <= final:
        raise ValueError("Unknown or empty requirement annotations")
    if not removed <= active or added & active:
        raise ValueError("Cannot remove inactive or add already active requirements")
    if not added or (active - removed) | added != final:
        raise ValueError("Final effective requirements do not match the frozen endpoint")
    if not unknown <= set(uncertainty):
        raise ValueError("Unknown uncertainty dimension")
    kind = draft["update_type"]
    if kind == "revision":
        if unknown or not (active & temporary) or removed != active & temporary:
            raise ValueError("Revision must explicitly retire its temporary requirements")
        replacements = {r["id"]: set(r["replaced_by"]) for r in c["temporary_requirements"]}
        if any(not replacements[rid] <= added for rid in removed):
            raise ValueError("Revision omits a required replacement")
    elif removed or active & temporary:
        raise ValueError("Only revision may introduce and remove a temporary requirement")
    if kind == "clarification":
        if not unknown:
            raise ValueError("Clarification needs an unresolved dimension")
        for uid in unknown:
            resolves = set(uncertainty[uid]["resolved_by"])
            if len(uncertainty[uid]["plausible_interpretations"]) < 2 or not resolves <= added:
                raise ValueError("Clarification must resolve its previously unknown dimension")
    elif unknown:
        raise ValueError("Only clarification may use unresolved dimensions in this pilot")
    for field in ("initial_message_en", "update_transition_en", "change_explanation"):
        if not draft[field].strip():
            raise ValueError("Missing message or change explanation")
    case = draft["contrast_case"]
    if any(not v.strip() for v in case.values()) or case["earlier_output"] == case["final_output"]:
        raise ValueError("A proposed behavioral contrast is required")
    messages = [{"id": "U0", "content": draft["initial_message_en"]},
                {"id": "U1", "content": draft["update_transition_en"].strip() +
                 "\n\n" + c["final_summary_en"]}]
    return {
        "status": "draft_requires_semantic_review", "experiment_ready": False,
        "update_type": kind, "author_preview": messages,
        "state_trace": [{"id": "U0", "active_ids": sorted(active), "unresolved": sorted(unknown)},
                        {"id": "U1", "active_ids": sorted(final), "unresolved": [],
                         "retired_ids": sorted(removed)}],
        "final_summary_origin": "verbatim frozen contract appended by code",
        "witness_status": "proposed_not_executed",
        "unchecked": ["free-text meaning matches annotations", "naturalness and future leakage",
                      "transition does not contradict appended final summary", "independent contract review",
                      "full environment tests and actual interruptibility"],
    }


def check_saved_draft(draft, row, request):
    if "update_type" in request["input"]:
        return check_trajectory(draft, request["input"], request["schema"])
    return check_draft(draft, row, request["schema"])
