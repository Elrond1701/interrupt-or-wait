"""Acceptance checks for a saved development dataset; no new model calls.

Rebuild reviewed construction evidence, simulate ordered message delivery, and
check original evaluation inputs. Optional harness checks need .venv-eval and
may fetch pinned repository requirements. All outputs are author-side only.
This is not a live solver experiment or validation of every task environment.
"""

import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path

from benchmark_data import load_candidates, prepare_prediction, released_message
from delivery import Delivery
from model_pilot import ROOT, digest, read_json, save
from pipeline import test_names
from source_dataset import export_dataset, extraction_source, rows_by_id, select_primary


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_calls(record):
    """Verify real saved call evidence without claiming a fresh generation."""
    run = ROOT / record["provenance"]["run"]
    if not run.is_relative_to(ROOT / "source_runs"):
        # select_primary already checks the frozen legacy drafting evidence.
        return 1
    contract = ROOT / read_json(run / "contract_link.json")["directory"]
    request = read_json(contract / "extraction/request.json")["input"]
    row = rows_by_id()[record["source"]["instance_id"]]
    seed = read_json(contract / "seed_link.json") if (contract / "seed_link.json").exists() else None
    expected, _ = extraction_source(row, ROOT / seed["directory"] if seed else None,
                                    bool(seed and seed.get("mode") == "scope_partition"),
                                    seed.get("scope_hints") if seed else None)
    require(request == expected,
            "Extraction input contains extra data or differs from the original issue")
    for folder in (contract, run):
        for name, expected in read_json(folder / "manifest.json")["input_hashes"].items():
            require(digest(folder / "inputs" / name) == expected, "Changed source snapshot: " + name)
    for folder in (contract / "extraction", run / "planning", run / "wording"):
        result = read_json(folder / "result.json")
        require(result["exit_code"] == 0 and not result["timed_out"] and result["reported_usages"],
                "Missing completed model call: " + str(folder))
    if seed and (ROOT / seed["directory"] / "endpoint_only.json").exists():
        endpoint = ROOT / seed["directory"]
        require(read_json(endpoint / "extraction/request.json")["input"] == extraction_source(row)[0],
                "Neutral endpoint extraction contains category hints or evaluator data")
        for name, expected in read_json(endpoint / "manifest.json")["input_hashes"].items():
            require(digest(endpoint / "inputs" / name) == expected, "Changed endpoint snapshot: " + name)
        result = read_json(endpoint / "extraction/result.json")
        require(result["exit_code"] == 0 and not result["timed_out"] and result["reported_usages"],
                "Missing neutral endpoint extraction call")
        return 4
    return 3


def check_delivery(record):
    """A scripted round-end submission tests delivery, not task-solving quality."""
    controller = Delivery(record, "wait")
    for index, message in enumerate(record["messages"]):
        visible = [m for m in controller.visible_history() if m["role"] == "user"]
        expected = [released_message(record, j) for j in range(index + 1)]
        require(visible == expected, "Missing, reordered, or prematurely released message")
        require(visible[-1] == {"role": "user", "content": message["content"]},
                "Author metadata entered the public message")
        controller.accept({"action": "submit", "command": "", "text": "Scripted delivery check only."})
    require(controller.status == "completed", "Round-based delivery did not terminate")
    return {"scenario_id": record["scenario_id"], "scripted_not_solver": True,
            "released_stages": [e["stage"] for e in controller.events if e["event"] == "delivery"]}


def check_dataset(dataset, output, harness=False, docker_evidence=None, require_three_majority=False):
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    require(output.is_relative_to(ROOT / "pipeline_output"), "Keep acceptance outputs author-side")
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "running", "visibility": "author_only", "dataset": str(dataset),
              "new_model_calls": 0, "new_solver_runs": 0, "checks": {},
              "scope": "Saved real generation evidence, construction replay, scripted delivery, evaluation compatibility."}
    try:
        records = load_candidates(dataset)
        selected, excluded = select_primary(records)
        require(records and len(selected) == len(records) and not excluded,
                "One or more records failed reviewed construction replay")
        ids = [r["source"]["instance_id"] for r in records]
        require(len(ids) == len(set(ids)), "Duplicate original task")
        if require_three_majority:
            count = sum(r["n_messages"] == 3 for r in records)
            passed = count * 2 > len(records)
            report["checks"]["three_message_majority"] = {
                "passed": passed, "three_message_conversations": count, "total_conversations": len(records),
                "rule": "Strictly more than half; count selected original tasks, not variants."}
            require(passed, "Three-message conversations must be strictly more than half of the dataset")
        originals = rows_by_id()
        sources = [json.loads(line) for line in (dataset / "evaluation_sources.jsonl").read_text().splitlines()]
        require(len(sources) == len(records) and {r["instance_id"] for r in sources} == set(ids),
                "Missing or duplicate original scoring rows")
        require(all(row == originals[row["instance_id"]] for row in sources), "Original scoring row changed")
        calls = 0
        for record in records:
            final = record["stage_annotations"][-1]
            require(not final["unresolved"] and set(final["active_ids"]) == set(record["final_requirement_ids"]),
                    "Final effective requirements do not match the reviewed endpoint")
            calls += check_calls(record)
        report["checks"]["reviewed_construction_and_original_scoring_rows"] = {"passed": True, "originals": len(ids),
                                                                                "saved_real_model_calls": calls}

        manifest = export_dataset([], [dataset], output / "rebuilt_dataset")
        for name in ("candidates.jsonl", "evaluation_sources.jsonl", "coverage.json", "examples.md"):
            require((dataset / name).read_bytes() == (output / "rebuilt_dataset" / name).read_bytes(),
                    "Export rebuild differs: " + name)
        # Rebuilding the selected rows cannot reconstruct discarded alternatives.
        # Preserve that selection history and compare all current-data fields.
        original_manifest = read_json(dataset / "manifest.json")
        history = {"excluded", "input_candidate_count"}
        require({k: v for k, v in manifest.items() if k not in history} ==
                {k: v for k, v in original_manifest.items() if k not in history}, "Current-data manifest differs")
        identical = (dataset / "manifest.json").read_bytes() == (output / "rebuilt_dataset/manifest.json").read_bytes()
        report["checks"]["export_rebuild"] = {"passed": True, "byte_identical_files": 4 + int(identical),
                                               "selection_history_preserved_in_original_manifest": not identical}

        delivery = [check_delivery(r) for r in records]
        save(output / "delivery_checks.json", delivery)
        report["checks"]["ordered_delivery"] = {"passed": True, "conversations": len(delivery),
                                                  "message_counts": dict(Counter(str(r["n_messages"]) for r in records)),
                                                  "method": "Scripted round ends; no model, code edits, or interruption experiment."}
        jobs = []
        for record in records:
            instance = record["source"]["instance_id"]
            folder = output / "prediction_checks" / instance
            jobs.append(prepare_prediction(record, originals[instance]["patch"], "author_gold_format_check", "full",
                                           dataset / "evaluation_sources.jsonl", folder))
        require(len({j["run_id"] for j in jobs}) == len(records), "Evaluation job IDs collide")
        report["checks"]["prediction_export"] = {"passed": True, "jobs": len(jobs),
                                                   "method": "Author gold used only to check the adapter; these are not solver outputs."}

        if harness:
            require(importlib.metadata.version("swebench") == "4.1.0", "Use pinned swebench==4.1.0")
            from swebench.harness.utils import get_predictions_from_file, load_swebench_dataset
            from swebench.harness.test_spec.test_spec import make_test_spec
            loaded = load_swebench_dataset(str(dataset / "evaluation_sources.jsonl"))
            require(loaded == sources, "Official loader changed scoring rows")
            specs = []
            for row in loaded:
                instance = row["instance_id"]
                spec = make_test_spec(row, namespace="swebench")
                require(spec.FAIL_TO_PASS == test_names(row, "FAIL_TO_PASS") and
                        spec.PASS_TO_PASS == test_names(row, "PASS_TO_PASS"), "Harness test selection differs")
                prediction_path = output / "prediction_checks" / instance / "predictions.jsonl"
                predictions = get_predictions_from_file(str(prediction_path), str(dataset / "evaluation_sources.jsonl"), "test")
                require(len(predictions) == 1 and predictions[0] == {
                    "instance_id": instance, "model_name_or_path": "author_gold_format_check", "model_patch": row["patch"]},
                    "Official prediction loader differs")
                specs.append({"instance_id": instance, "target_tests": len(spec.FAIL_TO_PASS),
                              "regression_tests": len(spec.PASS_TO_PASS), "environment_executed": False})
            save(output / "harness_checks.json", specs)
            report["checks"]["official_harness_inputs"] = {"passed": True, "tasks": len(specs),
                                                            "method": "Official loaders and TestSpec; not run_evaluation execution."}

        if docker_evidence:
            folder = Path(docker_evidence).resolve()
            evidence = read_json(folder / "summary.json")
            meta = read_json(folder / "manifest.json")
            require(evidence["complete"] and meta["instance_id"] in ids, "Docker anchor did not complete")
            require(read_json(folder / "inputs/source.json") == originals[meta["instance_id"]], "Docker used a different source")
            for name, expected in meta["inputs"].items():
                require(digest(ROOT / name) == expected, "Stale Docker evidence input: " + name)
            require(set(evidence["results"]) == {"base", "gold", "dash_only", "remove_all"}, "Incomplete Docker modes")
            for mode, result in evidence["results"].items():
                require(result["validation_expectations_met"] and all(result["checks"].values()),
                        "Docker validation failed: " + mode)
            report["checks"]["docker_anchor"] = {"passed": True, "instance_id": meta["instance_id"],
                                                   "evidence": str(folder), "summary_sha256": digest(folder / "summary.json"),
                                                   "method": meta["method"], "modes": list(evidence["results"])}
        report.update(status="passed", original_tasks=len(records),
                      environment_validated_originals=manifest["environment_validated_original_task_count"],
                      experiment_ready=False,
                      limitations=["Semantic completeness still relies on saved assistant reviews; no new independent review.",
                                   "Harness compatibility does not execute every task environment.",
                                   "Initial unresolved choices have no unique behavioral GT; new intermediate checks remain pending.",
                                   "No fresh model generation or solver experiment; observed lengths do not establish all-source yield or class balance."])
    except Exception as exc:
        report.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        save(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--harness", action="store_true")
    parser.add_argument("--docker-evidence", type=Path)
    parser.add_argument("--require-three-majority", action="store_true", help="Fail unless more than half of selected originals have three messages")
    args = parser.parse_args()
    result = check_dataset(args.dataset, args.output, args.harness, args.docker_evidence, args.require_three_majority)
    print(json.dumps({k: result[k] for k in ("status", "original_tasks", "checks", "experiment_ready")}))
