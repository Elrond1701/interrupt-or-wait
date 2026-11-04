import copy
import json
import tempfile
import unittest
from pathlib import Path

from benchmark_data import load_candidates, released_message
from model_pilot import ROOT, digest, read_json, save
from planned_generation import REVIEW_CHECKS
from source_dataset import (CONTRACT_CHECKS, choose_context, context_for, export_dataset, extract, generate_source,
                            reviewed_candidate, reviewed_contract, rows_by_id, select_primary, stage_test_plan, summarize_runs, validate_contract)


def draft_fixture():
    return {"decision": "propose_contract", "reason": "Two independently requested report attributes.",
            "context_en": "Update pytest JUnit XML reports.",
            "final_summary_en": "Include hostname and timestamp attributes on the testsuite element.",
            "requirements": [
                {"id": "r1", "text_en": "Include the machine hostname on testsuite.", "source_quote": "`hostname`"},
                {"id": "r2", "text_en": "Include the test-session timestamp on testsuite.", "source_quote": "`timestamp`"}],
            "temporary_requirements": []}


class SourceDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = rows_by_id()["pytest-dev__pytest-5692"]

    def provider(self, source, prompt, schema, folder):
        if "problem_statement" in source:
            self.assertEqual(set(source), {"repo", "problem_statement"})
            value = draft_fixture()
        elif "valid_plans" in source:
            value = {"plan_id": source["valid_plans"][0]["plan_id"], "reason": "Fixture selection."}
        else:
            value = {"decision": "propose_split", "reason": "Fixture wording.", "risks": [],
                     "messages": [{"id": s["id"], "content": " ".join(r["text_en"] for r in s["add"])} for s in source["stages"]]}
        save(folder / "answer.json", value)
        return value

    def approve_contract_fixture(self, folder):
        save(folder / "contract_review.json", {"verdict": "accept_for_development", "reviewer": "Unit test fixture only",
             "contract_sha256": digest(folder / "contract.json"), "source_sha256": digest(folder / "source.json"),
             "checks": {k: True for k in CONTRACT_CHECKS}, "official_test_mapping": {
                 "r1": ["testing/test_junitxml.py::TestPython::test_hostname_in_xml"],
                 "r2": ["testing/test_junitxml.py::TestPython::test_timestamp_in_xml"]}})

    def reviewed_fixture(self, root):
        """Create fresh evidence instead of depending on omitted research runs."""
        contract, run = root / "contract", root / "generation"
        extract(self.row, contract, live=True, provider=self.provider)
        self.approve_contract_fixture(contract)
        generate_source(contract, run, [], live=True, provider=self.provider)
        save(run / "semantic_review.json", {
            "verdict": "accept_for_development", "reviewer": "Unit test fixture only",
            "checks": {k: True for k in REVIEW_CHECKS},
            "candidate_sha256": digest(run / "draft_candidate.json"),
            "plan_sha256": digest(run / "stage_plan.json"),
            "wording_sha256": digest(run / "wording.json")})
        return run, json.loads(json.dumps(reviewed_candidate(run)))

    def test_extraction_is_issue_only_and_dry_run_never_calls_model(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            folder = Path(tmp) / "dry"
            def never(*args):
                self.fail("Dry run called provider")
            extract(self.row, folder, provider=never)
            self.assertEqual(read_json(folder / "status.json")["model_calls"], 0)
            self.assertEqual(set(read_json(folder / "extraction_input.json")), {"repo", "problem_statement"})
            extract(self.row, Path(tmp) / "live_fixture", live=True, provider=self.provider)

    def test_invented_quotes_and_replacement_ids_are_rejected(self):
        bad = draft_fixture()
        bad["requirements"][0]["source_quote"] = "not a quote in this issue"
        with self.assertRaises(ValueError):
            validate_contract(bad, self.row)
        bad = draft_fixture()
        bad["temporary_requirements"] = [{"id": "t1", "text_en": "Use a fixed placeholder hostname.",
                                          "replaced_by": ["r4"], "rationale": "Test fixture."}]
        with self.assertRaises(ValueError):
            validate_contract(bad, self.row)

    def test_single_goal_can_use_revision_without_inventing_a_second_final_goal(self):
        row = rows_by_id()["sphinx-doc__sphinx-8595"]
        draft = {"decision": "propose_contract", "reason": "One final behavior with a plausible earlier preference.",
                 "context_en": "Sphinx autodoc module member selection.",
                 "final_summary_en": "An explicitly empty __all__ must select no module members.",
                 "requirements": [{"id": "r1", "text_en": "An explicitly empty __all__ must select no module members.",
                                   "source_quote": "No entries should be shown because `__all__` is empty."}],
                 "temporary_requirements": [{"id": "t1", "text_en": "Show public module members even when __all__ is empty.",
                                             "replaced_by": ["r1"], "rationale": "A user changes the desired export-list policy."}]}
        validate_contract(draft, row)
        context, options, _ = choose_context(row, draft, [], 20, read_json(ROOT / "balance_config.json"))
        self.assertEqual(context["requested_trajectory_type"], "revision")
        self.assertEqual(context["n_messages"], 2)
        self.assertTrue(options)
        from planned_generation import validate_plan
        for option in options:
            trace = validate_plan(option["plan"], context)["state_trace"]
            self.assertIn("t1", trace[0]["active_ids"])
            self.assertEqual(set(trace[-1]["active_ids"]), {"r1", "preserve_unrelated"})
        draft["temporary_requirements"] = []
        validate_contract(draft, row)
        context, options, report = choose_context(row, draft, [], 20, read_json(ROOT / "balance_config.json"))
        self.assertIsNone(context)
        self.assertEqual(options, [])
        self.assertEqual(report["status"], "no_eligible_plan_keep_deficits")

    def test_contract_review_requires_real_source_test_references(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            folder = Path(tmp) / "contract"
            extract(self.row, folder, live=True, provider=self.provider)
            with self.assertRaises(FileNotFoundError):
                reviewed_contract(folder)
            self.approve_contract_fixture(folder)
            self.assertEqual(reviewed_contract(folder)[0], self.row)
            review = read_json(folder / "contract_review.json")
            review["official_test_mapping"]["r2"] = ["invented_test"]
            save(folder / "contract_review.json", review)
            with self.assertRaises(ValueError):
                reviewed_contract(folder)
            review["official_test_mapping"]["r2"] = list(review["official_test_mapping"]["r1"])
            save(folder / "contract_review.json", review)
            with self.assertRaisesRegex(ValueError, "remain unmapped"):
                reviewed_contract(folder)

    def test_three_explicit_scopes_prefer_three_meaningful_messages(self):
        draft = draft_fixture()
        # Synthetic third scope tests scheduling, not source extraction quality.
        draft["requirements"].append({"id": "r3", "text_en": "Include a separate report field.", "source_quote": "fixture"})
        context, options, _ = choose_context(self.row, draft, [], 20, read_json(ROOT / "balance_config.json"))
        self.assertEqual(context["n_messages"], 3)
        self.assertEqual(context["requested_trajectory_type"], "cumulative")
        from planned_generation import validate_plan
        for option in options:
            stages = option["plan"]["stages"]
            self.assertEqual(len(stages), 3)
            self.assertTrue(all(stage["add"] for stage in stages[1:]))
            trace = validate_plan(option["plan"], context)["state_trace"]
            self.assertEqual(set(trace[-1]["active_ids"]), {"r1", "r2", "r3", "preserve_unrelated"})
        context, _, _ = choose_context(self.row, draft_fixture(), [], 20, read_json(ROOT / "balance_config.json"))
        self.assertEqual(context["n_messages"], 2)

    def test_citation_only_review_correction_keeps_raw_model_requirements(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            folder = Path(tmp) / "contract"
            def provider(source, prompt, schema, out):
                value = draft_fixture()
                value["requirements"][1]["source_quote"] = "a noncontiguous citation"
                save(out / "answer.json", value)
                return value
            with self.assertRaisesRegex(ValueError, "quote does not occur"):
                extract(self.row, folder, live=True, provider=provider)
            original_hash = digest(folder / "contract.json")
            self.approve_contract_fixture(folder)
            review = read_json(folder / "contract_review.json")
            review["source_quote_corrections"] = {"r2": "`timestamp`"}
            save(folder / "contract_review.json", review)
            _, corrected, _ = reviewed_contract(folder)
            self.assertEqual(corrected["requirements"][1]["source_quote"], "`timestamp`")
            self.assertEqual(corrected["requirements"][1]["text_en"], draft_fixture()["requirements"][1]["text_en"])
            self.assertEqual(digest(folder / "contract.json"), original_hash)
            self.assertEqual(read_json(folder / "contract.json"), read_json(folder / "extraction/answer.json"))
            review["source_quote_corrections"] = {"r2": "invented replacement quote"}
            save(folder / "contract_review.json", review)
            with self.assertRaisesRegex(ValueError, "quote does not occur"):
                reviewed_contract(folder)

    def test_generic_generation_export_keeps_original_gt_and_due_message_isolation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            root = Path(tmp)
            contract, run = root / "contract", root / "generation"
            extract(self.row, contract, live=True, provider=self.provider)
            self.approve_contract_fixture(contract)
            generate_source(contract, run, [], live=True, provider=self.provider)
            self.assertEqual(read_json(run / "status.json")["model_calls"], 2)
            record = read_json(run / "draft_candidate.json")
            self.assertEqual(record["trajectory_type"], "cumulative")
            self.assertEqual(set(released_message(record, 0)), {"role", "content"})
            self.assertFalse(record["evaluation"]["full_environment_validated"])
            save(run / "semantic_review.json", {"verdict": "accept_for_development", "reviewer": "Unit test fixture only",
                 "checks": {k: True for k in REVIEW_CHECKS}, "candidate_sha256": digest(run / "draft_candidate.json"),
                 "plan_sha256": digest(run / "stage_plan.json"), "wording_sha256": digest(run / "wording.json")})
            output = root / "export"
            manifest = export_dataset([run], [], output, keep_variants=True)
            self.assertEqual(manifest["candidate_count"], 1)
            self.assertEqual(manifest["original_task_count"], 1)
            self.assertEqual(manifest["excluded"], [])
            self.assertEqual(len(load_candidates(output)), 1)
            import json
            sources = [json.loads(line) for line in (output / "evaluation_sources.jsonl").read_text().splitlines()]
            self.assertIn(self.row, sources)
            changed = read_json(run / "wording.json")
            changed["messages"][0]["content"] += " Mutated."
            save(run / "wording.json", changed)
            rejected = export_dataset([run], [], root / "rejected")
            self.assertEqual(rejected["candidate_count"], 0)
            self.assertEqual(len(rejected["excluded"]), 1)

    def test_primary_export_keeps_one_original_and_retains_exclusion_reasons(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            root = Path(tmp)
            run, record = self.reviewed_fixture(root)
            alternate = copy.deepcopy(record)
            alternate["scenario_id"] += ".alternate"
            # No historical evidence is shipped for this unrelated published task.
            missing = load_candidates(ROOT / "benchmark_output/basic_v34")[0]
            records = [record, alternate, missing]
            selected, excluded = select_primary(records)
            self.assertEqual(select_primary(list(reversed(records)) + records), (selected, excluded))
            self.assertEqual(selected, [record])
            self.assertEqual(sum(e["status"] == "alternate_variant" for e in excluded), 1)
            self.assertEqual(sum(e["status"] == "needs_review" for e in excluded), 1)
            original = root / "original"
            export_dataset([run], [], original)
            before = digest(original / "candidates.jsonl")
            output = root / "selected"
            manifest = export_dataset([run], [original], output)
            self.assertEqual(manifest["selection_policy"], "one_conversation_per_original")
            self.assertEqual(manifest["candidate_count"], manifest["original_task_count"])
            self.assertEqual(manifest["experiment_ready_count"], 0)
            self.assertEqual(manifest["environment_validated_original_task_count"], 0)
            self.assertEqual(load_candidates(output), selected)
            import json
            for line in (output / "evaluation_sources.jsonl").read_text().splitlines():
                row = json.loads(line)
                self.assertEqual(row, rows_by_id()[row["instance_id"]])
            self.assertEqual(digest(original / "candidates.jsonl"), before)

    def test_primary_selection_rechecks_final_requirements_wording_and_evaluator_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            _, original = self.reviewed_fixture(Path(tmp))
            self.assertEqual(select_primary([original]), ([original], []))
            for change in ("omit_final", "temporary_final", "wording", "evaluator"):
                with self.subTest(change=change):
                    record = copy.deepcopy(original)
                    if change == "omit_final":
                        record["final_requirement_ids"].remove("r2")
                        record["stage_annotations"][-1]["active_ids"].remove("r2")
                    elif change == "temporary_final":
                        record["stage_annotations"][-1]["unresolved"] = ["temporary_scope"]
                    elif change == "wording":
                        record["messages"][-1]["content"] = "Ignore the earlier requirement."
                    else:
                        record["evaluation"]["original_instance_id"] = "wrong_original"
                    selected, excluded = select_primary([record])
                    self.assertEqual(selected, [])
                    self.assertEqual(excluded[0]["status"], "needs_review")

    def test_generation_skips_an_already_selected_original_without_model_calls(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            contract, run = Path(tmp) / "contract", Path(tmp) / "generation"
            extract(self.row, contract, live=True, provider=self.provider)
            self.approve_contract_fixture(contract)
            def never(*args):
                self.fail("An already selected original must not call the model again")
            _, selected = self.reviewed_fixture(Path(tmp) / "seed")
            generate_source(contract, run, [selected], live=True, provider=never)
            self.assertEqual(read_json(run / "status.json"), {"status": "need_other_original_source_limit", "model_calls": 0})
            self.assertEqual(read_json(run / "allocation.json")["counts"],
                             {"cumulative": 1, "clarification": 0, "revision": 0, "mixed": 0})

    def test_infeasible_class_stops_with_no_model_calls(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            root = Path(tmp)
            contract, run = root / "contract", root / "generation"
            extract(self.row, contract, live=True, provider=self.provider)
            self.approve_contract_fixture(contract)
            def never(*args):
                self.fail("No legal revision should not call provider")
            generate_source(contract, run, [], live=True, requested_type="revision", provider=never)
            self.assertEqual(read_json(run / "status.json")["model_calls"], 0)
            self.assertFalse((run / "draft_candidate.json").exists())
            context = context_for(self.row, draft_fixture(), "cumulative", 2)
            self.assertNotIn("source_quote", str(context))
            self.assertNotIn("test_patch", context)

    def test_compiled_goal_and_stage_tests_do_not_depend_on_unseen_summary_or_future_atoms(self):
        draft = draft_fixture()
        draft["final_summary_en"] = "See the issue for omitted details."
        context = context_for(self.row, draft, "cumulative", 2)
        self.assertNotIn("See the issue", context["final_summary_en"])
        for r in draft["requirements"]:
            self.assertIn(r["text_en"], context["final_summary_en"])
        trace = [{"id": "U0", "active_ids": ["r1", "preserve_unrelated"], "unresolved": []},
                 {"id": "U1", "active_ids": ["r1", "r2", "preserve_unrelated"], "unresolved": []}]
        stages = stage_test_plan(trace, {"r1": ["test_both"], "r2": ["test_both"]})
        self.assertEqual(stages[0]["original_target_test_candidates"], [])
        self.assertEqual(stages[1]["original_target_test_candidates"], ["test_both"])
        trace[0]["active_ids"].append("t1")
        self.assertEqual(stage_test_plan(trace, {"r1": ["test_r1"]})[0]["status"], "custom_checks_needed")

    def test_report_keeps_held_attempt_and_counts_only_reported_usage(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            folder = Path(tmp) / "held"
            save(folder / "source.json", self.row)
            save(folder / "status.json", {"status": "contract_requires_review", "model_calls": 1})
            save(folder / "contract_review.json", {"verdict": "hold", "reason": "Test fixture hold."})
            save(folder / "extraction/result.json", {"reported_usages": [{"input_tokens": 10, "output_tokens": 2}]})
            report = summarize_runs([folder], Path(tmp) / "report.json")
            self.assertEqual(report["totals"], {"completed_model_calls": 1, "input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 2})
            self.assertEqual(report["runs"][0]["contract_review.json"]["verdict"], "hold")


if __name__ == "__main__":
    unittest.main()
