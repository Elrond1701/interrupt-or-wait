"""Verify a compact handoff offline. Does not prove semantics or run SWE-bench."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CODE = ROOT / "split_pilot"
sys.path.insert(0, str(CODE))

from benchmark_data import load_candidates, write_jsonl
from delivery import Delivery
from evaluate_benchmark import prepare, summarize
from model_pilot import digest, encoded, read_json
from source_batch import run_batch
from source_dataset import rows_by_id
from trajectory_labels import label_record


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_delivery(record, condition):
    controller = Delivery(record, condition, interrupt_after=1)
    total = 1 if condition == "full" else len(record["messages"])
    for number in range(total):
        users = [m["content"] for m in controller.visible_history() if m["role"] == "user"]
        expected = ([record["full_prompt"]] if condition == "full" else
                    [m["content"] for m in record["messages"][:number + 1]])
        require(users == expected, "Released message history differs from the expected prefix")
        if condition == "interrupt" and number + 1 < total:
            controller.accept({"action": "shell", "command": "not-executed", "text": ""},
                              observation={"output": "scripted"})
        else:
            controller.accept({"action": "submit", "command": "", "text": "Scripted completion"})
    require(controller.status == "completed", "Scripted delivery did not complete")


def main():
    checksums = read_json(ROOT / "CHECKSUMS.json")
    for name, expected in checksums.items():
        path = ROOT / name
        require(path.resolve().is_relative_to(ROOT) and path.is_file(), "Missing/unsafe shipped file: " + name)
        require(digest(path) == expected, "Shipped file changed: " + name)
    packaging = read_json(ROOT / "PACKAGING.json")
    for name, expected in packaging["preserved_files"].items():
        require(digest(CODE / name) == expected, "Original dataset bytes changed: " + name)
    dataset = CODE / "benchmark_output/basic_v34"
    preview = read_json(dataset / "preview.json")
    require(preview["manifest_sha256"] == digest(dataset / "manifest.json"), "Preview manifest hash differs")
    records = load_candidates(dataset)
    ids = [r["group_id"] for r in records]
    require(len(ids) == 152 and len(set(ids)) == len(ids), "Expected 152 distinct originals")
    originals = rows_by_id()
    scoring = [json.loads(s) for s in (dataset / "evaluation_sources.jsonl").read_text().splitlines()]
    require(len(originals) == 300, "Expected the complete 300-task original snapshot")
    require(len(scoring) == len(ids) and {s["instance_id"] for s in scoring} == set(ids), "Scoring IDs differ")
    for row in scoring:
        require(row == originals[row["instance_id"]], "Original scoring row differs from the source snapshot")
    for record in records:
        iid = record["group_id"]
        require(record["source"]["instance_id"] == iid == record["evaluation"]["original_instance_id"], "Task identity differs")
        require(hashlib.sha256(encoded(originals[iid])).hexdigest() == record["source"]["row_sha256"], "Original row hash differs")
        require(label_record(record) == record, "Category annotations disagree")
        final = record["stage_annotations"][-1]
        require(not final["unresolved"] and set(final["active_ids"]) == set(record["final_requirement_ids"]), "Final annotation set differs")
        for condition in ("wait", "full", "interrupt"):
            verify_delivery(record, condition)
    categories = dict(Counter(r["trajectory_type"] for r in records))
    lengths = dict(Counter(str(len(r["messages"])) for r in records))
    stats = read_json(dataset / "statistics.json")
    require(stats["selected"] == len(records) and stats["categories"] == categories
            and stats["message_counts"] == lengths, "Statistics disagree with the selected records")
    with tempfile.TemporaryDirectory(prefix="dialogue-scoring-check-") as tmp:
        folder = Path(tmp)
        predictions = folder / "predictions.jsonl"
        write_jsonl(predictions, [{"instance_id": iid, "model_name_or_path": "offline-check", "model_patch": ""} for iid in ids])
        job = prepare(dataset, predictions, "wait", folder / "job", python=sys.executable)
        require(len(job["tasks"]) == len(records), "Scoring preparation lost tasks")
        result = summarize(folder / "job")
        require(result["overall"]["status_counts"] == {"empty_patch": len(records)}, "Empty patches changed the denominator")
    runs = CODE / "source_runs"
    runs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="handoff-check-", dir=runs) as tmp:
        batch = run_batch(Path(tmp) / "batch", ["django__django-14017"],
                          target_total=4, max_new_calls=0, balance_categories=True,
                          construction_policy="strong_v1")
        require(batch["new_model_calls_attempted"] == 0, "Dry generation attempted a model call")
    print(json.dumps({"passed": True, "shipped_files_checked": len(checksums),
                      "original_snapshot_tasks": len(originals), "selected_conversations": len(records),
                      "message_counts": lengths, "categories": categories,
                      "scripted_delivery_conditions": ["wait", "full", "interrupt"],
                      "scoring_inputs_prepared": len(records), "model_calls": 0, "docker_runs": 0,
                      "scope": "Offline package and interface checks, not semantic certification or model evaluation"}, indent=2))


if __name__ == "__main__":
    main()
