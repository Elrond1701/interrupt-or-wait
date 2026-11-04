"""Export reviewed development candidates and prepare original-harness predictions.

All dataset/evaluator artifacts stay outside solver workspaces. Only
released_message() projects the single message due to the solver.
No model calls, Docker execution, or benchmark-ready claims.
"""

import argparse
import hashlib
import json
from pathlib import Path
import uuid

from model_pilot import ROOT, read_json, save, digest, encoded
from fixed_trajectory import check_fixed, contract_for
from multistage_trajectory import check_multistage, load_plan, environment_link

REVIEW_CHECKS = {"initial_matches_plan", "update_matches_plan", "final_goal_preserved",
                 "no_future_choice_in_initial", "natural_and_actionable"}
V6_REVIEW_CHECKS = REVIEW_CHECKS | {'every_stage_matches_plan', 'no_future_choice_before_release',
                                   'explicit_replacements_at_each_revision'}


def candidate_from_run(out, rows):
    out = Path(out).resolve()
    plan, draft = read_json(out / "plan.json"), read_json(out / "draft.json")
    execution = read_json(out / "result.json")
    if execution.get("exit_code") != 0 or execution.get("completed_turns") != 1:
        raise ValueError("No completed successful drafting turn")
    mode = plan['request']['input'].get('draft_mode')
    if mode not in ('fixed_stages', 'fixed_multistage'):
        raise ValueError("Exporter requires a v5/v6 fixed-stage run")
    multistage = mode == 'fixed_multistage'
    row = rows[plan["instance_id"]]
    result = (check_multistage if multistage else check_fixed)(draft, row, plan["request"])
    if result["status"] != "draft_requires_semantic_review":
        raise ValueError("No proposed scenario")
    local = read_json(out / "local_audit.json")
    if not local["local_contrast_supported"] or not local["base_fails_final"] or not local["gold_passes_final"]:
        raise ValueError("Required local probes failed")
    required = {str((out / "draft.json").relative_to(ROOT)), str((out / "plan.json").relative_to(ROOT)),
                "fixed_contracts.json", "data/lite_snapshot.json.gz"}
    required |= {'multistage_plans.json', 'multistage_trajectory.py'} if multistage else {'audit_fixed.py'}
    if not required <= set(local["input_hashes"]):
        raise ValueError("Missing local evidence hashes")
    for name, expected in local["input_hashes"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != expected:
            raise ValueError("Stale local evidence: " + name)
    review = read_json(out / "semantic_review.json")
    for key, file in [("draft_sha256", out / "draft.json"), ("plan_sha256", out / "plan.json"),
                      ("contract_sha256", ROOT / "fixed_contracts.json")]:
        if review.get(key) != digest(file):
            raise ValueError("Stale semantic review")
    if multistage and review.get('stage_plan_sha256') != digest(ROOT / 'multistage_plans.json'):
        raise ValueError('Stale multistage semantic review')
    review_checks = V6_REVIEW_CHECKS if multistage else REVIEW_CHECKS
    if (review.get("verdict") != "accept_for_development" or
            not all(review.get("checks", {}).get(k) is True for k in review_checks)):
        raise ValueError("Semantic review is missing required passes or holds this draft")
    if review["wording_edits"] == 0 and draft != read_json(out / "answer.txt"):
        raise ValueError("Unedited draft differs from the saved model answer")
    environment = None
    if multistage:
        trajectory = plan['request']['input']['trajectory_id']
        _, contract, _, _ = load_plan(row, trajectory)
        environment, _ = environment_link(row, trajectory)
        if local.get('environment_evidence') != environment:
            raise ValueError('Stage environment evidence differs from current mapping')
        kind = result['update_type']
    else:
        kind = plan["request"]["input"]["update_type"]
        trajectory = kind
        contract = contract_for(row, kind)
    version = 'v6' if multistage else 'v5'
    source_id = row["instance_id"]
    record = {
        "schema_version": "0.3" if multistage else "0.2", "visibility": "author_controller_only",
        "scenario_id": source_id + "." + trajectory + '.' + version + '.' + plan["request_sha256"][:8],
        "group_id": source_id, "split": "development", "update_type": kind,
        "source": {"dataset": "princeton-nlp/SWE-bench_Lite", "split": "test",
                   "instance_id": source_id, "repo": row["repo"], "base_commit": row["base_commit"],
                   "snapshot_sha256": digest(ROOT / "data/lite_snapshot.json.gz"),
                   "row_sha256": hashlib.sha256(encoded(row)).hexdigest()},
        "messages": result["author_preview"], "stage_annotations": result["state_trace"],
        "final_requirement_ids": result["state_trace"][-1]["active_ids"],
        "full_prompt": contract["final_summary_en"],
        "evaluation": {"kind": "swebench_original_tests", "original_instance_id": source_id,
                       "harness_package": read_json(ROOT / "evaluation_config.json")["harness_package"],
                       "source_file": "evaluation_sources.jsonl", "full_environment_validated": bool(environment)},
        "validation": {"status": ('environment_checked_pending_independent_review_and_agent' if environment
                                   else "offline_checked_pending_full_validation"),
                       "local_probes": 'frozen_environment_evidence_rechecked' if environment else "passed",
                       "semantic_review": review["reviewer"], "independent_human_review": False,
                       "experiment_ready": False},
        "provenance": {"run": str(out.relative_to(ROOT)), "draft_sha256": digest(out / "draft.json"),
                       "review_sha256": digest(out / "semantic_review.json"),
                       "annotation_origin": "fixed_author_plan",
                       "wording_origin": "codex_unedited" if review["wording_edits"] == 0 else "assistant_revised",
                       "wording_edits": review["wording_edits"]},
    }
    if multistage:
        record.update(n_messages=len(record['messages']), n_updates=len(record['messages']) - 1,
                      update_types=result['update_types'], trajectory_id=trajectory)
        record['evaluation']['stage_checks'] = environment['stages']
        record['evaluation']['environment_evidence'] = environment
        record['provenance']['stage_plan_sha256'] = digest(ROOT / 'multistage_plans.json')
    return record


def released_message(record, index):
    """One due user message only. The future runner owns timing/order enforcement."""
    if type(index) is not int or index < 0 or index >= len(record["messages"]):
        raise ValueError("Unknown message index")
    return {"role": "user", "content": record["messages"][index]["content"]}


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))


def load_candidates(folder):
    folder = Path(folder)
    manifest = read_json(folder / "manifest.json")
    for name in ("candidates.jsonl", "evaluation_sources.jsonl"):
        if digest(folder / name) != manifest["files"][name]:
            raise ValueError("Exported dataset changed; rebuild after review")
    return [json.loads(line) for line in (folder / "candidates.jsonl").read_text().splitlines()]


def build(runs, output):
    rows = {r["instance_id"]: r for r in read_json(ROOT / "data/lite_snapshot.json.gz")["instances"]}
    candidates, excluded, seen = [], [], set()
    for run in runs:
        try:
            record = candidate_from_run(run, rows)
            if record["scenario_id"] in seen:
                raise ValueError("Duplicate scenario")
            seen.add(record["scenario_id"])
            candidates.append(record)
        except (ValueError, KeyError, OSError) as error:
            excluded.append({"run": str(run), "reason": str(error)})
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output / "candidates.jsonl", candidates)
    source_ids = sorted({r["group_id"] for r in candidates})
    write_jsonl(output / "evaluation_sources.jsonl", [rows[key] for key in source_ids])
    manifest = {"visibility": "author_controller_and_external_evaluator_only",
                "candidate_count": len(candidates), "original_task_count": len(source_ids),
                "message_count_distribution": {str(n): sum(len(r['messages']) == n for r in candidates) for n in (2, 3)},
                "environment_validated_original_task_count": len({r['group_id'] for r in candidates
                                                                    if r['evaluation']['full_environment_validated']}),
                "experiment_ready_count": 0, "excluded": excluded,
                "files": {name: digest(output / name) for name in ("candidates.jsonl", "evaluation_sources.jsonl")},
                "evaluation_config": read_json(ROOT / "evaluation_config.json"),
                "note": "Development candidates, not a benchmark release. Future messages and evaluator sources must stay outside solver workspaces."}
    save(output / "manifest.json", manifest)
    return manifest


def prepare_prediction(record, model_patch, model_name, condition, sources, output):
    if condition not in ("full", "wait", "interrupt"):
        raise ValueError("Unknown condition")
    if not isinstance(model_patch, str) or not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("Expected patch text and model name")
    source_rows = [json.loads(line) for line in Path(sources).read_text().splitlines()]
    matched = [r for r in source_rows if r["instance_id"] == record["source"]["instance_id"]]
    if len(matched) != 1 or hashlib.sha256(encoded(matched[0])).hexdigest() != record["source"]["row_sha256"]:
        raise ValueError("Evaluation source does not match the frozen original")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    prediction = {"instance_id": matched[0]["instance_id"], "model_name_or_path": model_name, "model_patch": model_patch}
    write_jsonl(output / "predictions.jsonl", [prediction])
    run_id = "pilot-" + hashlib.sha256(record["scenario_id"].encode()).hexdigest()[:10] + "-" + condition + "-" + uuid.uuid4().hex[:8]
    command = ["python", "-m", "swebench.harness.run_evaluation", "--dataset_name", str(Path(sources).resolve()),
               "--predictions_path", str(output / "predictions.jsonl"), "--instance_ids", prediction["instance_id"],
               "--max_workers", "1", "--run_id", run_id]
    job = {"scenario_id": record["scenario_id"], "condition": condition, "run_id": run_id,
           "harness_package": record["evaluation"]["harness_package"], "command": command,
           "executed": False, "source_sha256": digest(Path(sources)),
           "note": "One scenario/condition per prediction file; repeated source IDs cannot overwrite other variants. Empty patches are retained as failed attempts."}
    save(output / "evaluation_job.json", job)
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    export = sub.add_parser("build")
    export.add_argument("--runs", nargs="+", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    pred = sub.add_parser("prediction")
    pred.add_argument("--dataset", type=Path, required=True)
    pred.add_argument("--scenario-id", required=True)
    pred.add_argument("--patch", type=Path, required=True)
    pred.add_argument("--model", required=True)
    pred.add_argument("--condition", choices=("full", "wait", "interrupt"), required=True)
    pred.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "build":
        result = build(args.runs, args.output)
        print(json.dumps({k: result[k] for k in ("candidate_count", "original_task_count", "experiment_ready_count", "excluded")}))
    else:
        records = load_candidates(args.dataset)
        record = next(r for r in records if r["scenario_id"] == args.scenario_id)
        print(json.dumps(prepare_prediction(record, args.patch.read_text(), args.model, args.condition,
                                            args.dataset / "evaluation_sources.jsonl", args.output)))


if __name__ == "__main__":
    main()
