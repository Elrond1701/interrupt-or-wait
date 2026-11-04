"""Print released messages using scripted actions, without a model or Docker."""

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "split_pilot"))

from benchmark_data import load_candidates
from delivery import Delivery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default="django__django-12983")
    parser.add_argument("--condition", choices=("wait", "full", "interrupt"), default="wait")
    args = parser.parse_args()
    records = load_candidates(ROOT / "split_pilot/benchmark_output/basic_v34")
    record = next((r for r in records if r["group_id"] == args.instance), None)
    if record is None:
        parser.error("Instance is not in the selected dataset")
    controller = Delivery(record, args.condition, interrupt_after=1)
    print(f"{record['group_id']} | {record['trajectory_type']} | {args.condition}")
    print("Scripted demonstration only: no code edits, model calls, or test execution.\n")
    shown = 0
    while controller.status == "running":
        users = [m for m in controller.visible_history() if m["role"] == "user"]
        for number, message in enumerate(users[shown:], start=shown):
            label = "Full final task" if args.condition == "full" else f"U{number}"
            print(f"--- {label} ---\n{message['content']}\n")
        shown = len(users)
        if args.condition == "interrupt" and shown < len(record["messages"]):
            print("[Simulated completed tool action; no command is executed.]\n")
            controller.accept({"action": "shell", "command": "demo-placeholder", "text": ""},
                              observation={"output": "Scripted observation"})
        else:
            print("[Simulated end of the current round.]\n")
            controller.accept({"action": "submit", "command": "", "text": "Scripted round complete"})
    print("Delivery completed. A real experiment would now score the agent's final patch.")


if __name__ == "__main__":
    main()
