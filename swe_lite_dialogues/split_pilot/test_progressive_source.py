import copy
import tempfile
import unittest
from pathlib import Path

from benchmark_data import load_candidates, released_message
from model_pilot import ROOT, digest, read_json, save
from planned_generation import REVIEW_CHECKS, validate_plan, wording_context
from source_dataset import (CONTRACT_CHECKS, PROGRESSIVE_CHECKS, choose_context,
                            context_for, export_dataset, extract, generate_source,
                            reviewed_candidate, reviewed_contract, validate_contract)
import test_source_dataset as fixtures


def progressive_fixture():
    draft = fixtures.draft_fixture()
    draft.update(schema_version="2", context_en="Adjust pytest JUnit XML reporting.",
                 dialogue_assessment={"three_messages": "natural", "reason": "Two separate report decisions can be clarified."},
                 clarifications=[
                     {"id": "c1", "question_en": "What host metadata should the report include?", "resolves_to": ["r1"]},
                     {"id": "c2", "question_en": "What timing metadata should the report include?", "resolves_to": ["r2"]}])
    return draft


class ProgressiveSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SourceDatasetTests.setUpClass()
        cls.row = fixtures.SourceDatasetTests.row

    def choose(self, draft):
        return choose_context(self.row, draft, [], 20, read_json(ROOT / "balance_config.json"))

    def test_two_open_decisions_support_three_clarifications_without_temporary_goal(self):
        draft = progressive_fixture()
        validate_contract(draft, self.row)
        context, menu, report = self.choose(draft)
        self.assertEqual((context["requested_trajectory_type"], context["n_messages"]), ("clarification", 3))
        self.assertEqual(context["temporary_requirements"], [])
        self.assertEqual({o["n_messages"] for o in menu}, {2, 3})
        result = validate_plan(menu[0]["plan"], context)
        self.assertEqual(result["update_types"], ["clarification", "clarification"])
        self.assertEqual(result["state_trace"][0]["active_ids"], ["preserve_unrelated"])
        self.assertEqual([len(s["unresolved"]) for s in result["state_trace"]], [2, 1, 0])
        public_questions = wording_context(context, result)["stages"][0]["uncertainties"]
        self.assertTrue(all(set(q) == {"id", "question_en"} for q in public_questions))
        self.assertTrue(any(r["n_messages"] == 3 and r["legal_plan_count"] for r in report["feasibility"]))
        legacy = copy.deepcopy(context)
        legacy.pop("planning_version")
        with self.assertRaises(ValueError):
            validate_plan(menu[0]["plan"], legacy)

    def test_one_final_goal_can_clarify_then_revise_and_prefers_that_over_two(self):
        draft = progressive_fixture()
        draft["requirements"] = draft["requirements"][:1]
        draft["clarifications"] = draft["clarifications"][:1]
        draft["temporary_requirements"] = [{"id": "t1", "text_en": "Use an anonymous placeholder hostname.",
                                            "replaced_by": ["r1"], "rationale": "Synthetic privacy-policy fixture."}]
        context, menu, _ = self.choose(draft)
        self.assertEqual((context["requested_trajectory_type"], context["n_messages"]), ("mixed", 3))
        result = validate_plan(menu[0]["plan"], context)
        self.assertEqual(result["update_types"], ["clarification", "revision"])
        self.assertEqual(set(result["state_trace"][-1]["active_ids"]), {"r1", "preserve_unrelated"})
        self.assertTrue(any(o["n_messages"] == 2 for o in menu))

    def test_missing_or_overlapping_decisions_and_premature_answers_are_rejected(self):
        for targets in (["r3"], ["r1"], ["r2", "r2"]):
            draft = progressive_fixture()
            draft["clarifications"][1]["resolves_to"] = targets
            with self.assertRaises(ValueError):
                validate_contract(draft, self.row)
        context, menu, _ = self.choose(progressive_fixture())
        plan = copy.deepcopy(menu[0]["plan"])
        plan["stages"][0]["add"].append("r1")
        with self.assertRaises(ValueError):
            validate_plan(plan, context)
        plan = copy.deepcopy(menu[0]["plan"])
        plan["stages"][2] = copy.deepcopy(plan["stages"][1])
        plan["stages"][2]["id"] = "U2"
        with self.assertRaises(ValueError):
            validate_plan(plan, context)

    def test_upfront_assessment_is_advisory_and_no_update_does_not_force_u2(self):
        draft = progressive_fixture()
        draft["dialogue_assessment"]["three_messages"] = "not_natural"
        _, menu, report = self.choose(draft)
        self.assertEqual({o["n_messages"] for o in menu}, {2, 3})
        self.assertEqual(report["upfront_assessment"]["three_messages"], "not_natural")
        draft["requirements"] = draft["requirements"][:1]
        draft["clarifications"] = []
        context, menu, report = self.choose(draft)
        self.assertIsNone(context)
        self.assertEqual(menu, [])
        self.assertEqual(report["status"], "no_eligible_plan_keep_deficits")

    def test_initial_invariant_rendering_keeps_future_answers_private_and_legacy_stable(self):
        draft = progressive_fixture()
        legacy = context_for(self.row, draft, "clarification", 3)
        current = context_for(self.row, draft, "clarification", 3, "2")
        invariant = "Preserve existing behavior outside the changes currently requested."
        self.assertNotIn("rendering_version", legacy)
        self.assertEqual(current["context_en"], legacy["context_en"] + "\n" + invariant)
        self.assertEqual(current["final_requirements"], legacy["final_requirements"])
        for requirement in draft["requirements"]:
            self.assertNotIn(requirement["text_en"], current["context_en"])
        with self.assertRaisesRegex(ValueError, "rendering version"):
            context_for(self.row, draft, "clarification", 3, "unexpected")

    def test_three_first_design_requires_two_distinct_supported_updates(self):
        draft = progressive_fixture()
        draft["length_design"] = dict(route="separate_scopes", u1_adds=["r1"], u2_adds=["r2"],
                                      scope_route_reason="Host and timing metadata are distinct fields.",
                                      revision_route_reason="Separate original scopes suffice; no reversal needed.")
        validate_contract(draft, self.row)
        _, menu, report = self.choose(draft)
        self.assertEqual({o["n_messages"] for o in menu}, {3})
        self.assertEqual(report["length_policy"], "upfront_three_first_v1")
        _, short_menu, _ = choose_context(self.row, draft, [], 20, read_json(ROOT / "balance_config.json"), requested_length=2)
        self.assertEqual({o["n_messages"] for o in short_menu}, {2})
        for field, value in (("u2_adds", ["r1"]), ("u2_adds", ["r3"]), ("u2_adds", [])):
            broken = copy.deepcopy(draft)
            broken["length_design"][field] = value
            with self.assertRaisesRegex(ValueError, "Length design"):
                validate_contract(broken, self.row)
        draft["requirements"] = draft["requirements"][:1]
        draft["clarifications"] = draft["clarifications"][:1]
        draft["temporary_requirements"] = [dict(id="t1", text_en="Use a placeholder hostname.",
                                                  replaced_by=["r1"], rationale="Synthetic privacy preference.")]
        draft["length_design"].update(route="clarify_then_revise", u1_adds=["t1"], u2_adds=["r1"])
        validate_contract(draft, self.row)
        draft["temporary_requirements"] = []
        with self.assertRaisesRegex(ValueError, "Length design"):
            validate_contract(draft, self.row)
        draft["length_design"].update(route="two_message_fallback", u1_adds=["r1"], u2_adds=[])
        with self.assertRaisesRegex(ValueError, "Length design"):
            validate_contract(draft, self.row)
        draft["dialogue_assessment"]["three_messages"] = "not_natural"
        validate_contract(draft, self.row)
        _, menu, _ = self.choose(draft)
        self.assertEqual({o["n_messages"] for o in menu}, {2})

    def test_new_extraction_requests_upfront_design_without_author_test_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            def provider(source, prompt, schema, folder):
                self.assertEqual(set(source), {"repo", "problem_statement"})
                self.assertTrue(prompt.startswith("THREE-FIRST DESIGN POLICY"))
                fields = list(schema["properties"])
                self.assertEqual(fields[-1], "length_design")
                self.assertLess(fields.index("requirements"), fields.index("dialogue_assessment"))
                self.assertLess(fields.index("clarifications"), fields.index("dialogue_assessment"))
                self.assertIn("length_design", schema["required"])
                value = progressive_fixture()
                value["length_design"] = dict(route="separate_scopes", u1_adds=["r1"], u2_adds=["r2"],
                                              scope_route_reason="Distinct metadata fields.", revision_route_reason="No reversal needed.")
                save(folder / "answer.json", value)
                return value
            extract(self.row, Path(tmp) / "contract", live=True, provider=provider)

    def test_model_can_choose_short_fallback_in_same_call_and_replay_preserves_evaluator(self):
        for preferred_length in (3, 2):
            with self.subTest(length=preferred_length), tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
                calls = []
                def provider(source, prompt, schema, folder):
                    calls.append(source)
                    if "problem_statement" in source:
                        self.assertEqual(set(source), {"repo", "problem_statement"})
                        value = progressive_fixture()
                    elif "valid_plans" in source:
                        option = next(o for o in source["valid_plans"] if o["n_messages"] == preferred_length)
                        value = {"plan_id": option["plan_id"], "reason": "Synthetic fixture selection including short fallback."}
                    else:
                        value = {"decision": "propose_split", "reason": "Unit-test wording only.", "risks": [],
                                 "messages": [{"id": s["id"], "content": " ".join(
                                     [r["text_en"] for r in s["add"] if r["id"] != "preserve_unrelated"] + [u.get("question_en", "Undecided.") for u in s["uncertainties"]])}
                                              for s in source["stages"]]}
                    save(folder / "answer.json", value)
                    return value
                root = Path(tmp)
                contract, run = root / "contract", root / "generation"
                extract(self.row, contract, live=True, provider=provider)
                fixtures.SourceDatasetTests().approve_contract_fixture(contract)
                with self.assertRaisesRegex(ValueError, "incomplete checks"):
                    reviewed_contract(contract)
                review = read_json(contract / "contract_review.json")
                review["checks"].update({k: True for k in PROGRESSIVE_CHECKS})
                save(contract / "contract_review.json", review)
                generate_source(contract, run, [], live=True, provider=provider)
                self.assertEqual(len(calls), 3)
                save(run / "semantic_review.json", {"verdict": "accept_for_development", "reviewer": "Unit test fixture only",
                     "candidate_sha256": digest(run / "draft_candidate.json"), "plan_sha256": digest(run / "stage_plan.json"),
                     "wording_sha256": digest(run / "wording.json"), "checks": {k: True for k in REVIEW_CHECKS}})
                record = reviewed_candidate(run)
                self.assertEqual(record["n_messages"], preferred_length)
                invariant = "Preserve existing behavior outside the changes currently requested."
                self.assertNotIn(invariant, read_json(run / "wording.json")["messages"][0]["content"])
                self.assertIn(invariant, released_message(record, 0)["content"])
                self.assertEqual(record["provenance"]["rendering_version"], "2")
                self.assertTrue(released_message(record, 0)["content"].startswith(read_json(run / "context.json")["context_en"]))
                original_context = read_json(run / "context.json")
                changed = dict(original_context)
                changed.pop("rendering_version")
                save(run / "context.json", changed)
                with self.assertRaisesRegex(ValueError, "context changed"):
                    reviewed_candidate(run)
                save(run / "context.json", original_context)
                if preferred_length == 3:
                    self.assertNotIn("Include the machine hostname", released_message(record, 0)["content"])
                    self.assertEqual(record["evaluation"]["stage_test_plan"][0]["status"], "intent_only_no_behavioral_gt")
                export_dataset([run], [], root / "export")
                self.assertEqual(load_candidates(root / "export"), [record])
                import json
                self.assertEqual(json.loads((root / "export/evaluation_sources.jsonl").read_text()), self.row)


if __name__ == "__main__":
    unittest.main()
