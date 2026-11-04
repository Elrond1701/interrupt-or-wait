"""Check saved slugify draft examples using fixed local implementations.

No model code is executed. Finite plain-string probes are not a full evaluator
or a proof that free-text annotations are faithful.
"""

import argparse
from pathlib import Path
import shutil
import tempfile

from model_pilot import ROOT, digest, read_json, save
from trajectory_draft import check_saved_draft, drafting_input
from verify_split import apply_patch, load_slugify, slugify_checks


def functions(directory):
    row = next(r for r in read_json(ROOT / "author_reference.json")["instances"]
               if r["instance_id"] == "django__django-12983")
    shutil.copytree(ROOT / "vendor/slugify", directory)
    file = directory / "django/utils/text.py"
    base_source = file.read_text()
    apply_patch(directory, row["patch"])
    gold_source = file.read_text()
    assert ".strip('-_')" in gold_source
    base = load_slugify(base_source)
    return {"dash_only": lambda s: base(s).strip('-'),
            "remove_all_underscores": lambda s: base(s).replace('_', '').strip('-'),
            "gold": load_slugify(gold_source)}


def initial_probes(fn, ids):
    cases = {
        "trim_dashes": [("---abc---", "abc")],
        "trim_boundary_underscores": [("__abc__", "abc"), ("_-abc_-", "abc")],
        "keep_internal_underscores": [("a_b", "a_b")],
        "keep_normalization": [("Hello, World!", "hello-world"), ("A  B", "a-b")],
        "remove_all_underscores": [("__a_b__", "ab")],
    }
    return {rid: all(fn(s) == expected for s, expected in cases[rid]) for rid in ids}


def audit(out):
    out = out.resolve()
    plan, draft = read_json(out / "plan.json"), read_json(out / "draft.json")
    row = next(r for r in read_json(ROOT / "data/lite_snapshot.json.gz")["instances"]
               if r["instance_id"] == plan["instance_id"])
    if row["instance_id"] != "django__django-12983" or plan["request"]["input"] != drafting_input(row, draft["update_type"]):
        raise ValueError("This local audit requires the current frozen slugify contract")
    verdict = check_saved_draft(draft, row, plan["request"])
    if draft["decision"] != "propose_split":
        raise ValueError("No proposed trajectory to audit")
    case = draft["contrast_case"]
    with tempfile.TemporaryDirectory(prefix="trajectory-audit-") as tmp:
        fns = functions(Path(tmp) / "slug")
        eligible = ["remove_all_underscores"] if draft["update_type"] == "revision" else (
            ["dash_only"] if draft["update_type"] == "addition" else ["dash_only", "remove_all_underscores"])
        witnesses = []
        for name in eligible:
            checks = initial_probes(fns[name], draft["initial_requirement_ids"])
            output = fns[name](case["input"])
            witnesses.append({"name": name, "initial_requirement_probes": checks,
                              "actual_output": output,
                              "matches_proposed_earlier_output": output == case["earlier_output"],
                              "supports_proposed_contrast": all(checks.values()) and output == case["earlier_output"]})
        final_output = fns["gold"](case["input"])
        final_probes = slugify_checks(fns["gold"])
    passed = (any(w["supports_proposed_contrast"] for w in witnesses)
              and final_output == case["final_output"] and final_output != case["earlier_output"]
              and all(g["passed"] == g["total"] for g in final_probes.values()))
    report = {
        "scope": "Offline plain-string probes only; not full Django or agent evaluation.",
        "input_hashes": {str(p.relative_to(ROOT)): digest(p) for p in (
            out / "draft.json", out / "plan.json", ROOT / "draft_contracts.json",
            ROOT / "author_reference.json", ROOT / "vendor/slugify/django/utils/text.py",
            Path(__file__).resolve(), ROOT / "verify_split.py", ROOT / "trajectory_draft.py")},
        "structure_status": verdict["status"], "contrast_case": case,
        "witnesses": witnesses, "actual_final_output": final_output,
        "gold_endpoint_probes": final_probes, "local_contrast_supported": passed,
        "experiment_ready": False,
        "remaining": ["Free-text fidelity/naturalness review", "Independent final-contract review",
                      "Full environment and regression checks", "Actual interruption trial"],
        "note": "For clarification the earlier output is one possible interpretation, not unique early GT. Witnesses are handwritten, not agent behavior."
    }
    save(out / "local_audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    result = audit(args.run.resolve())
    print({"local_contrast_supported": result["local_contrast_supported"], "experiment_ready": False})
    raise SystemExit(0 if result["local_contrast_supported"] else 1)
