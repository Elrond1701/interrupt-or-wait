"""Protect final-score denominator, original GT, and quality-hold identity."""

import hashlib
from pathlib import Path
import tempfile
import unittest

from benchmark_data import load_candidates, write_jsonl
from model_pilot import ROOT, encoded, read_json, save
from source_dataset import apply_quality_holds
import evaluate_benchmark as e


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.temp.name)
        self.dataset = ROOT / "benchmark_output/basic_v34"
        self.records = load_candidates(self.dataset)
        self.ids = [r["group_id"] for r in self.records[:2]]
        self.predictions = self.root / "input.jsonl"
        self.preds = [{"instance_id": i, "model_name_or_path": "unit/model", "model_patch": "diff fixture"} for i in self.ids]
        write_jsonl(self.predictions, self.preds)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self):
        return e.prepare(self.dataset, self.predictions, "wait", self.root / "job", self.ids)

    def report(self, job, iid, resolved=True, omit=False):
        row = next(r for r in e.jsonl(self.dataset / "evaluation_sources.jsonl") if r["instance_id"] == iid)
        tests = {}
        import json
        for k in ("FAIL_TO_PASS", "PASS_TO_PASS"):
            names = json.loads(row[k]) if isinstance(row[k], str) else row[k]
            tests[k] = {"success": names if resolved or k == "PASS_TO_PASS" else [],
                        "failure": names if not resolved and k == "FAIL_TO_PASS" else []}
        if omit:
            tests["FAIL_TO_PASS"]["success"] = []
        save(self.root / "job/logs/run_evaluation" / job["run_id"] / "unit__model" / iid / "report.json",
             {iid: {"resolved": resolved, "tests_status": tests}})

    def test_missing_duplicate_unknown_and_implicit_subset_rejected(self):
        for preds in (self.preds[:1], [self.preds[0], self.preds[0]],
                      [self.preds[0], {**self.preds[1], "instance_id": "other"}]):
            write_jsonl(self.predictions, preds)
            with self.assertRaisesRegex(ValueError, "exactly one"):
                self.prepare()
        write_jsonl(self.predictions, self.preds)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            e.prepare(self.dataset, self.predictions, "wait", self.root / "job")
        self.assertFalse((self.root / "job").exists())

    def test_empty_patch_is_failure_and_missing_report_keeps_denominator(self):
        self.preds[0]["model_patch"] = ""
        write_jsonl(self.predictions, self.preds)
        job = self.prepare()
        result = e.summarize(self.root / "job")
        self.assertEqual(result["overall"]["requested"], 2)
        self.assertEqual(result["overall"]["unscored"], 1)
        self.assertEqual(result["tasks"][0]["status"], "empty_patch")
        self.report(job, self.ids[1])
        result = e.summarize(self.root / "job")
        self.assertTrue(result["overall"]["complete"])
        self.assertEqual(result["overall"]["resolved_over_requested"], .5)
        self.assertEqual(sum(x["requested"] for x in result["by_category"].values()), 2)

    def test_original_failure_and_incomplete_report_are_distinct(self):
        job = self.prepare()
        self.report(job, self.ids[0], resolved=False)
        self.report(job, self.ids[1], omit=True)
        result = e.summarize(self.root / "job")
        self.assertEqual([r["status"] for r in result["tasks"]], ["test_failed", "incomplete_or_invalid_report"])
        self.assertEqual(result["overall"]["unscored"], 1)

    def test_prediction_tampering_cannot_reuse_a_job(self):
        self.prepare()
        write_jsonl(self.root / "job/predictions.jsonl", [])
        with self.assertRaisesRegex(ValueError, "input changed"):
            e.summarize(self.root / "job")

    def test_sources_are_exact_original_rows_and_command_uses_frozen_subset(self):
        job = self.prepare()
        expected = [r for r in e.jsonl(self.dataset / "evaluation_sources.jsonl") if r["instance_id"] in self.ids]
        self.assertEqual(e.jsonl(self.root / "job/evaluation_sources.jsonl"), expected)
        self.assertIn(str(self.root / "job/evaluation_sources.jsonl"), job["command"])
        self.assertEqual(job["scope"], "final_only")
        self.assertFalse((self.root / "job/execution.json").exists())

    def test_quality_hold_removes_only_bound_record_and_rejects_stale(self):
        record = self.records[0]
        hold = {"scenario_id": record["scenario_id"], "record_sha256": hashlib.sha256(encoded(record)).hexdigest(), "reason": "Known semantic defect"}
        path = self.root / "holds.json"
        save(path, {"holds": [hold]})
        kept, removed = apply_quality_holds(self.records, path)
        self.assertEqual(kept, self.records[1:])
        self.assertEqual(removed[0]["status"], "explicit_quality_hold")
        for bad in ({**hold, "record_sha256": "stale"}, {**hold, "scenario_id": "unknown"}):
            save(path, {"holds": [bad]})
            with self.assertRaisesRegex(ValueError, "Quality hold"):
                apply_quality_holds(self.records, path)


if __name__ == "__main__":
    unittest.main()
