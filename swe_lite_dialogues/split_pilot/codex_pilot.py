"""Run issue-only or contract-guided drafts through ChatGPT-authenticated Codex CLI.

Dry-run is the default. Each case starts fresh in an empty temporary workspace.
No API keys are read or used. Author reference files stay outside that workspace.
"""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

from model_pilot import ROOT, digest, encoded, read_json, save
from trajectory_draft import TYPES, check_saved_draft, drafting_input
from audit_trajectory import audit
from fixed_trajectory import fixed_input, check_fixed
from audit_fixed import audit_fixed
from multistage_trajectory import multistage_input, check_multistage, audit_multistage, environment_link


def child_environment(environment):
    # Preserve normal CLI login discovery; never extract/copy its credentials.
    blocked = {"OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN", "OPENAI_BASE_URL",
               "CODEX_THREAD_ID", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE"}
    return {key: value for key, value in environment.items() if key not in blocked}


def make_plan(row, config, prompt, schema, update_type=None, fixed_stages=False, trajectory=None):
    if (config["provider"] != "codex_cli_chatgpt" or config["model"] != "gpt-6-luna"
            or config["reasoning_effort"] != "low"):
        raise ValueError("This pilot is configured for Codex GPT-6 Luna with low reasoning")
    if not 1 <= config["max_invocations"] <= 3 or not 1 <= config["timeout_seconds"] <= 180:
        raise ValueError("Invalid pilot invocation/time limit")
    if config["cli_overrides"].get("forced_login_method") != "chatgpt":
        raise ValueError("ChatGPT authentication must be enforced")
    if trajectory:
        source = multistage_input(row, trajectory)
        environment_link(row, trajectory)  # Reject stale/unvalidated stage evidence before a model call.
    else:
        source = fixed_input(row, update_type) if fixed_stages else drafting_input(row, update_type)
    instructions = (prompt + "\nReturn only the final schema-conforming JSON. "
                    "Do not use any tools, inspect files, browse, or run commands.\n")
    request = {"config": config, "developer_instructions": instructions,
               "input": source, "schema": schema}
    if len(encoded(request)) > config["max_input_bytes"]:
        raise ValueError("Input too large; do not truncate source material")
    return {"instance_id": row["instance_id"], "base_commit": row["base_commit"],
            "request_sha256": hashlib.sha256(encoded(request)).hexdigest(), "request": request}


def command_for(plan, binary, workspace):
    request, config = plan["request"], plan["request"]["config"]
    command = [binary, "exec", "--ignore-user-config", "--strict-config", "--ephemeral",
               "--skip-git-repo-check", "--sandbox", "read-only", "--json",
               "--model", config["model"], "--cd", str(workspace),
               "--output-schema", str(workspace / "schema.json"),
               "--output-last-message", str(workspace / "answer.json")]
    overrides = {**config["cli_overrides"], "model_reasoning_effort": config["reasoning_effort"],
                 "developer_instructions": request["developer_instructions"],
                 "sqlite_home": str(workspace / "state"), "log_dir": str(workspace / "logs")}
    for key, value in overrides.items():
        command.extend(["-c", key + "=" + json.dumps(value, ensure_ascii=False)])
    return command + ["-"]


def inspect_events(events):
    failed = [e for e in events if e.get("type") in ("error", "turn.failed")]
    completed = [e for e in events if e.get("type") == "turn.completed"]
    in_turn = False
    actions = []
    for event in events:
        if event.get("type") == "turn.started":
            in_turn = True
        if event.get("type") not in ("item.started", "item.completed"):
            continue
        item = event.get("item", {})
        if item.get("type") == "error":
            # This CLI version encodes these two startup notices as error items.
            # Only audited notices before the turn are informational.
            known_notice = item.get("message", "").startswith((
                "Under-development features enabled:",
                "Code Mode is unavailable because code-mode host is disabled."))
            if in_turn or not known_notice:
                failed.append(event)
        elif item.get("type") not in ("agent_message", "reasoning"):
            actions.append(item.get("type"))
    # Every external action invalidates the issue-only assumption, even if the
    # tool did not succeed. Avoid claiming OS-level isolation from this audit.
    if failed:
        raise ValueError("CLI reported an error or failed turn")
    if len(completed) != 1:
        raise ValueError("Expected exactly one completed Codex turn")
    if actions:
        raise ValueError("Unexpected tool/action events; do not accept this as an issue-only draft")
    usage = completed[0].get("usage")
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0
                                         for k in ("input_tokens", "output_tokens")):
        raise ValueError("Completed turn is missing usable token accounting")
    return usage


def validate_output(draft, row, plan, out):
    if plan['request']['input'].get('draft_mode') == 'fixed_multistage':
        verdict = check_multistage(draft, row, plan['request'])
        if draft['decision'] == 'propose_split':
            evidence = audit_multistage(out, row)
            verdict.update(local_contrast_supported=evidence['local_contrast_supported'],
                           witness_status='frozen_docker_evidence_rechecked',
                           full_environment_validated=True,
                           environment_evidence_reused=True)
        return verdict
    if plan["request"]["input"].get("draft_mode") == "fixed_stages":
        verdict = check_fixed(draft, row, plan["request"])
        if draft["decision"] == "propose_split":
            local = audit_fixed(out, row)
            verdict.update(local_contrast_supported=local["local_contrast_supported"],
                           witness_status="fixed_local_probes_executed")
            if not local["local_contrast_supported"]:
                verdict["status"] = "held_failed_local_probe"
        return verdict
    verdict = check_saved_draft(draft, row, plan["request"])
    if "update_type" in plan["request"]["input"] and draft["decision"] == "propose_split":
        local = audit(out)
        verdict["local_contrast_supported"] = local["local_contrast_supported"]
        verdict["witness_status"] = "fixed_local_probes_executed"
        if not local["local_contrast_supported"]:
            verdict["status"] = "held_failed_local_probe"
    return verdict


def run_case(plan, row, binary, environment, out):
    out.mkdir(parents=True, exist_ok=False)
    save(out / "plan.json", plan)
    config = plan["request"]["config"]
    result = {"instance_id": plan["instance_id"], "request_sha256": plan["request_sha256"],
              "provider": config["provider"], "requested_model": config["model"],
              "effective_model": None, "status": "started_outcome_unknown",
              "experiment_ready": False, "billing": config["billing"]}
    save(out / "result.json", result)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="cmsc723-codex-") as directory:
        workspace = Path(directory)
        save(workspace / "schema.json", plan["request"]["schema"])
        command = command_for(plan, binary, workspace)
        save(out / "command.json", command)
        process = subprocess.Popen(command, cwd=workspace, env=environment, text=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(json.dumps(plan["request"]["input"], ensure_ascii=False),
                                                  timeout=config["timeout_seconds"])
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            timed_out = True
        (out / "events.jsonl").write_text(stdout)
        (out / "stderr.txt").write_text(stderr)
        answer = workspace / "answer.json"
        if answer.is_file():
            (out / "answer.txt").write_text(answer.read_text())
        result.update(exit_code=process.returncode, timed_out=timed_out,
                      elapsed_seconds=round(time.monotonic() - started, 2))
        try:
            events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            # Capture reported usage even when a later validation gate fails.
            result["completed_turns"] = sum(e.get("type") == "turn.completed" for e in events)
            result["reported_usages"] = [e.get("usage") for e in events if e.get("type") == "turn.completed"]
            if timed_out or process.returncode != 0:
                raise ValueError("Codex timed out or exited unsuccessfully; inspect local logs")
            result["usage"] = inspect_events(events)
            if not answer.is_file():
                raise ValueError("No final answer file")
            draft = read_json(answer)
            save(out / "draft.json", draft)
            result.update(validate_output(draft, row, plan, out))
        except (ValueError, KeyError, TypeError) as error:
            result["status"] = "failed_or_rejected"
            result["error"] = str(error)[:400]
        result["effective_model_note"] = "CLI JSONL does not independently attest the model; requested model and command are recorded."
        save(out / "result.json", result)
    return result


def recheck_run(out, row):
    """Reparse stored evidence after a parser fix, without another invocation."""
    result = read_json(out / "result.json")
    if result.get("exit_code") != 0 or result.get("timed_out"):
        raise ValueError("Only successful CLI exits can be rechecked offline")
    plan = read_json(out / "plan.json")
    source = plan["request"]["input"]
    if source.get('draft_mode') == 'fixed_multistage':
        expected_input = multistage_input(row, source['trajectory_id'])
    else:
        build_input = fixed_input if source.get("draft_mode") == "fixed_stages" else drafting_input
        expected_input = build_input(row, source.get("update_type"))
    if source != expected_input:
        raise ValueError("Source mismatch during offline recheck")
    events = [json.loads(line) for line in (out / "events.jsonl").read_text().splitlines() if line.strip()]
    usage = inspect_events(events)
    messages = [e["item"]["text"] for e in events if e.get("type") == "item.completed"
                and e.get("item", {}).get("type") == "agent_message"]
    if not messages:
        raise ValueError("No saved final agent message")
    draft = json.loads(messages[-1])
    save(out / "draft.json", draft)
    verdict = validate_output(draft, row, plan, out)
    if not (out / "result.before_recheck.json").exists():
        save(out / "result.before_recheck.json", result)
    result.pop("error", None)
    result.update(verdict, usage=usage, rechecked_offline=True,
                  recheck_parser_sha256=digest(Path(__file__)))
    save(out / "draft.json", draft)
    save(out / "result.json", result)
    return result


def check_previous(plan, runs, retry_reason):
    for path in runs.glob("*/result.json"):
        previous = read_json(path)
        if previous.get("request_sha256") != plan["request_sha256"]:
            continue
        if (previous.get("status") != "failed_or_rejected"
                or previous.get("completed_turns", 0) or not retry_reason):
            raise ValueError("Request already attempted; inspect its result before repeating")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--instance", action="append", help="Calibration ID; repeat for multiple cases")
    parser.add_argument("--retry-failed", metavar="REASON", help="Explicitly retry a reviewed failure with no completed turn")
    parser.add_argument("--recheck-run", type=Path, help="Revalidate saved JSONL without calling Codex")
    parser.add_argument("--prompt-version", choices=("v1", "v2", "v3", "v4", "v5", "v6", "v6.1"))
    parser.add_argument("--update-type", choices=TYPES, help="Use the frozen-contract two-message generator")
    parser.add_argument('--trajectory', choices=(*TYPES, 'clarification_revision'),
                        help='V6 fixed 2/3-message slugify trajectory; defaults to prompt v6.1')
    args = parser.parse_args()
    config = read_json(ROOT / "codex_config.json")
    version = args.prompt_version or ('v6.1' if args.trajectory else ("v5" if args.update_type else "v1"))
    multi_version = version in ('v6', 'v6.1')
    if multi_version != bool(args.trajectory) or (args.trajectory and args.update_type):
        raise ValueError('v6 requires --trajectory and cannot combine with --update-type')
    if (version in ("v3", "v4", "v5")) != bool(args.update_type):
        raise ValueError("v3/v4/v5 requires --update-type; v1/v2 is the legacy issue-only generator")
    schema_name = ('phrasing_schema_v6.json' if multi_version else
                   ("phrasing_schema.json" if version == "v5" else ("trajectory_schema.json" if args.update_type else "draft_schema.json")))
    schema = read_json(ROOT / schema_name)
    prompt_name = "prompts/" + ("propose_trajectory_" if args.update_type or args.trajectory else "propose_split_") + version + ".txt"
    prompt = (ROOT / prompt_name).read_text()
    batch = read_json(ROOT / "calibration_set.json")
    available = [c["instance_id"] for c in batch["cases"]]
    if version == "v5":
        available = [c["instance_id"] for c in read_json(ROOT / "fixed_contracts.json")["contracts"]]
    if multi_version:
        available = [read_json(ROOT / 'multistage_plans.json')['instance_id']]
    selected = args.instance or (["django__django-12983"] if args.update_type or args.trajectory else available)
    if (not set(selected) <= set(available) or len(set(selected)) != len(selected)
            or not 1 <= len(selected) <= config["max_invocations"]):
        raise ValueError("Select one to three distinct calibration cases")
    rows = {r["instance_id"]: r for r in read_json(ROOT / "data/lite_snapshot.json.gz")["instances"]}
    if args.recheck_run:
        if args.live:
            raise ValueError("Offline recheck cannot be combined with --live")
        record = read_json(args.recheck_run / "result.json")
        print(json.dumps(recheck_run(args.recheck_run, rows[record["instance_id"]]), ensure_ascii=False))
        return 0
    plans = [make_plan(rows[key], config, prompt, schema, args.update_type, version == "v5", args.trajectory) for key in selected]
    inputs = ["codex_pilot.py", "codex_config.json", "model_pilot.py", "trajectory_draft.py", schema_name,
              prompt_name, "calibration_set.json", "data/lite_snapshot.json.gz"]
    if args.update_type:
        inputs += ["draft_contracts.json", "requirements.json"]
    if version == "v5":
        inputs += ["fixed_contracts.json", "fixed_trajectory.py", "audit_fixed.py", "phrasing_schema.json"]
    if multi_version:
        inputs += ['fixed_contracts.json', 'fixed_trajectory.py', 'multistage_plans.json', 'multistage_trajectory.py']
    hashes = {name: digest(ROOT / name) for name in inputs}
    for plan in plans:
        plan["input_hashes"] = hashes
        plan["prompt_version"] = version
        plan["input_mode"] = ('fixed_multistage' if multi_version else
                              ("fixed_stages" if version == "v5" else ("frozen_contract" if args.update_type else "issue_only")))
    if not args.live:
        preview = ("trajectory_" + (args.trajectory or args.update_type) + "_" + version + "_dry_run.json"
                   if args.update_type or args.trajectory else "codex_dry_run.json")
        save(ROOT / "model_output" / preview, {"mode": "dry_run", "invocations": 0, "plans": plans})
        print(json.dumps({"mode": "dry_run", "invocations": 0, "selected": selected, "model": config["model"]}))
        return 0
    binary = shutil.which("codex")
    if not binary:
        raise ValueError("Codex CLI is not installed")
    environment = child_environment(os.environ)
    login = subprocess.run([binary, "login", "status"], capture_output=True, text=True,
                           env=environment, timeout=20)
    if login.returncode or "Logged in using ChatGPT" not in login.stdout + login.stderr:
        raise ValueError("ChatGPT login required; no API-key fallback")
    version = subprocess.run([binary, "--version"], capture_output=True, text=True,
                             env=environment, timeout=20).stdout.strip()
    runs = ROOT / "codex_runs"
    runs.mkdir(exist_ok=True)
    with (runs / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for plan in plans:
            check_previous(plan, runs, args.retry_failed)
        for plan in plans:
            plan.update(cli_version=version, retry_reason=args.retry_failed)
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
            out = runs / (run_id + "-" + plan["instance_id"])
            result = run_case(plan, rows[plan["instance_id"]], binary, environment, out)
            print(json.dumps({"directory": str(out), **{k: v for k, v in result.items()
                                if k not in ("author_preview", "unchecked", "reported_usages")}}, ensure_ascii=False), flush=True)
            if result["status"] == "failed_or_rejected":
                return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print("Codex pilot stopped:", str(error) if isinstance(error, ValueError) else type(error).__name__)
        raise SystemExit(2)
