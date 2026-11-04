"""Sequential, resumable construction batches; no automatic reviews or retries.

Preview creates only the batch plan. Live runs stop each item at missing review
files and continue other items. Completed or interrupted model stages are never
silently rerun. Use a new batch directory for an intentional retry.
"""

import argparse
from collections import Counter
import fcntl
import json
from pathlib import Path

from benchmark_data import load_candidates
from balanced_generation import category_schedule, endpoint_route, inventory
from trajectory_labels import TYPES
from model_pilot import ROOT, digest, read_json, save
from planned_generation import call_json
from source_dataset import (extract, generate_source, reviewed_candidate,
                            reviewed_contract, rows_by_id, select_primary)


def category_preference(plan, instance, endpoint):
    preferred = plan["category_preferences"][instance]
    # A locked single atom has no proper nonempty subset for cumulative U0.
    # This changes a drafting preference only, never the output's actual label.
    if (plan.get("category_strategy") == "locked_endpoint_v2"
            and preferred == "cumulative" and len(endpoint["requirements"]) == 1):
        return "clarification"
    return preferred


def prepare(folder, instances=None, existing=None, target_total=None, allow_refinement=None, balance_categories=None,
            construction_policy=None):
    folder = Path(folder).resolve()
    if not folder.is_relative_to(ROOT / "source_runs"):
        raise ValueError("Keep batch artifacts in author-side source_runs")
    path = folder / "batch_plan.json"
    if path.exists():
        plan = read_json(path)
        if instances is not None and instances != plan["instances"]:
            raise ValueError("Resume must keep the original task list")
        if existing is not None and [str(Path(p).resolve()) for p in existing] != [x["directory"] for x in plan["existing"]]:
            raise ValueError("Resume must keep the original inventory")
        if target_total is not None and target_total != plan["target_total"]:
            raise ValueError("Resume must keep the target size")
        if allow_refinement is not None and allow_refinement != plan.get("allow_refinement", False):
            raise ValueError("Resume must keep the refinement mode")
        if balance_categories is not None and balance_categories != plan.get("balance_categories", False):
            raise ValueError("Resume must keep the category balancing mode")
        if construction_policy is not None and construction_policy != plan.get("construction_policy", "legacy"):
            raise ValueError("Resume must keep the construction policy")
    else:
        rows = rows_by_id()
        if not instances or len(set(instances)) != len(instances) or any(i not in rows for i in instances):
            raise ValueError("Provide distinct IDs from the pinned source snapshot")
        target_total = 20 if target_total is None else target_total
        if type(target_total) is not int or target_total < 4:
            raise ValueError("Target size must be at least four")
        seeds, initial_records = [], []
        for item in existing or []:
            item = Path(item).resolve()
            initial_records.extend(load_candidates(item))
            seeds.append({"directory": str(item), "manifest_sha256": digest(item / "manifest.json")})
        folder.mkdir(parents=True, exist_ok=False)
        plan = {"instances": instances, "existing": seeds, "target_total": target_total,
                "snapshot_sha256": digest(ROOT / "data/lite_snapshot.json.gz"),
                "visibility": "author_only", "selection": "explicit_development_pilot_not_random_sample",
                "retry_policy": "No automatic retry. Keep failed/interrupted stages and use a new batch for a retry."}
        if allow_refinement is not None:
            plan["allow_refinement"] = allow_refinement
        if balance_categories is not None:
            plan["balance_categories"] = balance_categories
        policy = construction_policy or ("strong_v1" if balance_categories else "legacy")
        if policy not in ("legacy", "strong_v1") or (policy == "strong_v1" and not balance_categories):
            raise ValueError("Strong construction requires balanced categories")
        plan["construction_policy"] = policy
        if balance_categories:
            plan["category_strategy"] = "locked_endpoint_v3" if policy == "strong_v1" else "locked_endpoint_v2"
            if policy == "legacy":
                plan["category_preferences"] = category_schedule(
                    instances, select_primary(initial_records)[0], read_json(ROOT / "balance_config.json"))
        if policy == "strong_v1":
            config = dict(read_json(ROOT / "codex_config.json"), model="gpt-6.1-sol", reasoning_effort="medium")
            save(folder / "model_config.json", config)
            plan["model_config_sha256"] = digest(folder / "model_config.json")
            plan["balance_config_sha256"] = digest(ROOT / "balance_config.json")
            plan["prompt_hashes"] = {name: digest(ROOT / "prompts" / name) for name in (
                "extract_endpoint_v1.txt", "extract_category_v2.txt", "extract_category_v3.txt",
                "select_stage_plan_v5.txt", "select_stage_plan_v6.txt", "propose_trajectory_v10.txt")}
        save(path, plan)
        for name in ("source_batch.py", "source_dataset.py", "balance_config.json", "codex_config.json"):
            dest = folder / "inputs" / name
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())
    if digest(ROOT / "data/lite_snapshot.json.gz") != plan["snapshot_sha256"]:
        raise ValueError("Pinned source snapshot changed")
    records = []
    for item in plan["existing"]:
        directory = Path(item["directory"])
        if digest(directory / "manifest.json") != item["manifest_sha256"]:
            raise ValueError("Starting inventory changed")
        records.extend(load_candidates(directory))
    records = select_primary(records)[0]
    if plan.get("construction_policy") == "strong_v1":
        if digest(folder / "model_config.json") != plan["model_config_sha256"]:
            raise ValueError("Frozen model profile changed")
        if (digest(folder / "inputs/balance_config.json") != plan["balance_config_sha256"] or
                digest(ROOT / "balance_config.json") != plan["balance_config_sha256"]):
            raise ValueError("Frozen balance configuration changed")
        for name, expected in plan["prompt_hashes"].items():
            if digest(ROOT / "prompts" / name) != expected:
                raise ValueError("Frozen construction prompt changed: " + name)
    elif plan.get("balance_categories"):
        expected = category_schedule(plan["instances"], records, read_json(folder / "inputs/balance_config.json"))
        if plan.get("category_preferences") != expected:
            raise ValueError("Saved category preferences changed")
    return folder, plan, records


def run_batch(folder, instances=None, existing=None, target_total=None, live=False,
              max_new_calls=3, provider=call_json, allow_refinement=None, balance_categories=None, construction_policy=None):
    if type(max_new_calls) is not int or max_new_calls < 0:
        raise ValueError("Call budget must be a nonnegative integer")
    folder, plan, records = prepare(folder, instances, existing, target_total, allow_refinement, balance_categories, construction_policy)
    # A second process must not spend calls on the same unfinished batch.
    with (folder / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return advance(folder, plan, records, live, max_new_calls, provider)


def advance(folder, plan, records, live, max_new_calls, provider):
    strong = plan.get("construction_policy") == "strong_v1"
    neutral = plan.get("category_strategy") in {"locked_endpoint_v1", "locked_endpoint_v2", "locked_endpoint_v3"}
    calls_path = folder / "calls.json"
    calls = read_json(calls_path) if calls_path.exists() else []
    initial_count = len(calls)

    def remaining():
        return max_new_calls - (len(calls) - initial_count)

    def counted_provider(source, prompt, schema, stage_folder):
        if not live or remaining() <= 0:
            raise ValueError("New-call budget exhausted")
        entry = {"stage": str(stage_folder.relative_to(folder)), "status": "started"}
        calls.append(entry)
        save(calls_path, calls)
        try:
            kwargs = {"config": read_json(folder / "model_config.json")} if strong else {}
            value = provider(source, prompt, schema, stage_folder, **kwargs)
        except Exception as exc:
            entry.update(status="failed", error=str(exc))
            save(calls_path, calls)
            raise
        entry["status"] = "returned"
        save(calls_path, calls)
        return value

    rows, items = rows_by_id(), []
    # Include all already reviewed batch items before allocating any new calls.
    accepted = {}
    for instance in plan["instances"]:
        run = folder / instance / "generation"
        if (run / "semantic_review.json").exists():
            try:
                accepted[instance] = reviewed_candidate(run)
            except (OSError, ValueError, KeyError, StopIteration):
                pass
    records = select_primary(records + list(accepted.values()))[0]
    selected_ids = {r["source"]["instance_id"] for r in records}

    def checkpoint():
        usage = {"completed_model_calls": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
        for entry in calls:
            path = folder / entry["stage"] / "result.json"
            if path.exists():
                for value in read_json(path).get("reported_usages", []):
                    usage["completed_model_calls"] += 1
                    for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
                        usage[key] += value.get(key, 0)
        summary = {"mode": "live" if live else "preview", "planned_originals": len(plan["instances"]),
                   "items": items, "status_counts": dict(Counter(i["status"] for i in items)),
                   "new_model_calls_attempted": len(calls) - initial_count,
                   "total_model_calls_attempted": len(calls), "reported_usage": usage,
                   "note": "Construction only. Saved reviews are required; no Docker or solver execution is implied."}
        save(folder / "summary.json", summary)
        return summary

    for instance in plan["instances"]:
        item = {"instance_id": instance}
        contract = folder / instance / "contract"
        run = folder / instance / "generation"
        try:
            if instance in selected_ids:
                item["status"] = "reviewed_candidate_available" if instance in accepted else "already_selected"
                continue
            if not contract.exists():
                if not live or remaining() < 1:
                    item["status"] = "extraction_pending"
                    continue
                extract(rows[instance], contract, live=True, provider=counted_provider,
                        allow_refinement=False if neutral else plan.get("allow_refinement", False),
                        preferred_type=None if neutral else plan.get("category_preferences", {}).get(instance),
                        endpoint_only=neutral)
            saved_state = read_json(contract / "status.json")
            state = saved_state["status"]
            # A saved review can repair a citation-only extraction error. The
            # original failed status/answer stay intact; reviewed_contract
            # still checks the unchanged task and all review bindings below.
            repaired_review = state == "failed_or_rejected" and (contract / "contract_review.json").exists()
            if state != "contract_requires_review" and not repaired_review:
                item["status"] = "extraction_incomplete" if state == "dry_run" else "extraction_" + state
                if "error" in saved_state:
                    item["reason"] = saved_state["error"]
                elif state == "deferred_by_model":
                    item["reason"] = read_json(contract / "contract.json")["reason"]
                continue
            if not (contract / "contract_review.json").exists():
                item["status"] = "contract_review_pending"
                continue
            review = read_json(contract / "contract_review.json")
            if review.get("verdict") == "hold":
                item.update(status="contract_review_hold", reason=review.get("reason", "Saved contract review is on hold"))
                continue
            _, endpoint, _ = reviewed_contract(contract)
            if neutral:
                designed = folder / instance / "category_contract"
                prompt_version = "1"
                if strong:
                    route_path = folder / instance / "category_route.json"
                    config = read_json(folder / "inputs/balance_config.json")
                    if route_path.exists():
                        route = read_json(route_path)
                        expected = endpoint_route(endpoint, route["accepted_counts"], route["pending_reservations"], config)
                        expected["endpoint_sha256"] = digest(contract / "contract.json")
                        if route != expected:
                            raise ValueError("Saved endpoint routing changed")
                    else:
                        if not live or remaining() < 1:
                            item["status"] = "category_extraction_pending"
                            continue
                        reservations = dict.fromkeys(TYPES, 0)
                        for other in plan["instances"]:
                            route_file = folder / other / "category_route.json"
                            if other in selected_ids or not route_file.exists():
                                continue
                            base = folder / other
                            reviews = [base / "category_contract/contract_review.json", base / "generation/semantic_review.json"]
                            states = [base / "category_contract/status.json", base / "generation/status.json"]
                            if any(p.exists() and read_json(p).get("verdict") == "hold" for p in reviews):
                                continue
                            if any(p.exists() and read_json(p).get("status") in ("failed_or_rejected", "deferred_by_model", "wording_deferred") for p in states):
                                continue
                            stage = base / "generation/stage_plan.json"
                            kind = read_json(stage)["trajectory_type"] if stage.exists() else read_json(route_file)["preferred_type"]
                            reservations[kind] += 1
                        counts = inventory(records)["counted_original_class_pairs"]
                        route = endpoint_route(endpoint, counts, reservations, config)
                        route["endpoint_sha256"] = digest(contract / "contract.json")
                        save(route_path, route)
                    preferred, prompt_version = route["preferred_type"], route["category_prompt_version"]
                    item["category_preference"] = route
                else:
                    preferred = category_preference(plan, instance, endpoint)
                    item["category_preference"] = {
                        "scheduled": plan["category_preferences"][instance], "effective": preferred,
                        "single_requirement_fallback": preferred != plan["category_preferences"][instance]}
                if not designed.exists():
                    if not live or remaining() < 1:
                        item["status"] = "category_extraction_pending"
                        continue
                    extract(rows[instance], designed, live=True, provider=counted_provider,
                            seed_folder=contract, preferred_type=preferred,
                            allow_refinement=plan.get("allow_refinement", False), category_prompt_version=prompt_version)
                if (plan.get("category_strategy") in {"locked_endpoint_v2", "locked_endpoint_v3"}
                        and read_json(designed / "category_policy.json")["preferred_type"] != preferred):
                    raise ValueError("Saved category preference differs from reviewed endpoint routing")
                if strong and read_json(designed / "category_policy.json")["version"] != "category_v" + prompt_version:
                    raise ValueError("Saved category prompt differs from reviewed endpoint routing")
                state = read_json(designed / "status.json")
                if state["status"] != "contract_requires_review":
                    item.update(status="category_" + state["status"], reason=state.get("error", "See saved category draft"))
                    continue
                if not (designed / "contract_review.json").exists():
                    item["status"] = "category_contract_review_pending"
                    continue
                review = read_json(designed / "contract_review.json")
                if review.get("verdict") == "hold":
                    item.update(status="category_contract_review_hold", reason=review.get("reason", "Category draft held"))
                    continue
                reviewed_contract(designed)
                contract = designed
            if not run.exists():
                if not live or remaining() < 2:
                    item["status"] = "generation_pending"
                    continue
                generate_source(contract, run, records, total=plan["target_total"], live=True, provider=counted_provider,
                                precise_wording=strong)
            saved_state = read_json(run / "status.json")
            state = saved_state["status"]
            if state != "draft_requires_semantic_review":
                item["status"] = "generation_incomplete" if state == "dry_run" else "generation_" + state
                if "error" in saved_state:
                    item["reason"] = saved_state["error"]
                continue
            if not (run / "semantic_review.json").exists():
                item["status"] = "wording_review_pending"
                continue
            review = read_json(run / "semantic_review.json")
            if review.get("verdict") == "hold":
                item.update(status="wording_review_hold", reason=review.get("reason", "Saved wording review is on hold"))
                continue
            record = reviewed_candidate(run)
            records.append(record)
            selected_ids.add(instance)
            item["status"] = "reviewed_candidate_available"
        except (OSError, ValueError, KeyError, StopIteration, RuntimeError) as exc:
            item.update(status="held_or_failed", reason=str(exc))
        finally:
            items.append(item)
            checkpoint()
    return checkpoint()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--instances", nargs="+")
    parser.add_argument("--existing", type=Path, nargs="*")
    parser.add_argument("--target-total", type=int)
    parser.add_argument("--max-new-calls", type=int, default=3)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--allow-refinement", action="store_true", default=None,
                        help="Try compatible partial-to-complete goals; mode is frozen on resume")
    parser.add_argument("--balance-categories", action="store_true", default=None,
                        help="New balanced batches default to Sol/medium and endpoint-aware routing")
    parser.add_argument("--construction-policy", choices=("legacy", "strong_v1"))
    args = parser.parse_args()
    result = run_batch(args.output, args.instances, args.existing, args.target_total, args.live, args.max_new_calls,
                       allow_refinement=args.allow_refinement, balance_categories=args.balance_categories,
                       construction_policy=args.construction_policy)
    print(json.dumps({k: result[k] for k in ("status_counts", "new_model_calls_attempted", "reported_usage")}))


if __name__ == "__main__":
    main()
