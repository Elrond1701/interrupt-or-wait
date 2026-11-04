import json
import unittest

from delivery import DecisionBudgetExceeded, Delivery, run_episode


def record(n=3):
    return {"messages": [{"id": "U" + str(i), "content": "SECRET_STAGE_" + str(i)} for i in range(n)],
            "full_prompt": "FINAL_ONLY", "gold_patch": "DO_NOT_DISCLOSE"}


def action(kind="shell", command="edit"):
    return {"action": kind, "command": command if kind == "shell" else "", "text": kind}


class Workspace:
    def __init__(self):
        self.state = []

    def execute(self, command):
        self.state.append(command)
        return {"output": list(self.state)}

    def snapshot(self, call):
        return "snapshot-" + str(call)


class DeliveryTests(unittest.TestCase):
    def test_future_and_author_fields_absent(self):
        c = Delivery(record())
        text = json.dumps(c.visible_history())
        for secret in ("SECRET_STAGE_1", "SECRET_STAGE_2", "DO_NOT_DISCLOSE"):
            self.assertNotIn(secret, text)
        h = c.visible_history()
        h.clear()
        self.assertEqual(len(c.history), 1)

    def test_wait_retains_code_and_history_three_rounds(self):
        c, w, seen = Delivery(record()), Workspace(), []
        script = iter([action(command="a"), action("submit"), action(command="b"),
                       action("submit"), action(command="c"), action("submit")])
        def model(history, call):
            seen.append(history)
            return next(script)
        r = run_episode(c, model, w)
        self.assertEqual(r["status"], "completed")
        self.assertEqual(w.state, ["a", "b", "c"])
        self.assertEqual(r["released_stages"], ["U0", "U1", "U2"])
        self.assertIn("a", json.dumps(seen[-1]))
        self.assertNotIn("SECRET_STAGE_2", json.dumps(seen[3]))
        self.assertEqual([e["after_tools"] for e in r["events"] if e["event"] == "delivery"], [0, 1, 2])

    def test_interrupt_only_after_tool_observation(self):
        c = Delivery(record(), "interrupt", 2)
        for i in range(4):
            c.accept(action(), {"output": str(i)}, str(i))
            self.assertEqual(c.stage, min((i + 1) // 2, 2))
        self.assertEqual([m["role"] for m in c.history[-2:]], ["tool", "user"])
        self.assertEqual([e["after_tools"] for e in c.events if e["event"] == "delivery"], [0, 2, 4])
        self.assertEqual([e["reason"] for e in c.events if e["event"] == "delivery"],
                         ["initial", "tool_boundary", "tool_boundary"])

    def test_early_end_is_not_silent_interrupt(self):
        c = Delivery(record(2), "interrupt", 2)
        c.accept(action("submit"))
        self.assertEqual(c.events[-1]["reason"], "turn_end_before_scheduled_interrupt")

    def test_question_needs_alignment_review(self):
        c = Delivery(record(2), "interrupt")
        c.accept(action("ask"))
        self.assertEqual(c.status, "needs_scripted_answer_review")
        self.assertEqual(c.stage, 0)
        d = Delivery(record(2), "interrupt")
        d.accept(action("ask"), scripted_answer_reviewed=True)
        self.assertEqual(d.events[-1]["reason"], "question_reviewed_before_scheduled_interrupt")

    def test_budget_is_not_reset_or_forced_handoff(self):
        c, w = Delivery(record()), Workspace()
        r = run_episode(c, lambda h, n: action("submit") if n == 2 else action(), w, max_calls=3)
        self.assertEqual(r["status"], "budget_exhausted")
        self.assertEqual(r["model_calls"], 3)
        self.assertEqual(r["released_stages"], ["U0", "U1"])

    def test_full_releases_final_only(self):
        c = Delivery(record(), "full")
        self.assertEqual(c.visible_history(), [{"role": "user", "content": "FINAL_ONLY"}])
        c.accept(action("submit"))
        self.assertEqual(c.status, "completed")
        with self.assertRaises(ValueError):
            c.accept(action("submit"))

    def test_adapter_budget_is_not_execution_error(self):
        def exhausted(history, call):
            raise DecisionBudgetExceeded("input budget")
        r = run_episode(Delivery(record()), exhausted, Workspace())
        self.assertEqual(r["status"], "budget_exhausted")
        self.assertEqual(r["tool_calls"], 0)
        self.assertEqual(r["released_stages"], ["U0"])

    def test_invalid_order_action_and_tool_result(self):
        r = record()
        r["messages"][1]["id"] = "U2"
        with self.assertRaises(ValueError):
            Delivery(r)
        c = Delivery(record())
        with self.assertRaises(ValueError):
            c.accept(action())
        result = run_episode(c, lambda h, n: {"action": "danger"}, Workspace())
        self.assertEqual(result["status"], "execution_error")


if __name__ == "__main__":
    unittest.main()
