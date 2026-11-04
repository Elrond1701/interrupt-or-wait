"""Small mixed-length menu; retain short fallbacks without extra model calls."""

from copy import deepcopy

from planned_generation import validate_plan
from stage_plan_options import enumerate_options


def build_menu(make_context, kinds, lengths):
    options, feasibility = [], []
    for length in lengths:
        for kind in kinds:
            if kind == "mixed" and length == 2:
                continue
            legal = enumerate_options(make_context(kind, length), validate_plan)
            feasibility.append({"trajectory_type": kind, "n_messages": length,
                                "legal_plan_count": len(legal)})
            # Bound prompt size. Include different endpoints of the deterministic
            # enumeration; the complete structural count remains in the report.
            selected = [legal[0], legal[-1]] if len(legal) > 1 else legal
            for item in selected:
                item = deepcopy(item)
                item["plan_id"] = "P" + str(len(options) + 1)
                item.update(n_messages=length, trajectory_type=kind)
                options.append(item)
    return options, feasibility
