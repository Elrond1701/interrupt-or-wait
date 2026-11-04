"""V6 fixed 2/3-message plans and links to existing, frozen Docker evidence.

Author-side only. No solver, LLM call, or Docker execution in this module.
Checks grammar/state mechanically; wording meaning still requires review.
"""

from pathlib import Path
import re

from model_pilot import ROOT, read_json, save, digest, schema_check
from fixed_trajectory import contract_for


def unique_ids(values):
    if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
        raise ValueError("Requirement IDs must be a list of strings")
    if len(set(values)) != len(values):
        raise ValueError("Duplicate requirement IDs")
    return set(values)


def validate_stages(contract, stages, choices):
    if len(stages) not in (2, 3) or [s['id'] for s in stages] != ['U' + str(i) for i in range(len(stages))]:
        raise ValueError("Expected ordered U0/U1 or U0/U1/U2")
    final = {r['id'] for r in contract['requirements']}
    temporary = {r['id']: set(r['replaced_by']) for r in contract['temporary_requirements']}
    known = final | set(temporary)
    uncertainties = {u['id'] for u in contract['uncertainties']}
    if final & set(temporary) or not set(choices) <= uncertainties:
        raise ValueError("Invalid contract IDs")
    for alternatives in choices.values():
        if len(alternatives) < 2 or len({tuple(sorted(x)) for x in alternatives}) != len(alternatives):
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
                if removed or not resolves or added != selected:
                    raise ValueError("Clarification must settle only its unknown dimension")
            elif kind == 'revision':
                if resolves or not removed or not removed <= set(temporary):
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
    if active != final or unknown:
        raise ValueError("Final effective requirements differ from the original endpoint")
    return trace


def load_plan(row, trajectory):
    catalog = read_json(ROOT / 'multistage_plans.json')
    if digest(ROOT / 'fixed_contracts.json') != catalog['contract_sha256']:
        raise ValueError("Fixed contract changed; review stage plans first")
    if row['instance_id'] != catalog['instance_id'] or trajectory not in catalog['variants']:
        raise ValueError("No v6 plan for this original task/trajectory")
    contract = contract_for(row, 'clarification')
    stages = catalog['variants'][trajectory]['stages']
    trace = validate_stages(contract, stages, catalog['uncertainty_choices'])
    return catalog, contract, stages, trace


def multistage_input(row, trajectory):
    catalog, contract, stages, trace = load_plan(row, trajectory)
    by_id = {r['id']: r['text_en'] for r in contract['requirements'] + contract['temporary_requirements']}
    select = lambda ids: [{'id': rid, 'text_en': by_id[rid]} for rid in ids]
    return {'draft_mode': 'fixed_multistage', 'repo': row['repo'], 'trajectory_id': trajectory,
            'context_en': contract['context_en'], 'n_messages': len(stages),
            'stages': [{'id': s['id'], 'type': s['type'],
                        'active_requirements': select(t['active_ids']),
                        'add': select(s['add']), 'remove': select(s['remove']),
                        'resolves': {uid: select(ids) for uid, ids in s['resolves'].items()},
                        'uncertainties': [{'id': uid, 'alternatives': [select(ids) for ids in catalog['uncertainty_choices'][uid]]}
                                          for uid in t['unresolved']]}
                       for s, t in zip(stages, trace)],
            'final_summary_en': contract['final_summary_en']}


def check_multistage(wording, row, request):
    source = request['input']
    if source != multistage_input(row, source['trajectory_id']):
        raise ValueError("Saved multistage input differs from the fixed plan")
    schema_check(wording, read_json(ROOT / 'phrasing_schema_v6.json'))
    if wording['decision'] == 'defer':
        if wording['messages']:
            raise ValueError("Deferred wording must have no messages")
        return {'status': 'deferred_by_model', 'experiment_ready': False}
    catalog, contract, stages, trace = load_plan(row, source['trajectory_id'])
    if [m['id'] for m in wording['messages']] != [s['id'] for s in stages]:
        raise ValueError("Model message count/order differs from fixed stages")
    if any(contract['final_summary_en'] in m['content'] for m in wording['messages']):
        raise ValueError("Model copied the final summary; only code appends it")
    process_language = r'\b(?:program|script|pipeline)\s+will\s+(?:append|attach|insert)\b|\bfinal_summary_en\b|\b(?:benchmark|hidden tests)\b'
    if any(re.search(process_language, message['content'], re.IGNORECASE) for message in wording['messages']):
        raise ValueError('Author process information leaked into a user message')
    messages = [dict(m) for m in wording['messages']]
    messages[-1]['content'] = messages[-1]['content'].strip() + '\n\n' + contract['final_summary_en']
    types = [s['type'] for s in stages[1:]]
    return {'status': 'draft_requires_semantic_review', 'experiment_ready': False,
            'update_type': types[0] if len(set(types)) == 1 else 'mixed', 'update_types': types,
            'trajectory_id': source['trajectory_id'], 'n_messages': len(messages),
            'author_preview': messages, 'state_trace': trace,
            'annotation_origin': 'fixed_author_plan_not_model_output',
            'contrast_origin': 'fixed_author_reference_not_model_output',
            'final_summary_origin': 'verbatim frozen contract appended by code',
            'unchecked': ['free-text meaning matches every stage', 'future leakage and naturalness',
                          'independent semantic review', 'agent delivery and actual interruptibility']}


def environment_link(row, trajectory):
    """Verify frozen artifacts before reusing evidence; never rerun or rewrite it."""
    catalog, contract, stages, trace = load_plan(row, trajectory)
    anchor = catalog['environment_evidence']
    directory = (ROOT / anchor['directory']).resolve()
    if not directory.is_relative_to(ROOT / 'docker_validation'):
        raise ValueError("Evidence must stay in author-side Docker results")
    checksum_file = directory / 'evidence_hashes.json'
    if digest(checksum_file) != anchor['checksums_sha256']:
        raise ValueError("Frozen environment checksum manifest changed")
    hashes = read_json(checksum_file)['files']
    paths = [checksum_file]
    for name, expected in hashes.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or digest(path) != expected:
            raise ValueError("Stale environment evidence: " + name)
        paths.append(path)
    manifest, summary = read_json(directory / 'manifest.json'), read_json(directory / 'summary.json')
    if read_json(directory / 'inputs/source.json') != row or not summary['complete']:
        raise ValueError("Environment evidence source or completion mismatch")
    for name, expected in manifest['inputs'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != expected:
            raise ValueError("Environment validation input changed: " + name)
        paths.append(path)
    if (summary['results']['gold']['official_resolution_status'] != 'RESOLVED_FULL'
            or summary['results']['base']['official_resolution_status'] != 'RESOLVED_NO'
            or not all(r['validation_expectations_met'] and all(r['checks'].values())
                       for r in summary['results'].values())):
        raise ValueError("Original base/gold/regression expectations did not pass")
    mapping, outputs = [], []
    for s, state in zip(stages, trace):
        result = summary['results'][s['reference']]
        matches = [(k, p) for k, p in result['stage_profiles'].items()
                   if set(p['requirements']) == set(state['active_ids'])]
        if len(matches) != 1 or not matches[0][1]['all_passed'] or not result['checks']['all_regression_tests_pass']:
            raise ValueError("Stage lacks matching passed environment evidence")
        profile, score = matches[0]
        mapping.append({'stage_id': s['id'], 'active_requirement_ids': state['active_ids'],
                        'unresolved': state['unresolved'], 'profile': profile,
                        'reference_implementation': s['reference'],
                        'passed': score['passed'], 'total': score['total'],
                        'report': str((directory / s['reference'] / 'container_artifacts/stage_report.json').relative_to(ROOT))})
        outputs.append(result['examples']['__A_B__'])
    if any(a == b for a, b in zip(outputs, outputs[1:])):
        raise ValueError("Adjacent reference implementations do not demonstrate a change")
    evidence = {'source_instance_id': row['instance_id'], 'full_environment_validated': True,
                'evidence_reused_not_rerun': True, 'directory': str(directory.relative_to(ROOT)),
                'checksums_sha256': anchor['checksums_sha256'], 'scope': manifest['scope'],
                'method': manifest['method'], 'stages': mapping,
                'contrast': {'input': '__A_B__', 'reference_outputs': outputs,
                             'note': 'Feasible references, not required solver trajectories or a unique U0 GT.'},
                'original_tests': {'fail_to_pass': len(json_ids(row['FAIL_TO_PASS'])),
                                   'pass_to_pass': len(json_ids(row['PASS_TO_PASS']))}}
    return evidence, paths


def json_ids(value):
    import json
    return json.loads(value) if isinstance(value, str) else value


def audit_multistage(out, row):
    out = Path(out).resolve()
    plan, draft = read_json(out / 'plan.json'), read_json(out / 'draft.json')
    result = check_multistage(draft, row, plan['request'])
    if result['status'] != 'draft_requires_semantic_review':
        raise ValueError("No proposed multistage scenario")
    evidence, paths = environment_link(row, plan['request']['input']['trajectory_id'])
    paths += [out / 'plan.json', out / 'draft.json']
    paths += [ROOT / name for name in ('multistage_plans.json', 'multistage_trajectory.py',
              'fixed_contracts.json', 'fixed_trajectory.py', 'phrasing_schema_v6.json',
              'model_pilot.py', 'pipeline.py')]
    report = {'scope': 'Rechecked frozen single-task Docker evidence; no new Docker or agent execution.',
              'base_fails_final': True, 'gold_passes_final': True, 'local_contrast_supported': True,
              'environment_evidence': evidence, 'experiment_ready': False,
              'input_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths}}
    save(out / 'local_audit.json', report)
    return report
