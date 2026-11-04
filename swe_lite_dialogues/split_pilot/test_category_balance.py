"""Early class preferences must not relabel outputs or change old records."""

import copy
import tempfile
import unittest
from pathlib import Path

from balanced_generation import category_schedule
from model_pilot import ROOT, digest, read_json, save
from source_batch import category_preference, run_batch
from source_dataset import (PROGRESSIVE_CHECKS, choose_context, extract,
                            reviewed_contract, validate_contract, generate_source, export_dataset)
from planned_generation import validate_plan, REVIEW_CHECKS
from test_progressive_source import progressive_fixture
import test_source_dataset as fixtures


def cumulative_fixture():
    draft = progressive_fixture()
    draft.update(clarifications=[], dialogue_assessment={"three_messages": "not_natural", "reason": "Two real scopes."},
                 length_design=dict(route="two_message_fallback", u1_adds=["r2"], u2_adds=[],
                                    scope_route_reason="Two report fields.", revision_route_reason="No change of policy."))
    return draft


class CategoryBalanceTests(unittest.TestCase):
    def setUp(self):
        fixtures.SourceDatasetTests.setUpClass()
        self.row = fixtures.SourceDatasetTests.row
        self.config = read_json(ROOT / "balance_config.json")

    def test_opt_in_three_first_prompt_is_bound_without_relabeling(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            f = Path(tmp) / "contract"
            def provider(source, prompt, schema, folder):
                self.assertIn("COMPARE DELIVERY ROUTES", prompt)
                value = cumulative_fixture()
                save(folder / "request.json", {"input": source, "developer_instructions": prompt})
                save(folder / "answer.json", value)
                return value
            extract(self.row, f, live=True, preferred_type="revision", category_prompt_version="2", provider=provider)
            fixtures.SourceDatasetTests().approve_contract_fixture(f)
            review = read_json(f / "contract_review.json")
            review["checks"].update({k: True for k in PROGRESSIVE_CHECKS})
            review["category_policy_sha256"] = digest(f / "category_policy.json")
            save(f / "contract_review.json", review)
            _, draft, _ = reviewed_contract(f)
            _, menu, _ = choose_context(self.row, draft, [], 20, self.config, rendering_version="3")
            self.assertEqual({o["trajectory_type"] for o in menu}, {"cumulative"})
            self.assertEqual({o["n_messages"] for o in menu}, {2})
            self.assertEqual(read_json(f / "category_policy.json")["version"], "category_v2")
            request = read_json(f / "extraction/request.json")
            request["developer_instructions"] = "different prompt"
            save(f / "extraction/request.json", request)
            with self.assertRaisesRegex(ValueError, "Category policy differs"):
                reviewed_contract(f)
            with self.assertRaisesRegex(ValueError, "Category prompt version"):
                extract(self.row, Path(tmp) / "bad", category_prompt_version="2")

    def test_single_atom_routing_keeps_old_batches_and_other_preferences(self):
        draft = cumulative_fixture()
        plan = {"category_strategy": "locked_endpoint_v2", "category_preferences": {"x": "cumulative"}}
        self.assertEqual(category_preference(plan, "x", draft), "cumulative")
        draft["requirements"] = draft["requirements"][:1]
        self.assertEqual(category_preference(plan, "x", draft), "clarification")
        plan["category_strategy"] = "locked_endpoint_v1"
        self.assertEqual(category_preference(plan, "x", draft), "cumulative")
        plan["category_strategy"] = "locked_endpoint_v2"
        for kind in ("clarification", "revision", "mixed"):
            plan["category_preferences"]["x"] = kind
            self.assertEqual(category_preference(plan, "x", draft), kind)

    def test_single_atom_batch_routes_after_review_without_an_extra_call(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            b = Path(tmp) / "batch"
            calls = []
            def provider(source, prompt, schema, folder):
                calls.append(prompt)
                draft = cumulative_fixture()
                draft["requirements"] = draft["requirements"][:1]
                draft["requirements"][0]["text_en"] = "Include hostname and timestamp in the testsuite XML."
                draft["length_design"]["u1_adds"] = ["r1"]
                save(folder / "request.json", {"input": source, "developer_instructions": prompt})
                save(folder / "answer.json", draft)
                return draft
            run_batch(b, [self.row["instance_id"]], balance_categories=True, construction_policy="legacy", live=True, provider=provider)
            contract = b / self.row["instance_id"] / "contract"
            fixtures.SourceDatasetTests().approve_contract_fixture(contract)
            review = read_json(contract / "contract_review.json")
            review["checks"].update({k: True for k in PROGRESSIVE_CHECKS})
            review["official_test_mapping"] = {"r1": sum(review["official_test_mapping"].values(), [])}
            review["endpoint_only_sha256"] = digest(contract / "endpoint_only.json")
            save(contract / "contract_review.json", review)
            result = run_batch(b, live=True, provider=provider)
            self.assertEqual(result["status_counts"], {"category_contract_review_pending": 1})
            self.assertEqual(result["total_model_calls_attempted"], 2)
            self.assertTrue(calls[-1].startswith("Preferred trajectory type for this attempt: clarification."))
            self.assertTrue(result["items"][0]["category_preference"]["single_requirement_fallback"])
            self.assertEqual(run_batch(b, live=True, provider=provider)["new_model_calls_attempted"], 0)
            policy = b / self.row["instance_id"] / "category_contract/category_policy.json"
            value = read_json(policy)
            value["preferred_type"] = "cumulative"
            save(policy, value)
            result = run_batch(b, live=True, provider=provider)
            self.assertEqual(result["new_model_calls_attempted"], 0)
            self.assertIn("endpoint routing", result["items"][0]["reason"])

    def test_scarce_class_preferences_rotate_without_counting_attempts_as_success(self):
        records = []
        for kind, count in {"cumulative": 1, "clarification": 37, "mixed": 4}.items():
            for i in range(count):
                uid = kind + str(i)
                updates = ["addition", "revision"] if kind == "mixed" else ["addition" if kind == "cumulative" else "clarification"]
                records.append(dict(scenario_id=uid, group_id=uid, source={"instance_id": uid},
                                    messages=[{"id": "U" + str(j)} for j in range(len(updates) + 1)],
                                    update_types=updates, validation={"status": "semantic_reviewed_pending_new_stage_validation"}))
        before = copy.deepcopy(records)
        schedule = category_schedule([str(i) for i in range(6)], records, self.config)
        self.assertEqual(list(schedule.values()), ["revision", "cumulative", "revision", "cumulative", "revision", "cumulative"])
        self.assertEqual(records, before)
        self.assertEqual(category_schedule([str(i) for i in range(6)], records, self.config), schedule)
        with self.assertRaises(ValueError):
            category_schedule(["x", "x"], records, self.config)

    def test_definite_initial_requirements_allow_cumulative_and_pure_revision(self):
        draft = cumulative_fixture()
        validate_contract(draft, self.row)
        ctx, options, _ = choose_context(self.row, draft, [], 20, self.config, rendering_version="3")
        self.assertEqual({o["trajectory_type"] for o in options}, {"cumulative"})
        for option in options:
            state = validate_plan(option["plan"], ctx)
            self.assertEqual(state["update_types"], ["addition"])
            self.assertEqual(state["state_trace"][-1]["active_ids"], ["preserve_unrelated", "r1", "r2"])
        draft["requirements"] = draft["requirements"][:1]
        draft["temporary_requirements"] = [dict(id="t1", text_en="Use an anonymous placeholder hostname.",
                                                   replaced_by=["r1"], rationale="Privacy preference fixture.")]
        draft["length_design"]["u1_adds"] = ["r1"]
        validate_contract(draft, self.row)
        ctx, options, _ = choose_context(self.row, draft, [], 20, self.config, rendering_version="3")
        self.assertEqual({o["trajectory_type"] for o in options}, {"revision"})
        state = validate_plan(options[0]["plan"], ctx)
        self.assertIn("t1", state["state_trace"][0]["active_ids"])
        self.assertEqual(state["update_types"], ["revision"])
        self.assertEqual(state["state_trace"][-1]["active_ids"], ["preserve_unrelated", "r1"])

    def test_extraction_preference_is_bound_but_natural_fallback_is_allowed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            f = Path(tmp) / "contract"
            def provider(source, prompt, schema, folder):
                self.assertEqual(set(source), {"repo", "problem_statement"})
                self.assertTrue(prompt.startswith("Preferred trajectory type for this attempt: revision."))
                value = cumulative_fixture()  # A fallback is not relabeled revision.
                save(folder / "request.json", {"input": source, "developer_instructions": prompt})
                save(folder / "answer.json", value)
                return value
            extract(self.row, f, live=True, preferred_type="revision", provider=provider)
            fixtures.SourceDatasetTests().approve_contract_fixture(f)
            review = read_json(f / "contract_review.json")
            review["checks"].update({k: True for k in PROGRESSIVE_CHECKS})
            review["category_policy_sha256"] = digest(f / "category_policy.json")
            save(f / "contract_review.json", review)
            _, draft, _ = reviewed_contract(f)
            _, menu, _ = choose_context(self.row, draft, [], 20, self.config)
            self.assertEqual({o["trajectory_type"] for o in menu}, {"cumulative"})
            (f / "category_policy.json").unlink()
            with self.assertRaisesRegex(ValueError, "Category policy"):
                reviewed_contract(f)
            save(f / "category_policy.json", {"version": "category_v1", "preferred_type": "clarification"})
            with self.assertRaisesRegex(ValueError, "Category policy"):
                reviewed_contract(f)

    def test_batch_schedule_is_saved_on_preview_and_cannot_change_on_resume(self):
        ids = ["pytest-dev__pytest-5692", "scikit-learn__scikit-learn-14983"]
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            f = Path(tmp) / "batch"
            run_batch(f, ids, balance_categories=True, construction_policy="legacy")
            plan = read_json(f / "batch_plan.json")
            self.assertEqual(set(plan["category_preferences"]), set(ids))
            self.assertFalse((f / ids[0]).exists())
            self.assertEqual(run_batch(f)["new_model_calls_attempted"], 0)
            with self.assertRaisesRegex(ValueError, "category balancing mode"):
                run_batch(f, balance_categories=False)
            plan["category_preferences"][ids[0]] = "mixed"
            save(f / "batch_plan.json", plan)
            with self.assertRaisesRegex(ValueError, "category preferences"):
                run_batch(f)

    def test_explicit_replacement_preserves_sources_and_never_drops_old_on_bad_review(self):
        fixture = fixtures.SourceDatasetTests()
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            base = Path(tmp)
            contract = base / "contract"
            extract(self.row, contract, live=True, provider=fixture.provider)
            fixture.approve_contract_fixture(contract)
            for index in (0, 1):
                run = base / ("run" + str(index))
                def provider(source, prompt, schema, folder):
                    value = fixture.provider(source, prompt, schema, folder)
                    if "messages" in value:
                        value["messages"][0]["content"] += " " * index
                        save(folder / "answer.json", value)
                    return value
                generate_source(contract, run, [], live=True, provider=provider)
                save(run / "semantic_review.json", dict(verdict="accept_for_development", reviewer="Unit test fixture only",
                     checks={k: True for k in REVIEW_CHECKS}, candidate_sha256=digest(run / "draft_candidate.json"),
                     plan_sha256=digest(run / "stage_plan.json"), wording_sha256=digest(run / "wording.json")))
            export_dataset([base / "run0"], [], base / "old")
            old_bytes = (base / "old/candidates.jsonl").read_bytes()
            report = export_dataset([base / "run1"], [base / "old"], base / "new", replace_existing=True)
            self.assertEqual(report["original_task_count"], 1)
            self.assertEqual(report["excluded"][0]["status"], "explicitly_replaced")
            self.assertEqual((base / "old/evaluation_sources.jsonl").read_bytes(), (base / "new/evaluation_sources.jsonl").read_bytes())
            self.assertEqual((base / "old/candidates.jsonl").read_bytes(), old_bytes)
            save(base / "run1/semantic_review.json", {"verdict": "hold", "reason": "Bad fixture."})
            with self.assertRaisesRegex(ValueError, "Replacement requires"):
                export_dataset([base / "run1"], [base / "old"], base / "bad", replace_existing=True)
            self.assertFalse((base / "bad").exists())

    def test_balanced_batch_locks_endpoint_before_category_adaptation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            b = Path(tmp) / "batch"
            calls = []
            def provider(source, prompt, schema, folder):
                calls.append(source)
                value = cumulative_fixture()
                if "reviewed_final_requirements" in source:
                    self.assertTrue(prompt.startswith("Preferred trajectory type"))
                    value["requirements"] = copy.deepcopy(source["reviewed_final_requirements"])
                else:
                    self.assertFalse(prompt.startswith("Preferred trajectory type"))
                    self.assertEqual(set(source), {"repo", "problem_statement"})
                save(folder / "request.json", {"input": source, "developer_instructions": prompt})
                save(folder / "answer.json", value)
                return value
            result = run_batch(b, [self.row["instance_id"]], balance_categories=True, construction_policy="legacy", live=True, provider=provider)
            self.assertEqual(result["status_counts"], {"contract_review_pending": 1})
            self.assertEqual(run_batch(b, live=True, provider=provider)["new_model_calls_attempted"], 0)
            contract = b / self.row["instance_id"] / "contract"
            with self.assertRaisesRegex(ValueError, "Endpoint-only"):
                generate_source(contract, b / "invalid_generation", [], live=True, provider=provider)
            fixtures.SourceDatasetTests().approve_contract_fixture(contract)
            review = read_json(contract / "contract_review.json")
            review["checks"].update({k: True for k in PROGRESSIVE_CHECKS})
            review["endpoint_only_sha256"] = digest(contract / "endpoint_only.json")
            save(contract / "contract_review.json", review)
            result = run_batch(b, live=True, max_new_calls=1, provider=provider)
            self.assertEqual(result["status_counts"], {"category_contract_review_pending": 1})
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[1]["reviewed_final_requirements"], read_json(contract / "contract.json")["requirements"])
            self.assertEqual(run_batch(b, live=True, provider=provider)["new_model_calls_attempted"], 0)


if __name__ == "__main__":
    unittest.main()
