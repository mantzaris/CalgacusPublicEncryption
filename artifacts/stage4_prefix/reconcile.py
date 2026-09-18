#!/usr/bin/env python3
"""Reconcile retained Stage 4 evidence; stdlib only, no model/ledger mutation."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts/stage4_prefix'
START = 'fe3aeaddd7df1d4fb3b19c49ccc84251a519d39f'
TESTED = '32edd3bf54712a8134659f298b8958462024c2a0'

def read(path):
    return json.loads(Path(path).read_text())

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

def near(a, b):
    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9), (a, b)

def dump(name, value):
    (ART / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

allocation = read(ART / 'allocation.json')
anchor = read(ART / 'budget_anchor.json')
status = read(ART / 'run_status.json')
environment = read(ART / 'environment.json')
records = [json.loads(l) for l in (ART / 'cases.jsonl').read_text().splitlines()]
profile = read(ROOT / 'configs/public_utf8_rank16_v1.json')
profile_hash = sha(canonical(profile))
assert profile_hash == allocation['profile_sha256']
assert status['tested_code_commit'] == TESTED
assert len(records) == len(allocation['slots']) == status['recorded_outcomes'] == 21
assert not status['skipped'] and not status.get('controller_exception')
assert len({r['attempt_id'] for r in records}) == len({r['pid'] for r in records}) == 21
ledger_raw = (ROOT / anchor['path']).read_bytes()
history = subprocess.check_output(['git', 'show', START + ':' + anchor['path']], cwd=ROOT)
assert len(history) == anchor['bytes'] and sha(history) == anchor['sha256']
assert ledger_raw[:len(history)] == history
checkpoint = read(ROOT / 'artifacts/project_budget.checkpoint.json')
assert checkpoint['bytes'] == len(ledger_raw) and checkpoint['sha256'] == sha(ledger_raw)
events = [json.loads(l) for l in ledger_raw.splitlines()]
new_events = [json.loads(l) for l in ledger_raw[len(history):].splitlines()]
assert len(new_events) == 42
charged = {}
for event in events:
    aid = event['attempt_id']
    if event['event'] == 'reserve':
        assert aid not in charged
        charged[aid] = event['reserved']
    else:
        assert event['event'] == 'settle' and aid in charged
        charged[aid] = event['charged']
usage = {k: sum(c[k] for c in charged.values()) for k in ('seconds', 'tokens', 'cases')}
for k in usage:
    near(usage[k], status['cumulative_usage'][k])
    near(usage[k] - anchor['usage'][k], status['incremental_usage'][k])
    assert usage[k] <= allocation['global_limits'][k]
    assert status['incremental_usage'][k] <= allocation['additional_limits'][k]

# All tracked earlier artifacts/code remain exactly identifiable at the baseline.
protected = ['src/llm_stego_public_key/codecs', 'src/llm_stego_public_key/cryptography',
             'src/llm_stego_public_key/transport', 'src/llm_stego_public_key/profile.py',
             'src/llm_stego_public_key/evaluation/budget.py',
             'src/llm_stego_public_key/evaluation/worker_guard.py',
             'configs', 'artifacts/stage1', 'artifacts/stage1_review',
             'artifacts/stage2_pilot', 'artifacts/stage3_transport',
             'STAGE1_FOUNDATIONS_REPORT.md', 'STAGE1_REVIEW_REPORT.md',
             'STAGE2_PILOT_REPORT.md', 'STAGE3_TRANSPORT_REPORT.md',
             'scripts/run_smoke.py', 'scripts/gpu_worker.py', 'scripts/run_pilot.py',
             'scripts/gpu_transport_worker.py', 'scripts/run_stage3.py']
assert not subprocess.check_output(['git', 'diff', START, '--', *protected], cwd=ROOT)
assert not subprocess.check_output(['git', 'diff', TESTED, '--', 'src', 'scripts', 'tests', 'configs'], cwd=ROOT)

predictions = {}
historical = []
controls = []
phase_totals = {}
steps = []
running = dict(anchor['usage'])
for index, (r, slot) in enumerate(zip(records, allocation['slots'])):
    directory = ROOT / r['evidence_dir']
    job, command, claim = [read(directory / f) for f in ('input.json', 'command.json', 'worker_claim.json')]
    assert read(directory / 'outcome.json') == r
    result = read(directory / 'result.json')
    assert all(r[k] == v for k, v in result.items())
    assert r['case_id'] == slot['case_id'] and r['kind'] == slot['kind']
    assert r['success'] and r['exit_code'] == 0 and r['failure_category'] is None
    assert not r['authenticated'] and not r['authenticated_message_recovery']
    assert r['split'] == allocation['split']
    assert r['profile_sha256'] == profile_hash
    assert r['tested_code_commit'] == job['tested_code_commit'] == TESTED
    assert job['source_provenance']['commit'] == TESTED
    assert not job['source_provenance']['tracked_and_untracked_code_dirty']
    assert job['source_provenance']['checked_immediately_before_reservation']
    for flag in ('gpu_verified', 'lease_verified', 'phase_meter_verified', 'provenance_verified'):
        assert r[flag]
    env = command['environment']
    assert env['STAGE1_JOB_SHA256'] == sha((directory / 'input.json').read_bytes())
    assert claim['attempt_id'] == r['attempt_id'] == env['STAGE1_GOVERNED_ATTEMPT']
    assert claim['pid'] == r['pid'] and claim['controller_pid'] == int(env['STAGE1_CONTROLLER_PID'])
    assert claim['deadline_monotonic'] == float(env['STAGE1_DEADLINE_MONOTONIC'])
    assert command['argv'][1].endswith('/scripts/gpu_prefix_worker.py')
    assert command['reservation_seconds'] == job['wall_reservation_seconds'] == 45
    assert job['token_reservation'] == 64
    assert r['worker_seconds'] <= r['job_elapsed_seconds'] < 37
    assert r['gpu_uuid'] == environment['selected_gpu']['uuid']
    samples = read(directory / 'gpu_samples.json')
    matched = [s for s in samples if s['pid'] == r['pid'] and s['gpu_uuid'] == r['gpu_uuid']]
    assert matched and max(s['used_vram_mib'] for s in matched) == r['peak_sampled_process_vram_mib']
    assert 'offloaded 33/33 layers to GPU' in (directory / 'worker.log').read_text()
    reserve, settle = new_events[index*2:index*2+2]
    assert reserve['event'] == 'reserve' and settle['event'] == 'settle'
    assert reserve['attempt_id'] == settle['attempt_id'] == r['attempt_id']
    assert reserve['tested_code_commit'] == TESTED and reserve['case_id'] == slot['case_id']
    assert reserve['reserved'] == {'seconds': 45, 'tokens': 64, 'cases': 1}
    assert settle['charged'] == {'seconds': r['job_elapsed_seconds'], 'tokens': r['charged_tokens'], 'cases': 1}
    for k in running:
        assert running[k] + reserve['reserved'][k] <= allocation['global_limits'][k]
        assert running[k] - anchor['usage'][k] + reserve['reserved'][k] <= allocation['additional_limits'][k]
        running[k] += settle['charged'][k]
        near(running[k], r['cumulative_budget'][k])
    trace = r['trace']
    context = r['cover_context']
    assert context == profile['cover_contexts'][slot['context_index']]
    assert len(trace['advanced_ids']) == 6
    actual_context_ids = r['public_context_token_ids'][context]
    assert actual_context_ids == allocation['public_context_prelaunch_checks'][slot['context_index']]['context_token_ids']
    assert r['charged_tokens'] == slot['expected_evaluated_tokens'] == len(actual_context_ids) + 6
    assert r['charged_tokens'] == sum(r['tokens_by_phase'].values())
    for k, v in r['tokens_by_phase'].items():
        phase_totals[k] = phase_totals.get(k, 0) + v
    steps.extend(trace['candidate_steps'])
    wire = (directory / 'snippet.txt').read_bytes()
    assert bytes.fromhex(r['retained_generated_prefix_hex']) == wire
    if slot['kind'] == 'prediction':
        p = r['prediction']
        assert read(directory / 'public_prediction.json') == p
        assert p['token_ids'] == trace['advanced_ids'] and trace['symbols'] == [0]*6
        assert p['prefix_utf8'].encode('utf-8') == wire
        key = sha(canonical({'observer_id': 'public_zero6_v1', 'profile_sha256': profile_hash, 'cover_context': context}))
        assert p['cache_key'] == key and p['cover_context'] == context
        assert p['provenance']['tested_code_commit'] == TESTED
        assert p['provenance']['attempt_id'] == r['attempt_id'] and p['provenance']['pid'] == r['pid']
        assert len(p['scores']) == len(trace['candidate_steps']) == 6
        for pos, (score, candidate) in enumerate(zip(p['scores'], trace['candidate_steps'])):
            ids, logits = score['admissible_ids'], score['admissible_logits']
            assert len(ids) == len(set(ids)) == len(logits) == 16
            assert score['position'] == pos and score['token_id'] == ids[0] == p['token_ids'][pos]
            assert sorted(zip(ids, logits), key=lambda x: (-x[1], x[0])) == list(zip(ids, logits))
            assert candidate['ordered_ids_sha256'] == sha(b''.join(i.to_bytes(4, 'big') for i in ids))
            # Independently recompute B's conditional probabilities from retained logits.
            log_b = logits[0] - max(logits) - math.log(math.fsum(math.exp(x-max(logits)) for x in logits))
            near(log_b, score['B_log_probability'])
            near(math.exp(log_b), score['B_probability_admissible_zero'])
            near(math.exp(score['A_log_probability']), score['A_probability_latent_token'])
        for family, label in [('A', 'latent_sequence'), ('B', 'prefix_match')]:
            logp = math.fsum(s[family+'_log_probability'] for s in p['scores'])
            near(logp, p[family+'_log_probability_'+label])
            near(math.exp(logp), p[family+'_probability_'+label])
        near(p['C_probability_prefix_match'], 16**-6)
        assert [h['path'] for h in r['historical_reanalysis']] == slot['historical_carrier_paths']
        for h in r['historical_reanalysis']:
            raw = (ROOT / h['path']).read_bytes()
            raw.decode('utf-8', errors='strict')
            assert sha(raw) == h['transport_sha256']
            assert h['observer']['observed_prefix_ids'] == p['token_ids']
            assert h['observer']['prefix_match'] and h['observer']['status'] == 'match'
            historical.append(dict(h, context_index=slot['context_index'], prediction_attempt_id=r['attempt_id']))
        predictions[slot['context_index']] = dict(p, evidence_dir=r['evidence_dir'], historical_matches=len(r['historical_reanalysis']))
    else:
        p = predictions[slot['context_index']]
        assert r['family'] == slot['family'] and r['sampling_seed'] == slot['sampling_seed']
        assert r['prediction_cache_key'] == p['cache_key']
        assert r['prediction_sha256'] == job['prediction_sha256'] == sha((ROOT / r['prediction_path']).read_bytes())
        assert r['prediction_path'] == p['evidence_dir'] + '/public_prediction.json'
        assert r['generated_tokens'] == 6
        assert wire.decode('utf-8') == r['snippet_utf8'] and wire == bytes.fromhex(r['snippet_bytes_hex'])
        assert r['serialization_outcome'] == 'canonical' and r['text_retokenizes']
        assert r['retokenized_ids'] == trace['advanced_ids']
        assert r['observer']['observed_prefix_ids'] == r['retokenized_ids'][:6]
        match = r['retokenized_ids'][:6] == p['token_ids']
        assert r['observer']['prefix_match'] == match
        assert r['observer']['status'] == ('match' if match else 'valid_nonmatch')
        if r['family'] == 'A':
            assert trace['symbols'] == [None]*6 and not trace['candidate_steps']
        else:
            assert all(0 <= s < 16 for s in trace['symbols']) and len(trace['candidate_steps']) == 6
        controls.append({k: r[k] for k in ['case_id', 'attempt_id', 'context_index', 'family', 'sampling_seed', 'snippet_utf8', 'serialization_outcome', 'observer', 'evidence_dir', 'charged_tokens', 'job_elapsed_seconds']})
assert len(historical) == len({h['path'] for h in historical}) == 6
assert all(s['eligible_found_capped_at_16'] == 16 and 16 <= s['examined'] <= 128 for s in steps)

def counts(group):
    return {'attempted': len(group), 'prefix_matches': sum(r['observer']['prefix_match'] for r in group),
            'valid_nonmatches': sum(r['observer']['status'] == 'valid_nonmatch' for r in group),
            'invalid_utf8': sum(r['observer']['status'] == 'invalid_utf8' for r in group),
            'insufficient_tokens': sum(r['observer']['status'] == 'insufficient_tokens' for r in group),
            'retokenization_changes': sum(r['serialization_outcome'] == 'retokenization_change' for r in group),
            'candidate_exhaustions': 0, 'runtime_failures': 0}

summary = {'schema_version': 1, 'split': allocation['split'], 'starting_commit': START, 'gpu_tested_code_commit': TESTED,
           'verdict': 'bounded public-prefix diagnostic completed; predictable framing confirmed for this profile',
           'planned_cases': 21, 'attempted_cases': len(records), 'prediction_cases': 3, 'control_cases': len(controls),
           'skipped_cases': status['skipped'], 'new_encrypted_transmissions': 0, 'new_authenticated_recoveries': 0,
           'historical_artifacts_reanalyzed': len(historical), 'historical_prefix_matches': 6,
           'control_totals': {f: counts([r for r in controls if r['family'] == f]) for f in 'ABC'},
           'controls_by_context': {str(c): {f: counts([r for r in controls if r['family'] == f and r['context_index'] == c]) for f in 'ABC'} for c in range(3)},
           'baseline_usage': anchor['usage'], 'incremental_usage': status['incremental_usage'], 'cumulative_usage': status['cumulative_usage'],
           'remaining_project_headroom': {k: allocation['global_limits'][k]-usage[k] for k in usage},
           'phase_evaluated_tokens': phase_totals, 'selected_gpu': environment['selected_gpu'],
           'peak_sampled_process_vram_mib': max(r['peak_sampled_process_vram_mib'] for r in records),
           'job_seconds': {'min': min(r['job_elapsed_seconds'] for r in records), 'median': statistics.median(r['job_elapsed_seconds'] for r in records), 'max': max(r['job_elapsed_seconds'] for r in records)},
           'load_and_verify_seconds_total': math.fsum(r['timings']['load_and_verify_seconds'] for r in records),
           'operation_and_host_observation_seconds_total': math.fsum(r['timings']['operation_and_host_observation_seconds'] for r in records),
           'admission': {'candidate_steps': len(steps), 'examined_min': min(s['examined'] for s in steps), 'examined_max': max(s['examined'] for s in steps),
                         'rejected_candidates_by_reason': {k: sum(s['rejected'][k] for s in steps) for k in steps[0]['rejected']}},
           'all_workers_clean_exit_full_offload_pid_gpu_lease_phase_and_provenance_verified': True,
           'full_cpu_suite_rerun': False, 'focused_new_tests_passed': 5, 'focused_allocation_checks_passed': 5,
           'scientific_limits': ['no general false-positive/operational accuracy estimate', 'A probability is latent-token path only',
               'B/C probabilities assume ideal specified draws; fixed seeds are deterministic', 'historical artifacts selected; unknown full stego and cover abort rates',
               'no HPKE break, sender authentication, edit robustness or concealment proof', 'novelty and latest manuscript overlap unresolved']}
dump('summary.json', summary)
dump('public_predictions.json', {'schema_version': 1, 'contexts': predictions})
dump('control_outcomes.json', {'schema_version': 1, 'cases': controls})
dump('historical_reanalysis.json', {'schema_version': 1, 'cases': historical})
reconciliation = {'schema_version': 1, 'status': 'PASS', 'inference': False,
    'tested_source': TESTED, 'scope': 'retained evidence reconciliation, not another CPU implementation test suite',
    'attempts_reconciled': len(records), 'new_ledger_events': len(new_events),
    'historical_ledger_prefix': {'bytes': len(history), 'sha256': sha(history), 'unchanged': True},
    'final_ledger': {'bytes': len(ledger_raw), 'sha256': sha(ledger_raw)},
    'checks': ['immutable IDs and exact fixed slot order; no missing attempts/retries', 'every full reservation fits both ceilings',
        'ledger charges and summary/result/phase counts agree', 'clean tested-source provenance and public prediction cache hashes',
        '21 distinct fresh worker PIDs, one-shot lease claims, matching GPU samples and full offload logs',
        'all complete jobs below 37-second deadline, including import/load/shutdown',
        'historical ledger complete byte prefix, old artifacts/codecs/profiles unchanged',
        'zero-symbol prediction and candidate-order digests', 'B probabilities independently recomputed from saved logits',
        'A/B log-products and ideal C probability reconciled', 'exact snippet bytes, retained tokenization records and prefix decisions consistent'],
    'limitations': ['Artifact reconciliation does not rerun native inference or tokenizer',
        'A full-vocabulary normalization was computed by the worker; complete logits not retained',
        'Existing full CPU results do not test this new observer/controller code']}
dump('reconciliation.json', reconciliation)
print(json.dumps({'status': 'PASS', 'attempts': len(records), 'incremental_usage': status['incremental_usage'], 'cumulative_usage': status['cumulative_usage'], 'controls': summary['control_totals']}, indent=2))
