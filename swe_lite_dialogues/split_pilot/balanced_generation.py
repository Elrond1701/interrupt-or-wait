"""Soft class quotas for one construction attempt at a time; preview by default.

Only reviewed exports count. Rewordings of the same original/class count once.
This adapter does not certify naturalness or promote evaluation readiness.
"""

import argparse
import json
from fractions import Fraction
from pathlib import Path

from benchmark_data import load_candidates
from model_pilot import ROOT, read_json, save
from planned_generation import generate, planning_context, validate_plan
from stage_plan_options import enumerate_options
from trajectory_labels import TYPES, label_record

REVIEWED_STATUSES = {
    "offline_checked_pending_full_validation",
    "environment_checked_pending_independent_review_and_agent",
    "semantic_reviewed_pending_new_stage_validation",
}


def quotas(total, config):
    weights = config["target_percent"]
    if type(total) is not int or total < len(TYPES):
        raise ValueError("Use at least four slots to represent all four classes")
    if (set(weights) != set(TYPES) or any(type(w) is not int or w <= 0 for w in weights.values())
            or sum(weights.values()) != 100):
        raise ValueError("Four positive integer percentages must sum to 100")
    cap = config["max_classes_per_original"]
    if type(cap) is not int or not 1 <= cap <= len(TYPES):
        raise ValueError("Invalid per-original class limit")
    desired = {kind: Fraction(total * weights[kind], 100) for kind in TYPES}
    counts = {kind: max(1, int(desired[kind])) for kind in TYPES}
    # Allocate remaining slots to the largest shortfall. For tiny batches,
    # one slot per class takes precedence over exact percentages.
    while sum(counts.values()) < total:
        kind = max(TYPES, key=lambda k: desired[k] - counts[k])
        counts[kind] += 1
    while sum(counts.values()) > total:
        kind = max((k for k in TYPES if counts[k] > 1), key=lambda k: counts[k] - desired[k])
        counts[kind] -= 1
    return counts


def inventory(records):
    seen_scenarios, pairs, groups = set(), set(), {}
    raw_counts = dict.fromkeys(TYPES, 0)
    ignored = 0
    for original in records:
        record = label_record(original)
        scenario = record["scenario_id"]
        if scenario in seen_scenarios:
            continue
        seen_scenarios.add(scenario)
        if record.get("validation", {}).get("status") not in REVIEWED_STATUSES:
            ignored += 1
            continue
        kind, group = record["trajectory_type"], record["group_id"]
        if group != record["source"]["instance_id"]:
            raise ValueError("Quota group must retain the original task identity")
        raw_counts[kind] += 1
        pairs.add((group, kind))
        groups.setdefault(group, set()).add(kind)
    return {"reviewed_variant_counts": raw_counts,
            "counted_original_class_pairs": {k: sum(kind == k for _, kind in pairs) for k in TYPES},
            "distinct_originals_by_class": {k: sorted(g for g, kind in pairs if kind == k) for k in TYPES},
            "existing_classes_by_original": {g: sorted(kinds) for g, kinds in sorted(groups.items())},
            "ignored_unreviewed_scenarios": ignored,
            "extra_wordings_not_counted": sum(raw_counts.values()) - len(pairs)}


def category_schedule(instances, records, config):
    """Reserve attempt preferences, not successful samples, for a frozen batch."""
    quotas(max(4, len(records)), config)  # Validate the existing soft targets.
    floor = config.get("minimum_category_percent", 10)
    if type(floor) is not int or not 0 <= floor <= 25:
        raise ValueError("Minimum category percentage must be between 0 and 25")
    counts = inventory(records)["counted_original_class_pairs"].copy()
    preferred = {}
    for instance in instances:
        if instance in preferred:
            raise ValueError("Category schedule needs distinct originals")
        total = max(1, sum(counts.values()))
        rare = [k for k in TYPES if counts[k] * 100 < total * floor]
        pool = rare or list(TYPES)
        kind = min(pool, key=lambda k: (
            counts[k] if rare else Fraction(counts[k], config["target_percent"][k]), TYPES.index(k)))
        preferred[instance] = kind
        # A reservation prevents hammering the same empty class throughout a
        # review-gated batch. Only real reviewed records enter future counts.
        counts[kind] += 1
    return preferred


def endpoint_route(endpoint, counts, reservations, config):
    """Pick a feasible drafting preference; pending slots are never successes."""
    quotas(max(4, sum(counts.values())), config)
    for values in (counts, reservations):
        if set(values) != set(TYPES) or any(type(n) is not int or n < 0 for n in values.values()):
            raise ValueError("Invalid class inventory")
    floor = config.get("minimum_category_percent", 10)
    if type(floor) is not int or not 0 <= floor <= 25:
        raise ValueError("Invalid class floor")
    eligible = [k for k in TYPES if k != "cumulative" or len(endpoint["requirements"]) >= 2]
    projected = {k: counts[k] + reservations[k] for k in TYPES}
    rare = [k for k in eligible if projected[k] * 100 < max(1, sum(projected.values())) * floor]
    kind = min(rare or eligible, key=lambda k: (
        projected[k] if rare else Fraction(projected[k], config["target_percent"][k]), TYPES.index(k)))
    protect = counts[kind] * 100 < max(1, sum(counts.values())) * floor
    return {"preferred_type": kind, "category_prompt_version": "3" if protect else "2",
            "protect_rare_class": protect, "eligible_types": eligible,
            "accepted_counts": counts.copy(), "pending_reservations": reservations.copy()}


def propose(row, records, total, config):
    target, current = quotas(total, config), inventory(records)
    counts = current["counted_original_class_pairs"]
    deficits = {k: max(0, target[k] - counts[k]) for k in TYPES}
    priority = sorted(TYPES, key=lambda k: (-Fraction(deficits[k], target[k]), -deficits[k], TYPES.index(k)))
    existing = current["existing_classes_by_original"].get(row["instance_id"], [])
    report = {"mode": "construction_plan_not_new_data", "instance_id": row["instance_id"],
              "config": config, "target_total": total, "target_counts": target, "inventory": current,
              "remaining_counts": deficits, "priority_order": priority, "selected": None, "skipped": [],
              "readiness_note": "Counts are reviewed development coverage, not environment-validated benchmark size."}
    if not any(deficits.values()):
        report["status"] = "targets_met_no_new_attempt"
        return report
    if len(existing) >= config["max_classes_per_original"]:
        report["status"] = "need_other_original_source_limit"
        return report
    for kind in priority:
        if not deficits[kind] or kind in existing:
            report["skipped"].append({"trajectory_type": kind, "reason": "target_met_or_original_class_already_counted"})
            continue
        for length in (2, 3):
            if kind == "mixed" and length == 2:
                continue
            try:
                context = planning_context(row, kind, length)
                options = enumerate_options(context, validate_plan)
            except ValueError as exc:
                report["skipped"].append({"trajectory_type": kind, "n_messages": length, "reason": str(exc)})
                continue
            if not options:
                report["skipped"].append({"trajectory_type": kind, "n_messages": length, "reason": "no_legal_plan"})
                continue
            report["status"] = "one_attempt_proposed_pending_model_choice_and_review"
            report["selected"] = {"trajectory_type": kind, "n_messages": length, "legal_plan_count": len(options)}
            return report
    report["status"] = "no_eligible_plan_keep_deficits"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default="django__django-12983")
    parser.add_argument("--existing", type=Path, nargs="*", default=[])
    parser.add_argument("--target-total", type=int, default=20)
    parser.add_argument("--config", type=Path, default=ROOT / "balance_config.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "quota_runs"):
        raise ValueError("Keep quota records in author-side quota_runs")
    records = [r for folder in args.existing for r in load_candidates(folder)]
    row = next(r for r in read_json(ROOT / "data/lite_snapshot.json.gz")["instances"] if r["instance_id"] == args.instance)
    report = propose(row, records, args.target_total, read_json(args.config))
    output.mkdir(parents=True, exist_ok=False)
    save(output / "allocation.json", report)
    if args.live and report["selected"]:
        selected = report["selected"]
        # No retry or reassignment after a model refusal. Only reviewed exports
        # supplied to a later invocation can increase the accepted counts.
        generate(row, selected["trajectory_type"], selected["n_messages"], output / "generation", live=True)
    print(json.dumps({"status": report["status"], "target_counts": report["target_counts"],
                      "remaining_counts": report["remaining_counts"], "selected": report["selected"],
                      "generation_status": read_json(output / "generation/status.json") if (output / "generation/status.json").exists() else "not_run"}))


if __name__ == "__main__":
    main()
