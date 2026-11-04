"""Enumerate a small menu of mechanically valid plans from a prepared pool.

This bounded pilot is not a general planner: at most six requirement IDs and
two unknown dimensions. Semantic quality remains a separate review decision.
"""

from itertools import combinations, product

from trajectory_labels import classify


def subsets(values, nonempty=False):
    values = sorted(values)
    for count in range(int(nonempty), len(values) + 1):
        yield from (list(s) for s in combinations(values, count))


def enumerate_options(context, validate):
    final = {r["id"] for r in context["final_requirements"]}
    temporary = {r["id"]: r["replaced_by"] for r in context["temporary_requirements"]}
    choices = context["uncertainty_choices"]
    known = final | set(temporary)
    invariants = set(context["invariant_ids"])
    if len(known) > 6 or len(choices) > 2:
        raise ValueError("Prepared pool exceeds this small enumeration pilot")

    def stage(kind, add, remove=None, unknown=None, resolves=None):
        return {"id": "U0", "type": kind, "add": sorted(add), "remove": sorted(remove or []),
                "unknown": sorted(unknown or []), "resolves": resolves or [],
                "rationale": "Rule-enumerated " + kind + "; semantic suitability requires review."}

    updates = [stage("addition", ids) for ids in subsets(final - invariants, nonempty=True)]
    for uid, alternatives in choices.items():
        for ids in alternatives:
            updates.append(stage("clarification", ids, resolves=[{"dimension": uid, "requirement_ids": ids}]))
    for ids in subsets(temporary, nonempty=True):
        replacements = set().union(*(temporary[rid] for rid in ids))
        kind = "clarification" if set(ids) <= set(context.get("refinement_ids", [])) else "revision"
        updates.append(stage(kind, replacements, remove=ids))

    sequences = [seq for seq in product(updates, repeat=context["n_messages"] - 1)
                 if classify([s["type"] for s in seq]) == context["requested_trajectory_type"]]
    options = []
    for extra in subsets(known - invariants, nonempty=context.get("planning_version") != "2"):
        for unknown in subsets(choices):
            initial = stage("initial", invariants | set(extra), unknown=unknown)
            for sequence in sequences:
                stages = [dict(item, id="U" + str(i)) for i, item in enumerate([initial, *sequence])]
                plan = {"decision": "propose_plan", "trajectory_type": context["requested_trajectory_type"],
                        "reason": "Rule-enumerated candidate; not yet selected for naturalness.", "stages": stages}
                try:
                    validate(plan, context)
                except ValueError:
                    continue
                options.append({"plan_id": "P" + str(len(options) + 1), "plan": plan})
    return options


def selection_schema(options):
    return {"type": "object", "additionalProperties": False,
            "required": ["plan_id", "reason"], "properties": {
                "plan_id": {"type": "string", "enum": [o["plan_id"] for o in options] + ["none"]},
                "reason": {"type": "string", "minLength": 1, "maxLength": 600}}}
