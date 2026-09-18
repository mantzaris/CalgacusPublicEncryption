#!/usr/bin/env python3
"""Fixed authorized diagnostic allocation; no retries or discretionary extra cases."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger, amounts
from llm_stego_public_key.profile import canonical_json
from run_smoke import execute, revision, validate_resume, write_new

ART = ROOT / 'artifacts/stage2_pilot'
LIMITS = {'seconds': 1200, 'tokens': 8000, 'cases': 12}
RESERVATIONS = {'historical_replay': [60, 600], 'fresh_encrypted': [120, 2000],
                'control': [90, 1200], 'fresh_replay': [60, 750]}
FATAL = {'implementation_failure', 'rank_numerical_divergence', 'timeout_resource_failure'}


def admit(usage, baseline, requested):
    amounts(requested)
    if any(usage[k] < baseline[k] or usage[k] - baseline[k] + requested[k] > LIMITS[k]
           for k in LIMITS):
        raise BudgetError('Full reservation does not fit the additional pilot ceiling')


class PilotLedger:
    def __init__(self, ledger, baseline):
        self.ledger, self.baseline = ledger, baseline

    def __getattr__(self, name):
        return getattr(self.ledger, name)

    def reserve(self, seconds, tokens, cases=1, **metadata):
        admit(self.usage(), self.baseline, {'seconds': seconds, 'tokens': tokens, 'cases': cases})
        return self.ledger.reserve(seconds, tokens, cases, **metadata)


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def allocation_check(allocation):
    """Only the new admission arithmetic and fixed reservation contract; no model/tests suite."""
    assert allocation['pilot_limits'] == LIMITS
    assert len(allocation['slots']) == 12
    assert len({s['case_id'] for s in allocation['slots']}) == 12
    assert [s['family'] for s in allocation['slots']] == (
        ['historical_replay'] * 4 + ['fresh_encrypted'] * 4 + ['control'] * 2 + ['fresh_replay'] * 2)
    for slot in allocation['slots']:
        assert slot['reservation'] == RESERVATIONS[slot['family']]
    baseline = allocation['baseline_usage']
    request = {'seconds': 60, 'tokens': 600, 'cases': 1}
    boundary = {k: baseline[k] + LIMITS[k] - request[k] for k in LIMITS}
    admit(boundary, baseline, request)
    for key in LIMITS:
        outside = dict(boundary)
        outside[key] += 1
        try:
            admit(outside, baseline, request)
        except BudgetError:
            pass
        else:
            raise AssertionError('Admission accepted excess ' + key)
    print(json.dumps({'allocation_check': 'PASS', 'checks': 5,
                      'scope': 'fixed allocation, exact boundary, one-over seconds/tokens/cases',
                      'gpu_work': False}), flush=True)


def replay_job(slot, source, profile):
    # Expected payload/hash and encoder diagnostics remain exclusively in the controller.
    original = json.loads((ROOT / source['evidence_dir'] / 'input.json').read_text())
    carrier = ROOT / source['evidence_dir'] / 'carrier.txt'
    if hashlib.sha256(carrier.read_bytes()).hexdigest() != source['transport_sha256']:
        raise RuntimeError('Saved carrier provenance mismatch')
    return {'kind': 'replay', 'case_id': slot['case_id'],
            'context_index': profile['cover_contexts'].index(source['cover_context']),
            'carrier_path': str(carrier.relative_to(ROOT)),
            'TEST_ONLY_private_key_hex': original['TEST_ONLY_private_key_hex']}


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allocation-check', action='store_true')
    args = parser.parse_args()
    allocation = json.loads((ART / 'allocation.json').read_text())
    if args.allocation_check:
        allocation_check(allocation)
        return
    code = revision()
    frozen = ['artifacts/stage2_pilot/' + f for f in
              ['allocation.json', 'migration.json', 'TEST_ONLY_keys.json', 'environment.json']]
    if subprocess.check_output(['git', 'diff', 'HEAD', '--', *frozen], cwd=ROOT):
        raise RuntimeError('Frozen pilot inputs changed after source commit')
    for path in frozen:
        subprocess.check_call(['git', 'ls-files', '--error-unmatch', path], cwd=ROOT,
                              stdout=subprocess.DEVNULL)
    if (ART / 'run_status.json').exists():
        raise RuntimeError('Pilot already completed or stopped; no automatic resumption')
    profile = json.loads((ROOT / 'configs/public_profile.json').read_text())
    if hashlib.sha256(canonical_json(profile)).hexdigest() != allocation['profile_sha256']:
        raise RuntimeError('Frozen profile mismatch')
    runtime = json.loads((ROOT / 'configs/local_runtime.json').read_text())
    migration = json.loads((ART / 'migration.json').read_text())
    if allocation['baseline_usage'] != migration['prior_usage']:
        raise BudgetError('Pilot baseline does not match immutable migration')
    keys = {k['key_id']: k for k in json.loads((ART / 'TEST_ONLY_keys.json').read_text())['keys']}
    historical = rows(ROOT / 'artifacts/stage1/cases.jsonl')
    ledger = BudgetLedger(ROOT / 'artifacts/project_budget.jsonl', anchor=migration)
    pilot = PilotLedger(ledger, allocation['baseline_usage'])
    status = {'schema_version': 1, 'tested_code_commit': code,
              'split': 'development_only_excluded_from_future_heldout', 'skipped': []}
    try:
        results = rows(ART / 'cases.jsonl')
        validate_resume(ledger, historical + results)
        if results:
            raise BudgetError('Interrupted pilot requires review; no implicit continuation')
        for slot in allocation['slots']:
            family = slot['family']
            fresh = [r for r in results if r['kind'] == 'encrypted']
            if family in ('control', 'fresh_replay') and sum(bool(r['success']) for r in fresh) < 2:
                status['stop_reason'] = 'Fewer than two of four fresh transmissions recovered exactly'
                break
            source = None
            if family == 'historical_replay':
                source = next(r for r in historical if r['attempt_id'] == slot['source_attempt_id'])
                job = replay_job(slot, source, profile)
            elif family == 'fresh_replay':
                source = next((r for r in fresh if r.get('key_id') == slot['key_id'] and r['success']), None)
                if source is None:
                    status['skipped'].append({'case_id': slot['case_id'], 'reason': 'No successful new carrier for this key'})
                    continue
                job = replay_job(slot, source, profile)
            elif family == 'fresh_encrypted':
                job = {k: slot[k] for k in ['kind', 'case_id', 'key_id', 'payload_hex', 'context_index', 'public_observer']}
                job['TEST_ONLY_private_key_hex'] = keys[slot['key_id']]['TEST_ONLY_private_key_hex']
            else:
                match = next((r for r in fresh if r.get('cover_context') == profile['cover_contexts'][slot['context_index']]
                              and r.get('carrier_tokens') and (ROOT / r['evidence_dir'] / 'carrier.txt').exists()), None)
                job = {k: slot[k] for k in ['kind', 'case_id', 'context_index', 'sampling_seed']}
                job.update(target_tokens=match['carrier_tokens'] if match else slot['fallback_tokens'],
                           matched_attempt_id=match['attempt_id'] if match else None)
            job['profile_sha256'] = allocation['profile_sha256']
            record = execute(pilot, job, runtime, code, artifact_root=ART,
                             reservation=slot['reservation'], replay_source=source,
                             expected_rejection=slot.get('expected_rejection', False))
            results.append(record)
            if (record.get('failure_category') in FATAL or not record['provenance_verified']
                    or not record['lease_verified'] or not record['phase_meter_verified']
                    or not record['gpu_verified'] or record['exit_code'] != 0):
                status['stop_reason'] = 'Fatal execution/accounting/provenance gate: ' + slot['case_id']
                break
            if len({r.get('pid') for r in results}) != len(results):
                status['stop_reason'] = 'Receiver/worker PID uniqueness gate failed'
                break
            if family in ('historical_replay', 'fresh_replay') and not record['expected_outcome_agreement']:
                status['stop_reason'] = 'Unexpected replay outcome: ' + slot['case_id']
                break
        else:
            status['stop_reason'] = 'Fixed allocation exhausted; no further GPU work'
    except (Exception, KeyboardInterrupt) as exc:
        status['stop_reason'] = type(exc).__name__ + ': ' + str(exc)
        status['controller_exception'] = True
    finally:
        results = rows(ART / 'cases.jsonl')
        known = {r['case_id'] for r in results} | {r['case_id'] for r in status['skipped']}
        attempted = {e.get('case_id') for e in ledger.events() if e['event'] == 'reserve'}
        for slot in allocation['slots']:
            if slot['case_id'] not in known:
                status['skipped'].append({'case_id': slot['case_id'],
                                         'reason': 'abandoned attempt' if slot['case_id'] in attempted else status['stop_reason']})
        status['cumulative_usage'] = ledger.usage()
        status['incremental_usage'] = {k: status['cumulative_usage'][k] - allocation['baseline_usage'][k] for k in LIMITS}
        status['recorded_outcomes'] = len(results)
        status['both_fresh_128_failed'] = (len([r for r in results if r.get('payload_bytes') == 128]) == 2
                                         and not any(r['success'] for r in results if r.get('payload_bytes') == 128))
        write_new(ART / 'run_status.json', status)
        ledger.close()
        print(json.dumps(status), flush=True)


if __name__ == '__main__':
    run()
