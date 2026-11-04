import copy
import tempfile
import unittest
from pathlib import Path

from balanced_generation import endpoint_route
from model_pilot import ROOT, read_json, save, digest
from planned_generation import REVIEW_CHECKS
from source_batch import run_batch
from source_dataset import PROGRESSIVE_CHECKS, reviewed_candidate, reviewed_contract
from trajectory_labels import TYPES
from test_category_balance import cumulative_fixture
import test_source_dataset as fixtures


class StrongBatchTests(unittest.TestCase):
    def test_routing_uses_scope_and_protects_rare_classes_without_counting_attempts(self):
        config = read_json(ROOT / "balance_config.json")
        counts = dict(cumulative=5, clarification=34, revision=8, mixed=5)
        pending = dict.fromkeys(TYPES, 0)
        original = copy.deepcopy(counts)
        endpoint = cumulative_fixture()
        route = endpoint_route(endpoint, counts, pending, config)
        self.assertEqual((route["preferred_type"], route["category_prompt_version"]), ("cumulative", "3"))
        endpoint["requirements"] = endpoint["requirements"][:1]
        route = endpoint_route(endpoint, counts, pending, config)
        self.assertNotIn("cumulative", route["eligible_types"])
        self.assertEqual(route["preferred_type"], "mixed")
        pending["mixed"] = 3
        route = endpoint_route(endpoint, counts, pending, config)
        self.assertEqual((route["preferred_type"], route["category_prompt_version"]), ("revision", "2"))
        self.assertEqual(counts, original)
        # Accepted revision becomes scarce even though other classes have many examples.
        counts["revision"] = 0
        route = endpoint_route(endpoint, counts, dict.fromkeys(TYPES, 0), config)
        self.assertEqual((route["preferred_type"], route["category_prompt_version"]), ("revision", "3"))

    def test_full_review_gated_batch_keeps_two_scope_goal_and_frozen_model(self):
        fixtures.SourceDatasetTests.setUpClass()
        fixture = fixtures.SourceDatasetTests()
        iid = fixture.row["instance_id"]
        calls = []
        def provider(source, prompt, schema, folder, config):
            self.assertEqual((config["model"], config["reasoning_effort"]), ("gpt-6.1-sol", "medium"))
            calls.append(folder.name)
            if "problem_statement" in source:
                value = cumulative_fixture()
                if "reviewed_final_requirements" in source:
                    self.assertIn("SCARCE CATEGORY PREFERENCE", prompt)
                    self.assertEqual(value["requirements"], source["reviewed_final_requirements"])
                else:
                    self.assertEqual(set(source), {"repo", "problem_statement"})
            elif "valid_plans" in source:
                self.assertEqual({p["n_messages"] for p in source["valid_plans"]}, {2})
                value = {"plan_id": source["valid_plans"][0]["plan_id"], "reason": "Natural two-scope addition."}
            else:
                self.assertIn("EXACT OUTPUT AND REPRESENTATION", prompt)
                value = {"decision": "propose_split", "reason": "Fixture.", "risks": [],
                         "messages": [{"id": s["id"], "content": " ".join(r["text_en"] for r in s["add"])} for s in source["stages"]]}
            save(folder / "request.json", {"input": source, "developer_instructions": prompt, "config": config})
            save(folder / "answer.json", value)
            return value

        def approve(folder):
            fixture.approve_contract_fixture(folder)
            r = read_json(folder / "contract_review.json")
            r["checks"].update({k: True for k in PROGRESSIVE_CHECKS})
            name = "endpoint_only" if (folder / "endpoint_only.json").exists() else "category_policy"
            r[name + "_sha256"] = digest(folder / (name + ".json"))
            save(folder / "contract_review.json", r)

        with tempfile.TemporaryDirectory(dir=ROOT / "source_runs") as tmp:
            batch = Path(tmp) / "batch"
            result = run_batch(batch, [iid], balance_categories=True, live=True, provider=provider)
            self.assertEqual(result["status_counts"], {"contract_review_pending": 1})
            self.assertEqual(run_batch(batch, live=True, provider=provider)["new_model_calls_attempted"], 0)
            endpoint = batch / iid / "contract"
            approve(endpoint)
            self.assertEqual(run_batch(batch, live=True, provider=provider, max_new_calls=0)["new_model_calls_attempted"], 0)
            self.assertFalse((batch / iid / "category_route.json").exists())
            result = run_batch(batch, live=True, max_new_calls=1, provider=provider)
            self.assertEqual(result["status_counts"], {"category_contract_review_pending": 1})
            contract = batch / iid / "category_contract"
            approve(contract)
            self.assertEqual(reviewed_contract(contract)[1]["requirements"], read_json(endpoint / "contract.json")["requirements"])
            result = run_batch(batch, live=True, max_new_calls=2, provider=provider)
            self.assertEqual(result["status_counts"], {"wording_review_pending": 1})
            run = batch / iid / "generation"
            save(run / "semantic_review.json", dict(verdict="accept_for_development", reviewer="Unit test only",
                 checks={k: True for k in REVIEW_CHECKS}, candidate_sha256=digest(run / "draft_candidate.json"),
                 plan_sha256=digest(run / "stage_plan.json"), wording_sha256=digest(run / "wording.json")))
            record = reviewed_candidate(run)
            self.assertEqual(record["trajectory_type"], "cumulative")
            self.assertEqual(set(record["final_requirement_ids"]), {"r1", "r2", "preserve_unrelated"})
            self.assertEqual(len(calls), 4)
            self.assertEqual(run_batch(batch, live=True, provider=provider)["new_model_calls_attempted"], 0)
            request = read_json(run / "wording/request.json")
            request["developer_instructions"] = "Changed wording instruction"
            save(run / "wording/request.json", request)
            with self.assertRaisesRegex(ValueError, "Wording policy"):
                reviewed_candidate(run)
            with self.assertRaisesRegex(ValueError, "construction policy"):
                run_batch(batch, construction_policy="legacy")
            cfg = read_json(batch / "model_config.json")
            cfg["model"] = "gpt-6-luna"
            save(batch / "model_config.json", cfg)
            with self.assertRaisesRegex(ValueError, "Frozen model"):
                run_batch(batch, live=True, provider=provider)


if __name__ == "__main__":
    unittest.main()
