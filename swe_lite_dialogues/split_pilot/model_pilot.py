"""Small author-side drafting pilot. Dry-run by default; no solver execution.

Only problem_statement and repo enter the provider request. The output remains a
draft until semantic review and executable validation in the existing pipeline.
Uses Python's standard library. No provider SDK, implicit retry or fallback.
"""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import uuid

from pipeline import ROOT, digest, read_json

ENDPOINT = "https://api.openai.com/v1/responses"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def schema_check(value, schema, path="draft"):
    """Validate the small JSON Schema subset used by draft_schema.json locally."""
    kind = schema["type"]
    expected = {"object": dict, "array": list, "string": str}[kind]
    if not isinstance(value, expected):
        raise ValueError(f"{path}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: invalid enum")
    if kind == "object":
        if set(value) != set(schema["required"]) or set(value) - set(schema["properties"]):
            raise ValueError(f"{path}: missing or unexpected fields")
        for key, item in value.items():
            schema_check(item, schema["properties"][key], f"{path}.{key}")
    elif kind == "array":
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", math.inf):
            raise ValueError(f"{path}: invalid array length")
        for index, item in enumerate(value):
            schema_check(item, schema["items"], f"{path}[{index}]")
    elif (len(value.strip()) < schema.get("minLength", 0)
          or len(value) > schema.get("maxLength", math.inf)
          or ("pattern" in schema and not re.fullmatch(schema["pattern"], value))):
        raise ValueError(f"{path}: invalid string")


def check_draft(draft, row, schema):
    schema_check(draft, schema)
    if draft["decision"] == "defer":
        if any(draft[k] for k in ("context_en", "requirements", "stages", "update_checks")):
            raise ValueError("A deferred draft must not contain a proposed scenario")
        return {"status": "deferred_by_model", "experiment_ready": False}
    requirements = draft["requirements"]
    by_id = {r["id"]: r for r in requirements}
    if len(requirements) < 2 or len(by_id) != len(requirements):
        raise ValueError("At least two unique requirements are needed")
    if not draft["context_en"].strip():
        raise ValueError("Missing task context")
    if [s["id"] for s in draft["stages"]] != ["U0", "U1"]:
        raise ValueError("This calibration requires exactly U0 and U1")
    if len(draft["update_checks"]) != 1:
        raise ValueError("Missing proposed U1 witness")
    for requirement in requirements:
        if requirement["source_quote"] not in row["problem_statement"]:
            raise ValueError("Source quote not found in problem_statement")
        deps = requirement["depends_on"]
        if len(deps) != len(set(deps)) or not set(deps) <= set(by_id):
            raise ValueError("Invalid requirement dependencies")
    visiting, visited = set(), set()

    def visit(rid):
        if rid in visiting:
            raise ValueError("Cyclic requirement dependencies")
        if rid in visited:
            return
        visiting.add(rid)
        for parent in by_id[rid]["depends_on"]:
            visit(parent)
        visiting.remove(rid)
        visited.add(rid)

    for rid in by_id:
        visit(rid)
    active, messages = set(), []
    for stage in draft["stages"]:
        ids = stage["requirement_ids"]
        if len(ids) != len(set(ids)) or set(ids) & active or not set(ids) <= set(by_id):
            raise ValueError("Unknown or repeated stage requirement")
        active.update(ids)
        if any(not set(by_id[rid]["depends_on"]) <= active for rid in ids):
            raise ValueError("A requirement depends on an unreleased requirement")
        header = draft["context_en"] if stage["id"] == "U0" else "Add these requirements to the current task:"
        messages.append({"id": stage["id"], "content": header + "\n" +
                         "\n".join("- " + by_id[rid]["text_en"] for rid in ids)})
    if active != set(by_id):
        raise ValueError("An extracted requirement was omitted from the stages")
    return {
        "status": "draft_requires_semantic_review", "experiment_ready": False,
        "witness_status": "proposed_not_executed", "author_preview": messages,
        "unchecked": ["source entailment and complete coverage", "future information leakage",
                      "meaningful update and naturalness", "base/gold and regression tests",
                      "executed partial-solution witness", "actual interruptibility"],
    }


def make_request(row, config, prompt, schema):
    # Explicit allowlist. In particular, no hints_text, patch, test_patch or
    # previous annotations/verification results are sent to the drafting model.
    source = {"repo": row["repo"], "problem_statement": row["problem_statement"]}
    return {
        "model": config["model"], "reasoning": {"effort": config["reasoning_effort"]},
        "service_tier": "default", "store": False,
        "max_output_tokens": config["max_output_tokens"],
        "input": [{"role": "developer", "content": prompt},
                  {"role": "user", "content": json.dumps(source, ensure_ascii=False)}],
        "text": {"format": {"type": "json_schema", "name": "split_draft_v1",
                             "strict": True, "schema": schema}},
    }


def validate_config(config):
    if (config["provider"] != "openai_responses" or config["model"] != "gpt-6-luna"
            or config["service_tier"] != "default" or config["reasoning_effort"] != "low"):
        raise ValueError("This pilot only has a verified OpenAI Luna/low/standard configuration")
    for field in ("max_calls", "max_output_tokens", "max_request_bytes", "timeout_seconds"):
        if type(config[field]) is not int or config[field] <= 0:
            raise ValueError(f"Invalid positive integer: {field}")
    if config["max_calls"] > 3 or config["max_output_tokens"] > 4096 or config["max_request_bytes"] > 40000:
        raise ValueError("Pilot limits: 3 calls, 4096 output tokens, 40000 request bytes")
    rates = config["usd_per_million_tokens"]
    if rates != {"input": 0.10, "output": 0.50, "input_reserve": 0.25}:
        raise ValueError("Pricing changed: update and review the reservation logic first")
    if not math.isfinite(config["budget_usd"]) or not 0 < config["budget_usd"] <= 0.10:
        raise ValueError("Pilot budget must be positive and at most $0.10")


def plan_batch(rows, config, prompt, schema):
    validate_config(config)
    if not rows or len(rows) > config["max_calls"] or len({r["instance_id"] for r in rows}) != len(rows):
        raise ValueError("Empty, duplicate or excessive task selection")
    entries = []
    rates = config["usd_per_million_tokens"]
    for row in rows:
        request = make_request(row, config, prompt, schema)
        body = encoded(request)
        if len(body) > config["max_request_bytes"]:
            raise ValueError("Request too large; do not silently truncate an issue")
        estimate = len(body) + 1024  # Includes schema and conservative wrapper allowance.
        reserve = (estimate * rates["input_reserve"] +
                   config["max_output_tokens"] * rates["output"]) / 1_000_000
        entries.append({"instance_id": row["instance_id"], "base_commit": row["base_commit"],
                        "request_sha256": hashlib.sha256(body).hexdigest(),
                        "input_tokens_estimate": estimate, "reserved_usd_estimate": reserve,
                        "request": request})
    total = sum(e["reserved_usd_estimate"] for e in entries)
    if total > config["budget_usd"]:
        raise ValueError("Preflight budget would be exceeded")
    return {"mode": "dry_run", "api_calls": 0, "experiment_ready_count": 0,
            "budget_usd": config["budget_usd"], "reserved_usd_estimate": total,
            "budget_note": config["budget_note"], "requests": entries}


def extract_draft(response):
    if response.get("status") != "completed":
        raise ValueError("Response incomplete or failed; no automatic retry")
    chunks = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    raise ValueError("Provider refusal")
                if content.get("type") == "output_text":
                    chunks.append(content["text"])
    if not chunks:
        raise ValueError("No output text")
    return json.loads("".join(chunks))


def usage_cost(response, config):
    usage = response.get("usage") or {}
    if not isinstance(usage, dict):
        return None
    counts = [usage.get("input_tokens"), usage.get("output_tokens")]
    if any(type(n) is not int or n < 0 for n in counts):
        return None
    rates = config["usd_per_million_tokens"]
    # Conservative estimate from returned usage; no cache discount assumed.
    # This is not the provider's invoice or evidence of a precise dollar charge.
    return (counts[0] * rates["input_reserve"] + counts[1] * rates["output"]) / 1_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send_openai(request, key, timeout):
    """Provider boundary; a future DeepSeek adapter can keep the draft contract."""
    http_request = urllib.request.Request(ENDPOINT, data=encoded(request), method="POST",
                                          headers={"Authorization": "Bearer " + key,
                                                   "Content-Type": "application/json"})
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(http_request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not echo server error bodies, headers or the authentication value.
        raise RuntimeError(f"OpenAI HTTP {error.code}; no automatic retry") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise RuntimeError("Network/response failure; outcome may be unknown; no automatic retry") from None


def run_batch(plan, rows, schema, config, out, send):
    """Write a reservation before each request; keep failed/unknown attempts."""
    out.mkdir(parents=True, exist_ok=False)
    save(out / "plan.json", plan)
    results, charged = [], 0.0
    for entry in plan["requests"]:
        result = {"instance_id": entry["instance_id"], "request_sha256": entry["request_sha256"],
                  "status": "started_outcome_unknown", "experiment_ready": False,
                  "reserved_usd_estimate": entry["reserved_usd_estimate"]}
        result_path = out / (entry["instance_id"] + ".json")
        save(result_path, result)
        charged += entry["reserved_usd_estimate"]
        response = None
        stop = False
        try:
            response = send(entry["request"])
            if not isinstance(response, dict):
                response = None
                raise ValueError("Provider response must be an object")
            result["response"] = response
            cost = usage_cost(response, config)
            result["usage_cost_usd_estimate"] = cost
            if cost is not None:
                charged += cost - entry["reserved_usd_estimate"]
            if (cost is None or cost > entry["reserved_usd_estimate"]
                    or response.get("service_tier", "default") != "default"):
                stop = True
                result["billing_review_required"] = True
            draft = extract_draft(response)
            result["draft"] = draft
            result.update(check_draft(draft, rows[entry["instance_id"]], schema))
        except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as error:
            result["status"] = "request_failed" if response is None else "response_rejected"
            # Validation/provider errors are controlled locally. Never store raw
            # error bodies or raw exceptions from an unknown provider adapter.
            result["error_type"] = type(error).__name__
            if isinstance(error, ValueError):
                result["error"] = str(error)[:400]
            if isinstance(error, RuntimeError) and str(error).startswith("OpenAI HTTP "):
                result["error"] = str(error)
            stop = True
        save(result_path, result)
        results.append({k: v for k, v in result.items() if k not in ("response", "draft", "author_preview")})
        if stop:
            break
    report = {"mode": "live", "api_attempts": len(results), "results": results,
              "accounted_usd_estimate": charged, "experiment_ready_count": 0,
              "not_attempted": len(plan["requests"]) - len(results),
              "note": "Drafting only; unknown charges retain reservation; no solver or harness run."}
    save(out / "report.json", report)
    return report


def reject_repeated_requests(plan, runs):
    requested = {r["request_sha256"] for r in plan["requests"]}
    # Failed/time-out requests also count: restarting must not repeat charges.
    for previous in runs.glob("*/*.json"):
        record = read_json(previous)
        if record.get("request_sha256") in requested:
            raise ValueError("An identical request was already attempted; inspect its record before rerunning")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Make at most three paid requests")
    parser.add_argument("--key-file", type=Path, help="Explicit private file containing only the API key")
    args = parser.parse_args()
    config = read_json(ROOT / "model_config.json")
    batch = read_json(ROOT / "calibration_set.json")
    schema = read_json(ROOT / "draft_schema.json")
    prompt = (ROOT / "prompts/propose_split_v1.txt").read_text()
    snapshot = read_json(ROOT / "data/lite_snapshot.json.gz")
    rows = {r["instance_id"]: r for r in snapshot["instances"]}
    plan = plan_batch([rows[c["instance_id"]] for c in batch["cases"]], config, prompt, schema)
    plan["provenance"] = {"config": config, "batch_version": batch["version"],
                          "hashes": {name: digest(ROOT / name) for name in (
                              "model_pilot.py", "pipeline.py", "data/lite_snapshot.json.gz",
                              "model_config.json", "calibration_set.json", "draft_schema.json",
                              "prompts/propose_split_v1.txt")}}
    if not args.live:
        save(ROOT / "model_output/dry_run.json", plan)
        print(json.dumps({k: v for k, v in plan.items() if k not in ("requests", "provenance")}, indent=2))
        return 0
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if base_url != "https://api.openai.com/v1":
        raise ValueError("Custom endpoints are not configured for this OpenAI pilot")
    key = args.key_file.read_text().strip() if args.key_file else os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or any(c.isspace() for c in key):
        print("No usable API key. Set OPENAI_API_KEY or use --key-file; no request was sent.")
        return 2
    runs = ROOT / "model_runs"
    runs.mkdir(exist_ok=True)
    with (runs / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        reject_repeated_requests(plan, runs)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        out = runs / run_id
        plan["mode"] = "live_plan"
        report = run_batch(plan, rows, schema, config, out,
                           lambda request: send_openai(request, key, config["timeout_seconds"]))
        print(json.dumps({"run_directory": str(out), **report}, indent=2))
        return int(bool(report["not_attempted"]) or any(
            r["status"] in ("request_failed", "response_rejected") or r.get("billing_review_required")
            for r in report["results"]))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as error:
        # OSError may contain a private credential path; do not echo its text.
        print("Pilot stopped before proceeding:", str(error) if isinstance(error, ValueError) else type(error).__name__)
        raise SystemExit(2)
