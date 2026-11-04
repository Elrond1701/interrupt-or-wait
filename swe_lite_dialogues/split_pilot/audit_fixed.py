"""Author-side fixed probes; never executes model-generated code or a full harness."""

import argparse
import ast
import json
from pathlib import Path
import re
import shutil
import tempfile

from model_pilot import ROOT, read_json, save, digest
from fixed_trajectory import check_fixed, contract_for
from audit_trajectory import functions as slug_functions, initial_probes
from verify_split import apply_patch, load_slugify, slugify_checks


def username_regexes(source):
    result = {}
    for cls in ast.parse(source).body:
        if not isinstance(cls, ast.ClassDef) or cls.name not in ("ASCIIUsernameValidator", "UnicodeUsernameValidator"):
            continue
        fields = {n.targets[0].id: n.value for n in cls.body
                  if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
        flag = fields["flags"]
        if isinstance(flag, ast.Constant) and flag.value == 0:
            flags = 0
        elif isinstance(flag, ast.Attribute) and isinstance(flag.value, ast.Name) and flag.value.id == "re" and flag.attr == "ASCII":
            flags = re.ASCII
        else:
            raise ValueError("Unsupported upstream validator flags")
        result[cls.name] = re.compile(ast.literal_eval(fields["regex"]), flags)
    if len(result) != 2:
        raise ValueError("Expected both username validators")
    return result


def username_probes(patterns):
    a, u = "ASCIIUsernameValidator", "UnicodeUsernameValidator"
    cases = {
        "ascii_reject_newline": [(a, "trailingnewline\n", False), (a, "user\n\n", False)],
        "unicode_reject_newline": [(u, "trailingnewline\n", False), (u, "Éric\n", False)],
        "preserve_character_rules": [
            (a, "glenn", True), (a, "a_b.@+-9", True), (a, "Éric", False),
            (a, "jean marc", False), (a, "", False), (a, "o'connell", False),
            (u, "Éric", True), (u, "أحمد", True), (u, "a_b.@+-9", True),
            (u, "jean marc", False), (u, "", False), (u, "zero\u200bwidth", False),
        ],
    }
    return {rid: [{"input": [cls, text], "passed": bool(patterns[cls].search(text)) == expected}
                  for cls, text, expected in probes] for rid, probes in cases.items()}


def run_probes(row, contract, kind):
    p = contract["plans"][kind]
    case = p["contrast_case"]
    if row["instance_id"] == "django__django-12983":
        with tempfile.TemporaryDirectory(prefix="fixed-slug-") as temp:
            fns = slug_functions(Path(temp) / "slug")
            base = load_slugify((ROOT / "vendor/slugify/django/utils/text.py").read_text())
            witness = fns["dash_only" if kind == "addition" else "remove_all_underscores"]
            initial = initial_probes(witness, p["initial_requirement_ids"])
            base_results, gold_results = slugify_checks(base), slugify_checks(fns["gold"])
            earlier, final = witness(case["input"]), fns["gold"](case["input"])
            base_ok = all(g["passed"] == g["total"] for g in base_results.values())
            gold_ok = all(g["passed"] == g["total"] for g in gold_results.values())
        scope = "Extracted plain-string slugify only; lazy strings and full Django tests are not executed."
    elif row["instance_id"] == "django__django-11099":
        with tempfile.TemporaryDirectory(prefix="fixed-username-") as temp:
            directory = Path(temp) / "repo"
            shutil.copytree(ROOT / "vendor/username", directory)
            path = directory / "django/contrib/auth/validators.py"
            base = username_regexes(path.read_text())
            apply_patch(directory, row["patch"])
            gold = username_regexes(path.read_text())
            witness = {**base, "ASCIIUsernameValidator": gold["ASCIIUsernameValidator"]}
            witness_results = username_probes(witness)
            initial = {rid: all(x["passed"] for x in witness_results[rid]) for rid in p["initial_requirement_ids"]}
            base_results, gold_results = username_probes(base), username_probes(gold)
            probe = json.loads(case["input"])
            outcome = lambda pats: "accepted" if pats[probe["validator"]].search(probe["value"]) else "rejected"
            earlier, final = outcome(witness), outcome(gold)
            base_ok = all(x["passed"] for group in base_results.values() for x in group)
            gold_ok = all(x["passed"] for group in gold_results.values() for x in group)
        scope = "Upstream regexes and flags with re.search on plain strings; no full Django objects/help-text/regression suite."
    else:
        raise ValueError("No local auditor for this source instance")
    passed = (all(initial.values()) and not base_ok and gold_ok and earlier != final
              and earlier == case["earlier_output"] and final == case["final_output"])
    return {"scope": scope, "initial_requirement_probes": initial,
            "base_probes": base_results, "gold_probes": gold_results,
            "base_fails_final": not base_ok, "gold_passes_final": gold_ok,
            "contrast_case": case, "actual_earlier_output": earlier, "actual_final_output": final,
            "local_contrast_supported": passed, "experiment_ready": False,
            "note": "Handwritten witness, not agent behavior; clarification has no unique early GT. Model does not generate these probes."}


def audit_fixed(out, row=None):
    out = Path(out).resolve()
    plan, draft = read_json(out / "plan.json"), read_json(out / "draft.json")
    if row is None:
        row = next(r for r in read_json(ROOT / "data/lite_snapshot.json.gz")["instances"] if r["instance_id"] == plan["instance_id"])
    check_fixed(draft, row, plan["request"])
    if draft["decision"] != "propose_split":
        raise ValueError("No proposed wording to audit")
    kind = plan["request"]["input"]["update_type"]
    contract = contract_for(row, kind)
    for filename, expected in contract["vendor_hashes"].items():
        if digest(ROOT / filename) != expected:
            raise ValueError("Upstream local source changed")
    report = run_probes(row, contract, kind)
    files = [out / "plan.json", out / "draft.json", ROOT / "fixed_contracts.json",
             ROOT / "fixed_trajectory.py", ROOT / "audit_fixed.py", ROOT / "audit_trajectory.py",
             ROOT / "trajectory_draft.py", ROOT / "verify_split.py", ROOT / "author_reference.json",
             ROOT / "trajectory_schema.json", ROOT / "phrasing_schema.json", ROOT / "data/lite_snapshot.json.gz"]
    files += [ROOT / name for name in contract["vendor_hashes"]]
    report["input_hashes"] = {str(p.relative_to(ROOT)): digest(p) for p in files}
    save(out / "local_audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    result = audit_fixed(parser.parse_args().run)
    print(json.dumps({k: result[k] for k in ("base_fails_final", "gold_passes_final", "local_contrast_supported", "experiment_ready")}))
    raise SystemExit(0 if result["local_contrast_supported"] else 1)
