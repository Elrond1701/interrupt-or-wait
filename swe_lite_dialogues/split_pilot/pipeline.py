"""Offline authoring pipeline: inventory -> annotations -> messages -> gates.

Uses the pinned local snapshot, no network, models, or execution of dataset code.
It compiles explicitly annotated requirements; it does not infer their semantics.
Run: python3 split_pilot/pipeline.py
"""

import argparse
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def read_json(path):
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_names(row, key):
    value = row.get(key, [])
    value = json.loads(value) if isinstance(value, str) else value
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"{row['instance_id']}: invalid {key}")
    return value


def inventory(rows):
    """Structural signals only: one test name does not imply one requirement."""
    entries = []
    for row in rows:
        statement = row["problem_statement"]
        test_patch = row.get("test_patch", "")
        added = "\n".join(line[1:] for line in test_patch.splitlines()
                          if line.startswith("+") and not line.startswith("+++"))
        ftp = test_names(row, "FAIL_TO_PASS")
        ptp = test_names(row, "PASS_TO_PASS")
        flags = []
        if len(ftp) == 1:
            flags.append("single_test_name_inspect_assertions")
        if not ptp:
            flags.append("no_named_regression_tests_review_coverage")
        if re.search(r"the (?:fix|patch)|can be fixed|regex could be changed", statement, re.I):
            flags.append("possible_solution_hint_manual_review")
        entries.append({
            "source_instance_id": row["instance_id"],
            "repo": row["repo"], "base_commit": row["base_commit"],
            "title": statement.splitlines()[0],
            "statement_words": len(statement.split()),
            "fail_to_pass_count": len(ftp), "pass_to_pass_count": len(ptp),
            "new_test_functions": re.findall(r"^\s*def (test_\w+)\(", added, re.M),
            "added_assertion_lines": sum(
                bool(re.search(r"\bassert\b|assert[A-Z_]", line))
                for line in added.splitlines()
            ),
            "review_flags": flags,
            "status": "needs_requirement_annotation",
        })
    # Spread manual inspection across repositories. This is not a quality score.
    buckets = defaultdict(deque)
    for item in sorted(entries, key=lambda x: x["source_instance_id"]):
        buckets[item["repo"]].append(item["source_instance_id"])
    queue = []
    while any(buckets.values()):
        for repo in sorted(buckets):
            if buckets[repo]:
                queue.append(buckets[repo].popleft())
    return {
        "instance_count": len(entries),
        "repository_counts": dict(sorted(Counter(e["repo"] for e in entries).items())),
        "single_fail_to_pass_count": sum(e["fail_to_pass_count"] == 1 for e in entries),
        "notes": [
            "Counts and flags are inspection aids, not semantic suitability decisions.",
            "New assertion lines include helpers/comments; they are not independent requirements.",
            "The round-robin queue balances review order only, not the final sample.",
        ],
        "suggested_annotation_order": queue, "instances": entries,
    }


def lookup(value, path):
    for key in path:
        value = value[key]
    return value


def compile_spec(spec, row):
    """Validate referential integrity, then render only released requirements."""
    if spec["base_commit"] != row["base_commit"]:
        raise ValueError("base_commit does not match the source instance")
    requirements = spec["requirements"]
    by_id = {r["id"]: r for r in requirements}
    if not requirements or len(by_id) != len(requirements):
        raise ValueError("Requirement IDs must be unique and nonempty")
    for requirement in requirements:
        if not isinstance(requirement["id"], str) or not requirement["id"].strip():
            raise ValueError("Empty requirement ID")
        if not requirement["text_en"].strip() or not requirement.get("probe_path"):
            raise ValueError(f"{requirement['id']}: missing text or test mapping")
        if requirement.get("construction") not in {
            "source_rewrite", "test_aligned_rewrite", "synthetic_initial", "composed_inference",
        }:
            raise ValueError("Unknown requirement construction type")
        spans = requirement.get("source_spans", [])
        if not spans and requirement["construction"] != "synthetic_initial":
            raise ValueError(f"{requirement['id']}: source evidence missing")
        if requirement["construction"] == "synthetic_initial" and not requirement.get("note"):
            raise ValueError("Synthetic requirements must explain their construction")
        for span in spans:
            if span["field"] not in ("problem_statement", "test_patch"):
                raise ValueError("Requirement evidence must not come from the solution patch")
            if not span["quote"] or span["quote"] not in row.get(span["field"], ""):
                raise ValueError(f"{requirement['id']}: source quote not found")
        if not set(requirement.get("depends_on", [])) <= set(by_id):
            raise ValueError("Unknown dependency")

    visiting, visited = set(), set()

    def visit(rid):
        if rid in visiting:
            raise ValueError("Cyclic requirement dependency")
        if rid in visited:
            return
        visiting.add(rid)
        for parent in by_id[rid].get("depends_on", []):
            visit(parent)
        visiting.remove(rid)
        visited.add(rid)

    for rid in by_id:
        visit(rid)

    active, introduced, rendered = set(), set(), []
    stages = spec["stages"]
    if len(stages) < 2:
        raise ValueError("An interruption scenario needs U0 and at least one update")
    for index, stage in enumerate(stages):
        if stage["id"] != f"U{index}":
            raise ValueError("Messages must be contiguous U0, U1, ...")
        add, remove = stage["add"], stage.get("remove", [])
        if len(add) != len(set(add)) or len(remove) != len(set(remove)):
            raise ValueError("Duplicate stage requirement")
        if set(add) & set(remove):
            raise ValueError("Removing and readding the same requirement is a no-op")
        if not add and not remove:
            raise ValueError("Empty update")
        if not set(add) <= set(by_id) or not set(remove) <= active:
            raise ValueError("Stage references unknown or inactive requirements")
        if set(add) & (active - set(remove)):
            raise ValueError("Repeating an active requirement is not a new update")
        if index == 0 and (not add or remove):
            raise ValueError("U0 must introduce a nonempty initial task")
        active = (active - set(remove)) | set(add)
        introduced.update(add)
        for rid in active:
            if not set(by_id[rid].get("depends_on", [])) <= active:
                raise ValueError(f"{rid}: dependency absent from effective requirements")
        chunks = [spec["context_en"]] if index == 0 else ["Update the requirements for the current task."]
        if remove:
            chunks.append("The following earlier requirements no longer apply:")
            chunks.extend("- " + by_id[rid]["text_en"] for rid in remove)
        if add:
            chunks.append("Apply these requirements:")
            chunks.extend("- " + by_id[rid]["text_en"] for rid in add)
        rendered.append({
            "id": stage["id"], "content": "\n".join(chunks),
            "added_requirement_ids": add, "removed_requirement_ids": remove,
            "effective_requirement_ids": sorted(active),
        })
    target = spec["final_requirement_ids"]
    if not target or len(target) != len(set(target)) or active != set(target):
        raise ValueError("Final effective requirements do not equal the declared target")
    if introduced != set(by_id):
        raise ValueError("Annotated requirements are never introduced")
    if any(by_id[rid]["construction"] == "synthetic_initial" for rid in target):
        raise ValueError("Synthetic initial requirement remains in the original final target")
    roles = spec["evidence_roles"]
    witnesses = roles["update_witnesses"]
    if set(witnesses) != {s["id"] for s in stages[1:]}:
        raise ValueError("Every update needs an initial-pass/next-stage-fail witness pair")
    checks = set(spec["evidence_checks"])
    if not {roles["base_fails_final"], roles["gold_passes_final"]} <= checks:
        raise ValueError("Base and gold validation must be included")
    for pair in witnesses.values():
        if len(pair) != 2 or pair[0] == pair[1] or not set(pair) <= checks:
            raise ValueError("Invalid update witness evidence mapping")
    return {
        "scenario_id": spec["scenario_id"], "source_instance_id": row["instance_id"],
        "base_commit": row["base_commit"],
        "construction_types": sorted({r["construction"] for r in requirements}),
        "initial_message": rendered[0], "updates": rendered[1:],
        "final_requirement_ids": target,
        "full_prompt": spec["context_en"] + "\n" + "\n".join("- " + by_id[rid]["text_en"] for rid in target),
    }


def evidence_freshness(report, root):
    hashes = report.get("input_hashes", {})
    required = {"verify_split.py", "author_reference.json", "task_cards.json", "requirements.json"}
    errors = [f"missing evidence input hash: {name}" for name in sorted(required - set(hashes))]
    if not any(name.startswith("vendor/") for name in hashes):
        errors.append("missing vendor hashes")
    for name, expected in hashes.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            errors.append(f"evidence path outside author directory: {name}")
        elif not path.is_file() or digest(path) != expected:
            errors.append(f"stale evidence: {name}")
    return errors


def evaluate_spec(spec, row, report, freshness_errors):
    try:
        compiled = compile_spec(spec, row)
    except (ValueError, KeyError, TypeError) as e:
        return {"scenario_id": spec.get("scenario_id"), "status": "invalid_annotation", "reasons": [str(e)]}
    result = {
        **compiled, "review_status": spec.get("review_status", "unreviewed"),
        "status": "await_local_evidence", "reasons": [],
        "scope": "Author preview only; no experiment-ready or semantic-equivalence claim.",
    }
    if freshness_errors:
        result["reasons"] = freshness_errors
        return result
    checks = spec.get("evidence_checks", [])
    missing = [name for name in checks if name not in report.get("checks", {})]
    if not checks or missing:
        result["reasons"] = ["Required runtime evidence absent", *missing]
        return result
    failed = [name for name in checks if report["checks"][name] is not True]
    # Check every active final requirement's declared probe group.
    for requirement in spec["requirements"]:
        try:
            group = lookup(report, requirement["probe_path"])
            if not isinstance(group["total"], int) or group["total"] <= 0:
                raise ValueError("Empty probe group")
            if requirement["id"] in spec["final_requirement_ids"] and group["passed"] != group["total"]:
                failed.append("final_requirement:" + requirement["id"])
        except (KeyError, TypeError, ValueError):
            result["reasons"] = ["Unresolved test mapping: " + requirement["id"]]
            return result
    if failed:
        result["status"] = "hold_failed_evidence"
        result["reasons"] = sorted(set(failed))
    else:
        result["status"] = "ready_for_full_validation"
        result["next_gates"] = [
            "Independent review of source meaning, naturalness, and final-spec equivalence.",
            "Full repository base/gold and regression validation.",
            "Agent smoke run to check actual interruption opportunities.",
        ]
    return result


def build(snapshot, annotations, evidence, root):
    rows = snapshot["instances"]
    by_id = {r["instance_id"]: r for r in rows}
    if len(rows) != len(by_id):
        raise ValueError("Duplicate source instance")
    specs = annotations["scenarios"]
    if len({s["scenario_id"] for s in specs}) != len(specs):
        raise ValueError("Duplicate scenario ID")
    # Bind runtime references to the actual snapshot, rather than only their IDs.
    references = {r["instance_id"]: r for r in read_json(root / "author_reference.json")["instances"]}
    freshness = evidence_freshness(evidence, root)
    result = []
    for spec in specs:
        row = by_id.get(spec["source_instance_id"])
        if row is None:
            result.append({"scenario_id": spec["scenario_id"], "status": "invalid_annotation", "reasons": ["Unknown source instance"]})
            continue
        problems = list(freshness)
        if references.get(row["instance_id"]) != row:
            problems.append("Runtime source reference differs from snapshot")
        result.append(evaluate_spec(spec, row, evidence, problems))
    return {
        "schema_version": "0.1", "visibility": "author_only",
        "pipeline_scope": "Deterministic inventory, compilation of assistant-authored annotations, and local evidence gates. No automatic semantic sharding, models, or Docker.",
        "source_instances": len(rows),
        "annotated_original_instances": len({s["source_instance_id"] for s in specs}),
        "scenario_status_counts": dict(Counter(s["status"] for s in result)),
        "experiment_ready_count": 0,
        "scenarios": result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=ROOT / "data/lite_snapshot.json.gz")
    parser.add_argument("--annotations", type=Path, default=ROOT / "requirements.json")
    parser.add_argument("--evidence", type=Path, default=ROOT / "verification_report.json")
    parser.add_argument("--output", type=Path, default=ROOT / "pipeline_output")
    args = parser.parse_args()
    # Evidence is bound to the canonical annotations; alternate inputs need revalidation.
    evidence = read_json(args.evidence)
    if digest(args.annotations) != evidence.get("input_hashes", {}).get("requirements.json"):
        evidence = dict(evidence, input_hashes={})
    snapshot = read_json(args.snapshot)
    summary = build(snapshot, read_json(args.annotations), evidence, ROOT)
    summary["input_hashes"] = {
        "snapshot": digest(args.snapshot), "annotations": digest(args.annotations),
        "evidence": digest(args.evidence), "pipeline": digest(Path(__file__)),
    }
    review_inventory = inventory(snapshot["instances"])
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in [("inventory.json", review_inventory), ("compiled_scenarios.json", summary)]:
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "source_instances": summary["source_instances"],
        "single_fail_to_pass_count": review_inventory["single_fail_to_pass_count"],
        "annotated_original_instances": summary["annotated_original_instances"],
        "scenario_status_counts": summary["scenario_status_counts"],
        "experiment_ready_count": 0,
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    if any(s["status"] == "invalid_annotation" for s in summary["scenarios"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
