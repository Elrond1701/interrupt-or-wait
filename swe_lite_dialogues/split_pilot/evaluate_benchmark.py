"""Prepare, run and summarize final-only SWE-bench scoring, outside the solver.

No generation/model calls. A subset must be explicit; missing predictions cannot
silently change the denominator. Empty patches are counted even though the
official harness skips them. Scores retain the installed official grader's rules.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import uuid

from benchmark_data import load_candidates, write_jsonl
from model_pilot import ROOT, digest, encoded, read_json, save


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def prepare(dataset, predictions, condition, output, instance_ids=None, python=None):
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    if condition not in ("full", "wait", "interrupt"):
        raise ValueError("Unknown condition")
    records = load_candidates(dataset)
    indexed = {r["group_id"]: r for r in records}
    if len(indexed) != len(records):
        raise ValueError("Final scoring requires one dialogue per original")
    ids = sorted(indexed if instance_ids is None else instance_ids)
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(indexed):
        raise ValueError("Empty, duplicate or unknown selected IDs")
    preds = jsonl(predictions)
    if (any(not isinstance(p, dict) or set(p) != {"instance_id", "model_name_or_path", "model_patch"}
            or not isinstance(p["instance_id"], str) or not isinstance(p["model_patch"], str)
            or not isinstance(p["model_name_or_path"], str) for p in preds)
            or len(preds) != len(ids) or sorted(p["instance_id"] for p in preds) != ids):
        raise ValueError("Provide exactly one prediction per selected ID; use an empty string for no patch")
    models = {p["model_name_or_path"] for p in preds}
    if len(models) != 1:
        raise ValueError("One model and condition per evaluation job")
    model = next(iter(models))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-/]*", model) or any(p in ("", ".", "..") for p in model.split("/")):
        raise ValueError("Use a simple model label, optionally organization/model")
    sources = jsonl(dataset / "evaluation_sources.jsonl")
    originals = {r["instance_id"]: r for r in sources}
    if len(originals) != len(sources) or set(originals) != set(indexed):
        raise ValueError("Scoring rows must match the whole frozen dataset")
    for iid in ids:
        if hashlib.sha256(encoded(originals[iid])).hexdigest() != indexed[iid]["source"]["row_sha256"]:
            raise ValueError("Original scoring row changed")
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output / "predictions.jsonl", sorted(preds, key=lambda p: p["instance_id"]))
    write_jsonl(output / "evaluation_sources.jsonl", [originals[i] for i in ids])
    run_id = "split-" + condition + "-" + uuid.uuid4().hex[:12]
    interpreter = str(Path(python or ROOT / ".venv-eval/bin/python").absolute())
    command = [interpreter, "-m", "swebench.harness.run_evaluation",
               "--dataset_name", str(output / "evaluation_sources.jsonl"),
               "--predictions_path", str(output / "predictions.jsonl"),
               "--instance_ids", *ids, "--max_workers", "1", "--run_id", run_id,
               "--namespace", "swebench", "--timeout", "1800", "--report_dir", str(output)]
    job = {"schema_version": 1, "visibility": "author_evaluator_only", "condition": condition,
           "scope": "final_only", "dataset": str(dataset), "dataset_manifest_sha256": digest(dataset / "manifest.json"),
           "harness_package": read_json(ROOT / "evaluation_config.json")["harness_package"],
           "model": model, "run_id": run_id, "cwd": str(output), "command": command,
           "files": {n: digest(output / n) for n in ("predictions.jsonl", "evaluation_sources.jsonl")},
           "tasks": [{"instance_id": i, "scenario_id": indexed[i]["scenario_id"],
                      "category": indexed[i]["trajectory_type"], "messages": len(indexed[i]["messages"])} for i in ids],
           "note": "All selected tasks stay in denominator. No early-stage score. Official harness results do not independently validate dialogue semantics."}
    save(output / "job.json", job)
    (output / "run.sh").write_text("#!/bin/sh\nset -eu\ncd " + shlex.quote(str(output)) + "\n" + shlex.join(command) + "\n")
    return job


def checked_job(folder):
    folder = Path(folder).resolve()
    job = read_json(folder / "job.json")
    if str(folder) != job["cwd"]:
        raise ValueError("Job moved; prepare a fresh job with current paths")
    for name, expected in job["files"].items():
        if name not in ("predictions.jsonl", "evaluation_sources.jsonl") or digest(folder / name) != expected:
            raise ValueError("Frozen evaluation input changed")
    if digest(Path(job["dataset"]) / "manifest.json") != job["dataset_manifest_sha256"]:
        raise ValueError("Dataset manifest changed")
    load_candidates(job["dataset"])
    return job


def run(folder):
    folder = Path(folder).resolve()
    job = checked_job(folder)
    # The caller explicitly runs this outside solver workspaces. Docker and
    # original tests are owned by the external official harness.
    with (folder / "harness.log").open("a") as log:
        result = subprocess.run(job["command"], cwd=folder, stdout=log, stderr=subprocess.STDOUT)
    save(folder / "execution.json", {"job_sha256": digest(folder / "job.json"), "exit_code": result.returncode})
    return summarize(folder)


def summarize(folder):
    folder = Path(folder).resolve()
    job = checked_job(folder)
    preds = {p["instance_id"]: p for p in jsonl(folder / "predictions.jsonl")}
    sources = {r["instance_id"]: r for r in jsonl(folder / "evaluation_sources.jsonl")}
    results = []
    for task in job["tasks"]:
        iid = task["instance_id"]
        item = {**task, "resolved": False}
        report_path = folder / "logs/run_evaluation" / job["run_id"] / job["model"].replace("/", "__") / iid / "report.json"
        if not preds[iid]["model_patch"].strip():
            item["status"] = "empty_patch"
        elif not report_path.exists():
            item["status"] = "missing_report"
        else:
            try:
                report = read_json(report_path)[iid]
                if type(report["resolved"]) is not bool:
                    raise ValueError("resolved must be boolean")
                tests = report.get("tests_status", {})
                for group in ("FAIL_TO_PASS", "PASS_TO_PASS"):
                    expected = sources[iid][group]
                    expected = json.loads(expected) if isinstance(expected, str) else expected
                    passed, failed = tests[group]["success"], tests[group]["failure"]
                    if (not isinstance(passed, list) or not isinstance(failed, list)
                            or Counter(passed + failed) != Counter(expected)):
                        raise ValueError("Test inventory incomplete")
                expected_resolved = bool(tests["FAIL_TO_PASS"]["success"]) and not any(
                    tests[g]["failure"] for g in ("FAIL_TO_PASS", "PASS_TO_PASS"))
                if expected_resolved != report["resolved"]:
                    raise ValueError("Resolution inconsistent with original test results")
                item.update(status="resolved" if report["resolved"] else "test_failed", resolved=report["resolved"],
                            report_sha256=digest(report_path), tests_status=tests)
            except (ValueError, KeyError, TypeError) as exc:
                item.update(status="incomplete_or_invalid_report", detail=str(exc))
        results.append(item)

    def counts(items):
        n = len(items)
        resolved = sum(r["resolved"] for r in items)
        pending = sum(r["status"] in ("missing_report", "incomplete_or_invalid_report") for r in items)
        return {"requested": n, "resolved": resolved, "unscored": pending,
                "resolved_over_requested": resolved / n if n else None,
                "complete": pending == 0, "status_counts": dict(Counter(r["status"] for r in items))}

    result = {"scope": "final_only", "condition": job["condition"], "model": job["model"],
              "job_sha256": digest(folder / "job.json"), "overall": counts(results),
              "by_category": {k: counts([r for r in results if r["category"] == k]) for k in sorted({r["category"] for r in results})},
              "by_messages": {str(k): counts([r for r in results if r["messages"] == k]) for k in sorted({r["messages"] for r in results})},
              "tasks": results,
              "note": "If unscored > 0, resolved/requested is provisional, not a completed benchmark score. Empty patches count as failures. Original grader behavior is retained; report completeness is not an independent raw-log audit."}
    save(folder / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--dataset", type=Path, required=True)
    prep.add_argument("--predictions", type=Path, required=True)
    prep.add_argument("--condition", choices=("full", "wait", "interrupt"), required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--instance-ids", nargs="+")
    prep.add_argument("--python", type=Path)
    for op in ("run", "summarize"):
        sub.add_parser(op).add_argument("--job", type=Path, required=True)
    args = parser.parse_args()
    if args.op == "prepare":
        job = prepare(args.dataset, args.predictions, args.condition, args.output, args.instance_ids, args.python)
        print(json.dumps({"requested": len(job["tasks"]), "job": str(args.output / "job.json"), "executed": False}))
    else:
        report = (run if args.op == "run" else summarize)(args.job)
        print(json.dumps(report["overall"]))


if __name__ == "__main__":
    main()
