#!/usr/bin/env python3
"""Read-only reconciliation of retained pilot records; no model loading or inference.

Writes only derived reconciliation/summary/trace outputs, never original attempts.
Run from any directory with the existing Python. This is an evidence check, not a CPU test suite.
"""
import base64
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts/stage2_pilot'

def read(path): return json.loads(path.read_text())
def lines(path): return [json.loads(s) for s in path.read_text().splitlines()]
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(name, value): (ART / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def same(a, b): return all(math.isclose(a[k], b[k], abs_tol=1e-7) for k in a)
def first(a, b):
    for i in range(max(len(a), len(b))):
        left = a[i] if i < len(a) else None
        right = b[i] if i < len(b) else None
        if left != right: return {'index': i, 'intended': left, 'observed': right}
    return None


def main():
    allocation, status, migration = [read(ART / n) for n in ('allocation.json','run_status.json','migration.json')]
    profile = read(ROOT / 'configs/public_profile.json')
    history = (ROOT / migration['source']).read_bytes()
    raw = (ROOT / migration['destination']).read_bytes()
    assert raw[:len(history)] == history and len(history) == migration['bytes']
    assert sha(history) == migration['sha256']
    preserved = ['artifacts/stage1', 'artifacts/stage1_review', 'STAGE1_FOUNDATIONS_REPORT.md',
                 'STAGE1_REVIEW_REPORT.md', 'configs', 'manifests', 'src']
    assert not subprocess.check_output(['git','diff',allocation['starting_commit'],'--',*preserved],cwd=ROOT)
    checkpoint = read(ROOT / 'artifacts/project_budget.checkpoint.json')
    assert checkpoint['bytes'] == len(raw) and checkpoint['sha256'] == sha(raw)
    events = lines(ROOT / migration['destination'])
    old_events = lines(ROOT / migration['source'])
    new_events = events[len(old_events):]
    reservations = {e['attempt_id']:e for e in new_events if e['event']=='reserve'}
    settlements = {e['attempt_id']:e for e in new_events if e['event'] in ('settle','overrun')}
    records = lines(ART / 'cases.jsonl')
    assert len({r['attempt_id'] for r in records}) == len(records)
    assert set(reservations) == set(settlements) == {r['attempt_id'] for r in records}
    by_id = {r['attempt_id']:r for r in lines(ROOT/'artifacts/stage1/cases.jsonl') + records}
    slots = {s['case_id']:s for s in allocation['slots']}
    assert len({r['case_id'] for r in records}) == len(records)
    assert len({r['pid'] for r in records}) == len(records)
    cumulative = dict(allocation['baseline_usage'])
    traces, checked_phases, formats = [], [], []
    for r in records:
        aid = r['attempt_id']; directory = ROOT / r['evidence_dir']; slot = slots[r['case_id']]
        job, claim, command = [read(directory/n) for n in ('input.json','worker_claim.json','command.json')]
        assert r == read(directory/'outcome.json')
        assert r['tested_code_commit'] == status['tested_code_commit'] == job['tested_code_commit']
        assert r['profile_sha256'] == allocation['profile_sha256']
        assert all(r[n] for n in ('gpu_verified','lease_verified','phase_meter_verified','provenance_verified'))
        assert r['exit_code'] == 0
        assert r['job_elapsed_seconds'] < slot['reservation'][0] - 8
        assert r['pid'] == claim['pid'] and claim['attempt_id'] == aid
        assert claim['deadline_monotonic'] == float(command['environment']['STAGE1_DEADLINE_MONOTONIC'])
        assert command['environment']['STAGE1_JOB_SHA256'] == sha((directory/'input.json').read_bytes())
        requested = dict(zip(('seconds','tokens'),slot['reservation']),cases=1)
        assert reservations[aid]['reserved'] == requested
        assert all(cumulative[k]+requested[k] <= allocation['global_limits'][k] for k in cumulative)
        assert all(cumulative[k]-allocation['baseline_usage'][k]+requested[k] <= allocation['pilot_limits'][k] for k in cumulative)
        charged = settlements[aid]['charged']
        assert charged['tokens'] == r['charged_tokens'] == sum(r['tokens_by_phase'].values())
        assert math.isclose(charged['seconds'],r['job_elapsed_seconds']) and charged['cases']==1
        for k in cumulative: cumulative[k] += charged[k]
        assert same(cumulative,r['cumulative_budget'])
        samples=read(directory/'gpu_samples.json')
        assert samples and all(s['pid']==r['pid'] and s['gpu_uuid']==r['gpu_uuid'] for s in samples)
        assert 'offloaded 33/33 layers to GPU' in (directory/'worker.log').read_text()
        assert max(s['used_vram_mib'] for s in samples) == r['peak_sampled_process_vram_mib']
        contexts=r['public_context_token_ids']
        base=len(contexts[r['cover_context']])+len(contexts[profile['source_context']])
        trace=r.get('encoder_trace',{})
        expected={}
        if 'encode' in r['tokens_by_phase']: expected['encode']=base+2*len(trace['source_ids'])
        for phase,key in [('receiver','receiver_trace'),('fresh_receiver','receiver_trace'),('public_inversion','observer_trace')]:
            if phase in r['tokens_by_phase']: expected[phase]=base+2*len(r[key]['received_ids'])
        if 'ordinary_control' in r['tokens_by_phase']:
            expected['ordinary_control']=len(contexts[r['cover_context']])+len(r['control_ids'])
        for phase,count in expected.items():
            assert count==r['tokens_by_phase'][phase]
            checked_phases.append({'attempt_id':aid,'phase':phase,'tokens':count})
        carrier=ROOT/job['carrier_path'] if r['kind']=='replay' else directory/'carrier.txt'
        if carrier.exists():
            wire=carrier.read_bytes(); wire.decode('utf-8','strict')
            assert sha(wire)==r['transport_sha256']
        if r['kind']=='replay':
            assert not set(job)&{'payload_hex','expected_payload','payload_sha256','expected_payload_hash','source_attempt_id','encoder_trace','source_ranks','source_ids','carrier_ids','cache'}
            source=by_id[r['source_attempt_id']]
            assert r['pid']!=source['pid'] and r['transport_sha256']==source['transport_sha256']
            if r['authenticated']:
                assert r['recovered_sha256']==source['payload_sha256'] and r['exact_recovery']
            original=source.get('encoder_trace',{})
            decoder=r['receiver_trace']
            divergence={'transport':first(original.get('carrier_ids',[]),decoder.get('received_ids',[])),
                        'ranks':first(original.get('source_ranks',[]),decoder.get('received_ranks',[])),
                        'reconstruction':first(original.get('source_ids',[]),decoder.get('reconstructed_ids',[]))}
        else:
            divergence={'transport':trace.get('first_transport_divergence'),
                        'ranks':r.get('first_rank_divergence'),
                        'reconstruction':r.get('first_reconstruction_divergence')}
        if r['kind']=='encrypted':
            payload=bytes.fromhex(job['payload_hex'])
            assert job['payload_hex']==slot['payload_hex'] and sha(payload)==r['payload_sha256']
            assert len(payload)==r['payload_bytes']
            envelope=base64.b64decode(r['serialized_base64'],validate=True)
            assert sha(envelope)==r['envelope_sha256'] and len(envelope)==r['envelope_bytes']
            assert len(envelope)==68+len(payload)
            if r['authenticated']:
                assert r['recovered_sha256']==r['payload_sha256']
                assert r['text_retokenizes'] and trace['carrier_ids']==trace['retokenized_ids']
                assert trace['source_ids']==r['receiver_trace']['reconstructed_ids']
                assert trace['source_ranks']==r['receiver_trace']['received_ranks']
        observer=r.get('observer')
        if observer:
            assert observer['authenticated'] is False
            if 'extracted_text' in observer:
                text=observer['extracted_text']; valid=False
                try:
                    decoded=base64.b64decode(text.encode('ascii'),validate=True)
                    valid=92<=len(text)<=264 and len(text)%4==0 and 68<=len(decoded)<=196 and base64.b64encode(decoded).decode()==text
                except (ValueError,UnicodeError): pass
                assert valid==observer['format_valid']
            formats.append({'attempt_id':aid,'case_id':r['case_id'],'family':slot['family'],
                            'format_valid':observer['format_valid'],'tag_authentication_performed':False})
        traces.append({'attempt_id':aid,'case_id':r['case_id'],'family':slot['family'],
                       'first_divergences':divergence,'primary_failure':r['failure_category'],
                       'downstream_error':r.get('receiver_error',r.get('error')),
                       'invalid_utf8':bool(trace.get('carrier_bytes_hex')) and 'first_transport_divergence' not in trace,
                       'retokenization_drift':divergence['transport'] is not None,
                       'raw_trace_path':str((directory/'result.json').relative_to(ROOT))})
    incremental={k:cumulative[k]-allocation['baseline_usage'][k] for k in cumulative}
    assert same(cumulative,status['cumulative_usage']) and same(incremental,status['incremental_usage'])
    assert all(incremental[k]<=allocation['pilot_limits'][k] for k in cumulative)
    fresh=[r for r in records if r['kind']=='encrypted']
    historical=[r for r in records if slots[r['case_id']]['family']=='historical_replay']
    replay=[r for r in records if slots[r['case_id']]['family']=='fresh_replay']
    controls=[r for r in records if r['kind']=='control']
    key_ids={r.get('receiver_public_key_hex') for r in fresh}
    assert len(key_ids)==2
    keys=read(ART/'TEST_ONLY_keys.json')['keys']
    assert key_ids=={k['public_key_hex'] for k in keys}
    assert len({k['TEST_ONLY_private_key_hex'] for k in keys})==2
    old_keys=read(ROOT/'artifacts/stage1/TEST_ONLY_keys.json')['keys']
    assert not key_ids & {k['public_key_hex'] for k in old_keys}
    assert len({r['serialized_base64'][:40] for r in fresh})==len(fresh)
    summary={'schema_version':1,'starting_commit':allocation['starting_commit'],
             'gpu_tested_code_commit':status['tested_code_commit'],
             'split':'development_only_excluded_from_future_heldout',
             'planned_cases':len(slots),'attempted_cases':len(reservations),'outcomes':len(records),
             'unused_slots':status['skipped'],'historical_replays':{'attempted':len(historical),
             'expected_outcome_agreement':sum(r['expected_outcome_agreement'] for r in historical),
             'authenticated_exact_recovery':sum(r['authenticated_message_recovery'] for r in historical),
             'expected_rejections':sum(r['expected_rejection'] and r['expected_outcome_agreement'] for r in historical)},
             'fresh_recovery':{str(n):{'attempted':sum(r['payload_bytes']==n for r in fresh),
             'authenticated_exact':sum(r['payload_bytes']==n and r['authenticated_message_recovery'] for r in fresh)} for n in (32,128)},
             'fresh_key_pairs':len(key_ids),'controls':{'attempted':len(controls),'generated_utf8':sum(r['success'] for r in controls)},
             'fresh_process_replays':{'attempted':len(replay),'authenticated_exact':sum(r['authenticated_message_recovery'] for r in replay)},
             'public_diagnostics':formats,'incremental_usage':incremental,'cumulative_usage':cumulative,
             'peak_sampled_process_vram_mib':max(r['peak_sampled_process_vram_mib'] for r in records),
             'stop_reason':status['stop_reason'],'both_fresh_128_failed':status['both_fresh_128_failed'],
             'cpu_validation':{'new_full_suite_run':False,'historical_tests_reused':109,'historical_code_commit':'7f60caf86f7430a19105aa5641f1003336d154b6',
             'new_allocation_check':'5 focused checks only; not a suite rerun'},
             'novelty':'unresolved, not reassessed','comparators':'unresolved, not executed'}
    save('compact_traces.json',{'schema_version':1,'records':traces})
    save('summary.json',summary)
    save('reconciliation.json',{'schema_version':1,'status':'PASS','original_artifacts_and_core_source_unchanged':True,
         'historical_ledger_prefix_bytes':len(history),'historical_ledger_prefix_sha256':sha(history),
         'checked_attempts':len(records),'independently_reconciled_phases':checked_phases,
         'reservations_settlements_outcomes_agree':True,'input_lease_hashes_match':True,
         'pid_matched_gpu_and_full_offload':True,'both_budget_ceilings_respected':True,
         'summary_regenerated_from_retained_records':True,'no_inference':True})
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
