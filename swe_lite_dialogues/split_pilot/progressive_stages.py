"""Version 2 state validation with open questions and recorded resolutions.

The legacy validator is hash-bound to frozen evidence and remains unchanged.
"""

from multistage_trajectory import unique_ids


def validate_progressive_stages(contract, stages, choices):
    if len(stages) not in (2, 3) or [s['id'] for s in stages] != ['U' + str(i) for i in range(len(stages))]:
        raise ValueError("Expected ordered U0/U1 or U0/U1/U2")
    final = {r['id'] for r in contract['requirements']}
    temporary = {r['id']: set(r['replaced_by']) for r in contract['temporary_requirements']}
    refinements = set(contract.get('refinement_ids', []))
    if not refinements <= set(temporary):
        raise ValueError("Unknown partial requirement")
    known = final | set(temporary)
    uncertainties = {u['id'] for u in contract['uncertainties']}
    if final & set(temporary) or not set(choices) <= uncertainties:
        raise ValueError("Invalid contract IDs")
    for alternatives in choices.values():
        if len(alternatives) < 1 or len({tuple(sorted(x)) for x in alternatives}) != len(alternatives):
            raise ValueError("Uncertainty needs distinct alternatives")
        if any(not unique_ids(x) or not set(x) <= known for x in alternatives):
            raise ValueError("Unknown uncertainty choice")
    active, unknown, trace = set(), set(), []
    for index, stage in enumerate(stages):
        added, removed = unique_ids(stage['add']), unique_ids(stage['remove'])
        resolves, kind = stage['resolves'], stage['type']
        if not added <= known or not removed <= active or added & active or added & removed:
            raise ValueError("Invalid requirement addition/removal")
        if index == 0:
            unknown = unique_ids(stage.get('unknown', []))
            if kind != 'initial' or not added or removed or resolves or not unknown <= set(choices):
                raise ValueError("Invalid initial state")
        else:
            if stage.get('unknown') or not added:
                raise ValueError("No new unknowns or empty updates in this pilot")
            if not set(resolves) <= unknown:
                raise ValueError("Cannot resolve an already known dimension")
            selected = set()
            for uid, ids in resolves.items():
                selection = unique_ids(ids)
                if selection not in [set(x) for x in choices[uid]]:
                    raise ValueError("Resolution must select one declared alternative")
                selected |= selection
            if kind == 'clarification':
                if removed:
                    if (resolves or not removed <= refinements
                            or added != set().union(*(temporary[rid] for rid in removed))):
                        raise ValueError("Refinement must specify its declared partial goal completely")
                elif not resolves or added != selected:
                    raise ValueError("Clarification must settle only its unknown dimension")
            elif kind == 'revision':
                if resolves or not removed or not removed <= set(temporary) - refinements:
                    raise ValueError("Revision must retire a declared temporary requirement")
                if added != set().union(*(temporary[rid] for rid in removed)):
                    raise ValueError("Revision omits or changes its declared replacements")
            elif kind == 'addition':
                if removed or resolves or not added <= final:
                    raise ValueError("Addition cannot revise or resolve requirements")
            else:
                raise ValueError("Unsupported update type")
            unknown -= set(resolves)
        active = (active - removed) | added
        if not active:
            raise ValueError("Empty active stage")
        for rid, replacements in temporary.items():
            if rid in active and active & replacements:
                raise ValueError("Conflicting temporary and replacement requirements")
        for uid in unknown:
            if active & set().union(*(set(x) for x in choices[uid])):
                raise ValueError("Unresolved choice was already made definite")
        trace.append({'id': stage['id'], 'type': kind, 'active_ids': sorted(active),
                      'unresolved': sorted(unknown), 'added_ids': sorted(added),
                      'retired_ids': sorted(removed), 'resolved_dimensions': sorted(resolves)})
        if refinements:
            # Replacing a weaker formulation preserves its meaning, unlike a
            # policy reversal. Keep this distinction explicit for evaluation.
            trace[-1].update(refined_ids=sorted(removed & refinements),
                             pending_refinement_ids=sorted(active & refinements))
            trace[-1]['retired_ids'] = sorted(removed - refinements)
    if active != final or unknown:
        raise ValueError("Final effective requirements differ from the original endpoint")
    return trace

