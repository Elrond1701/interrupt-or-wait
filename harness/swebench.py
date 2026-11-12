"""Run the swe_lite_dialogues conversations through the harness on SWE-bench Lite (Docker).

Each conversation's user messages (U0, U1, optional U2) become harness pieces. The agent works in the
task's official SWE-bench image, and its final submitted patch goes to predictions.jsonl in the format
swe_lite_dialogues/split_pilot/evaluate_benchmark.py scores. Future messages stay in this process;
the agent only sees what has been delivered.

    uv run python -m harness.swebench --condition wait --instances django__django-12983 --dry-run
    uv run python -m harness.swebench --condition wait --instances django__django-12983
    uv run python -m harness.swebench --condition interrupt --all --workers 2

Needs a running Docker daemon and the model's API key (ANTHROPIC_API_KEY for the default Sonnet 4.5).
"""

import os

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")

import argparse
import concurrent.futures
import json
import platform
import re
import shlex
import subprocess
import time
import traceback
from collections import Counter
from pathlib import Path

import yaml

from minisweagent.environments import get_environment
from minisweagent.models import get_model
from minisweagent.run.benchmarks.swebench import get_swebench_docker_image_name

from harness.agents import AGENTS
from harness.pieces import TaskPieces

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "swe_lite_dialogues/split_pilot/benchmark_output/basic_v34"
SCORER = ROOT / "swe_lite_dialogues/split_pilot/evaluate_benchmark.py"
CONFIG = Path(__file__).resolve().parent / "config/interactive_swebench.yaml"
OUTPUT = ROOT / "runs/swebench"
SCORER_CONDITION = {"upfront": "full", "interrupt": "interrupt", "wait": "wait"}
"""evaluate_benchmark.py calls the upfront condition `full`."""
EMULATE_AMD64 = platform.machine().lower() in ("arm64", "aarch64")
"""SWE-bench images are x86_64 only; on Apple Silicon they run under emulation."""


def load_records(dataset_dir: Path = DATASET_DIR) -> dict[str, dict]:
    records = {}
    for line in (Path(dataset_dir) / "candidates.jsonl").read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            records[record["source"]["instance_id"]] = record
    return records


def to_pieces(record: dict, condition: str, interrupt_gap: int = 5) -> TaskPieces:
    """One user message per piece.

    Upfront gets the conversation's reconciled final task (`full_prompt`) as a single piece. Joining
    U0..U2 instead would also hand the agent requirements that later messages withdraw.
    Interrupt releases U1 right after the agent's first edit and each later message `interrupt_gap`
    steps after the previous one's trigger. This timing is provisional until the team fixes it.
    """
    if interrupt_gap < 1:
        raise ValueError("interrupt_gap must be >= 1, or later messages arrive on consecutive steps")
    tags = {
        "instance_id": record["source"]["instance_id"],
        "trajectory_type": record["trajectory_type"],
        "n_messages": len(record["messages"]),
    }
    if condition == "upfront":
        pieces = [{"id": "full", "text": record["full_prompt"]}]
    else:
        pieces = [{"id": m["id"], "text": m["content"]} for m in record["messages"]]
    if condition == "interrupt":
        for k, piece in enumerate(pieces[1:]):
            piece["release"] = {"after_first_edit": True, "plus_steps": k * interrupt_gap}
    task = TaskPieces.model_validate({"pieces": pieces, "tags": tags})
    task.check_for(condition)
    return task


def load_config(path: Path = CONFIG, *, model_name: str | None = None, step_limit: int | None = None,
                cost_limit: float | None = None) -> dict:
    config = yaml.safe_load(Path(path).read_text())
    if model_name:
        config["model"]["model_name"] = model_name
    if step_limit is not None:
        config["agent"]["step_limit"] = step_limit
    if cost_limit is not None:
        config["agent"]["cost_limit"] = cost_limit
    if EMULATE_AMD64:
        env = config["environment"]
        env["run_args"] = [*env.get("run_args", ["--rm"]), "--platform", "linux/amd64"]
    return config


def pull_image(image: str, executable: str = "docker", timeout: int = 3600) -> None:
    """Pull before starting: `docker run`'s implicit pull is cut off by the environment's 120 s timeout."""
    if subprocess.run([executable, "image", "inspect", image], capture_output=True).returncode == 0:
        return
    platform_args = ["--platform", "linux/amd64"] if EMULATE_AMD64 else []
    subprocess.run([executable, "pull", *platform_args, image], check=True, capture_output=True, text=True,
                   timeout=timeout)


def docker_env(record: dict, config: dict):
    image = get_swebench_docker_image_name({"instance_id": record["source"]["instance_id"]})
    env_config = {**config["environment"], "image": image}
    pull_image(image, env_config.get("executable", "docker"))
    return get_environment(env_config)


def run_one(record: dict, condition: str, config: dict, out_dir: Path, *, interrupt_gap: int = 5,
            make_env=docker_env, make_model=None) -> dict:
    """Run one conversation and write <instance>.traj.json and <instance>.result.json to out_dir.

    Agent outcomes (Submitted, LimitsExceeded, ...) are results. An exception (Docker, API, ...) is
    recorded under `error`; those instances are left out of predictions and rerun next time.
    """
    iid = record["source"]["instance_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"instance_id": iid, "condition": condition, "model": config["model"]["model_name"],
              "trajectory_type": record["trajectory_type"], "n_messages": len(record["messages"])}
    env = agent = None
    try:
        pieces = to_pieces(record, condition, interrupt_gap)
        env = make_env(record, config)
        model = make_model() if make_model else get_model(config=config["model"])
        agent = AGENTS[condition](model, env, pieces=pieces, output_path=out_dir / f"{iid}.traj.json",
                                  **config["agent"])
        info = agent.run()
        result |= {"exit_status": info.get("exit_status", ""), "model_patch": info.get("submission") or ""}
    except Exception as e:
        result |= {"exit_status": type(e).__name__, "model_patch": "", "error": traceback.format_exc()}
    finally:
        if agent is not None:
            base_sha = agent.snapshotter.base_sha if agent.snapshotter else ""
            result |= {
                "steps": agent.n_calls,
                "cost": round(agent.cost, 4),
                "rounds": len(agent.rounds),
                "delivered": [d["piece_id"] for d in agent.deliveries if d["status"] == "delivered"],
                "base_sha_matches": base_sha == record["source"]["base_commit"],
            }
        if env is not None and hasattr(env, "cleanup"):
            env.cleanup()
    (out_dir / f"{iid}.result.json").write_text(json.dumps(result, indent=2))
    return result


def write_predictions(out_dir: Path, model_label: str) -> tuple[Path, list[str]]:
    """predictions.jsonl with exactly the three fields evaluate_benchmark.py accepts. Empty patches stay in
    (the scorer counts them as failures); instances that hit an error are left out until rerun."""
    rows = []
    for path in sorted(out_dir.glob("*.result.json")):
        result = json.loads(path.read_text())
        if "error" not in result:
            rows.append({"instance_id": result["instance_id"], "model_name_or_path": model_label,
                         "model_patch": result["model_patch"]})
    path = out_dir / "predictions.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path, [row["instance_id"] for row in rows]


def finished(out_dir: Path, iid: str) -> bool:
    path = out_dir / f"{iid}.result.json"
    return path.exists() and "error" not in json.loads(path.read_text())


def dry_run(records: list[dict], condition: str, interrupt_gap: int) -> None:
    for record in records:
        iid = record["source"]["instance_id"]
        print(f"=== {iid} | {record['trajectory_type']} | {condition} | "
              f"{get_swebench_docker_image_name({'instance_id': iid})}")
        for i, piece in enumerate(to_pieces(record, condition, interrupt_gap).pieces):
            if i == 0:
                when = "opening task"
            elif piece.release:
                when = f"interrupt at {piece.release.label}, or on an earlier submit"
            else:
                when = "after the agent submits"
            print(f"--- {piece.id} [{when}]\n{piece.text}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--condition", choices=sorted(AGENTS), required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--instances", nargs="+", help="Instance IDs from the dataset")
    selection.add_argument("--all", action="store_true", help="All conversations in the dataset")
    parser.add_argument("--model", help="litellm model name (default: the config's, Sonnet 4.5)")
    parser.add_argument("--interrupt-gap", type=int, default=5, help="Steps between interrupt releases")
    parser.add_argument("--step-limit", type=int, help="Override the config's step limit (250)")
    parser.add_argument("--cost-limit", type=float, help="Override the config's per-task USD limit (3)")
    parser.add_argument("--workers", type=int, default=1, help="Tasks to run in parallel")
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--redo", action="store_true", help="Rerun instances that already have a result")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be delivered; no Docker or model")
    args = parser.parse_args()

    all_records = load_records(args.dataset)
    ids = sorted(all_records) if args.all else args.instances
    unknown = [i for i in ids if i not in all_records]
    if unknown:
        parser.error(f"not in the dataset: {unknown}")
    records = [all_records[i] for i in ids]
    if args.dry_run:
        dry_run(records, args.condition, args.interrupt_gap)
        return

    config = load_config(model_name=args.model, step_limit=args.step_limit, cost_limit=args.cost_limit)
    model_label = config["model"]["model_name"]
    out_dir = args.output / re.sub(r"[^A-Za-z0-9._-]+", "_", model_label) / args.condition
    todo = [r for r in records if args.redo or not finished(out_dir, r["source"]["instance_id"])]
    print(f"{args.condition} | {model_label} | {len(todo)} to run, {len(records) - len(todo)} already done "
          f"| output {out_dir}")

    def task(record):
        result = run_one(record, args.condition, config, out_dir, interrupt_gap=args.interrupt_gap)
        print(f"{result['instance_id']}: {result['exit_status']} | steps={result.get('steps')} "
              f"rounds={result.get('rounds')} cost=${result.get('cost', 0)}", flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(task, todo))

    predictions, done = write_predictions(out_dir, model_label)
    errors = [r["instance_id"] for r in results if "error" in r]
    print(f"\nexit statuses: {dict(Counter(r['exit_status'] for r in results))}")
    print(f"cost this run: ${sum(r.get('cost', 0) for r in results):.2f}")
    if errors:
        print(f"errors (left out of predictions; rerun to retry): {errors} — see <id>.result.json")
    selected = [i for i in ids if i in done]
    if selected:
        rel = lambda p: os.path.relpath(Path(p).resolve())  # noqa: E731
        job = out_dir.parent / f"eval_{args.condition}_{time.strftime('%Y%m%d-%H%M%S')}"  # prepare needs a new folder
        cmd = ["python3", rel(SCORER), "prepare", "--dataset", rel(args.dataset), "--predictions", rel(predictions),
               "--condition", SCORER_CONDITION[args.condition], "--output", rel(job), "--instance-ids", *selected]
        print(f"\npredictions: {rel(predictions)}\nscore with (then `run --job` and `summarize --job` on that folder):")
        print(shlex.join(cmd))


if __name__ == "__main__":
    main()
