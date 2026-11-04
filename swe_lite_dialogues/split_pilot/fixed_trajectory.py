"""Fixed author annotations -> model wording -> deterministic two-message draft."""

import hashlib

from model_pilot import ROOT, encoded, read_json, digest, schema_check
from trajectory_draft import check_trajectory


def contract_for(row, kind):
    catalog = read_json(ROOT / "fixed_contracts.json")
    if catalog["snapshot_sha256"] != digest(ROOT / "data/lite_snapshot.json.gz"):
        raise ValueError("Fixed-plan snapshot changed; review contracts first")
    matches = [c for c in catalog["contracts"] if c["instance_id"] == row["instance_id"]]
    if len(matches) != 1 or kind not in matches[0]["plans"]:
        raise ValueError("No fixed stage plan for this instance/type")
    c = matches[0]
    if (c["base_commit"] != row["base_commit"] or
            c["source_row_sha256"] != hashlib.sha256(encoded(row)).hexdigest()):
        raise ValueError("Fixed-plan source changed")
    for requirement in c["requirements"]:
        evidence = requirement.get("evidence")
        if evidence and evidence["quote"] not in row[evidence["field"]]:
            raise ValueError("Contract source evidence missing")
    if c.get("source_contract_sha256") and c["source_contract_sha256"] != digest(ROOT / "draft_contracts.json"):
        raise ValueError("Original slugify contract changed")
    return c


def fixed_input(row, kind):
    c = contract_for(row, kind)
    p = c["plans"][kind]
    by_id = {r["id"]: r for r in c["requirements"] + c["temporary_requirements"]}
    select = lambda ids: [{"id": rid, "text_en": by_id[rid]["text_en"]} for rid in ids]
    source = {
        "draft_mode": "fixed_stages", "repo": row["repo"], "context_en": c["context_en"],
        "update_type": kind,
        "initial_stage": {"requirements": select(p["initial_requirement_ids"]),
                          "uncertainties": [u for u in c["uncertainties"] if u["id"] in p["unresolved_dimensions"]]},
        "update_stage": {"add": select(p["add_requirement_ids"]),
                         "remove": select(p["remove_requirement_ids"]),
                         "resolves": p["unresolved_dimensions"]},
        "final_summary_en": c["final_summary_en"],
    }
    # Validate the author's stage state before spending any generation allowance.
    assemble({"decision": "propose_split", "reason": "preflight", "initial_message_en": "preflight",
              "update_transition_en": "preflight", "risks": []}, c, kind)
    return source


def assemble(wording, contract, kind):
    schema_check(wording, read_json(ROOT / "phrasing_schema.json"))
    if wording["decision"] == "defer":
        if wording["initial_message_en"] or wording["update_transition_en"]:
            raise ValueError("Deferred wording must not include messages")
        return {"status": "deferred_by_model", "experiment_ready": False}
    p = contract["plans"][kind]
    draft = {**p, **wording, "update_type": kind,
             "change_explanation": "Stage annotations and contrast fixed by author before wording generation."}
    source = {"update_type": kind, "final_contract": contract}
    result = check_trajectory(draft, source, read_json(ROOT / "trajectory_schema.json"))
    result.update(annotation_origin="fixed_author_plan_not_model_output",
                  contrast_origin="fixed_author_probe_not_model_output")
    return result


def check_fixed(wording, row, request):
    source = request["input"]
    if source != fixed_input(row, source["update_type"]):
        raise ValueError("Saved fixed stage input differs from current contract")
    return assemble(wording, contract_for(row, source["update_type"]), source["update_type"])
