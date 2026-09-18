#!/usr/bin/env python3
"""Retained-record reconciliation only; no backend import or model inference."""
from collections import Counter
import base64
import hashlib
import json
import math
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage3_transport'
def read(p): return json.loads(p.read_text())
def rows(p): return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(name,obj): (ART/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def first(a,b):
    for i in range(max(len(a),len(b))):
        left=a[i] if i<len(a) else None;right=b[i] if i<len(b) else None
        if left!=right: return {'position':i,'expected':left,'actual':right}
    return None

def main():
    a=read(ART/'allocation.json');status=read(ART/'run_status.json');anchor=read(ART/'budget_anchor.json')
    profile=read(ROOT/'configs/public_utf8_rank16_v1.json');slots={s['case_id']:s for s in a['slots']}
    raw=(ROOT/'artifacts/project_budget.jsonl').read_bytes()
    assert sha(raw[:anchor['bytes']])==anchor['sha256']
    assert raw[:anchor['bytes']]==subprocess.check_output(['git','show',a['starting_commit']+':artifacts/project_budget.jsonl'],cwd=ROOT)
    preserved=['artifacts/stage1','artifacts/stage1_review','artifacts/stage2_pilot','STAGE1_FOUNDATIONS_REPORT.md','STAGE1_REVIEW_REPORT.md','STAGE2_PILOT_REPORT.md','configs/public_profile.json','configs/local_runtime.json','src/llm_stego_public_key/codecs/calgacus.py','src/llm_stego_public_key/codecs/llama_backend.py','src/llm_stego_public_key/cryptography/hpke.py','scripts/gpu_worker.py']
    assert not subprocess.check_output(['git','diff',a['starting_commit'],'--',*preserved],cwd=ROOT)
    checkpoint=read(ROOT/'artifacts/project_budget.checkpoint.json')
    assert checkpoint['bytes']==len(raw) and checkpoint['sha256']==sha(raw)
    events=[json.loads(s) for s in raw[anchor['bytes']:].splitlines()]
    reserves={e['attempt_id']:e for e in events if e['event']=='reserve'}
    settled={e['attempt_id']:e for e in events if e['event'] in ('settle','overrun')}
    records=rows(ART/'cases.jsonl');history=rows(ROOT/'artifacts/stage1/cases.jsonl')
    by_id={r['attempt_id']:r for r in history+records}
    assert len({r['attempt_id'] for r in records})==len(records)
    assert len({r['case_id'] for r in records})==len(records)
    assert set(reserves)==set(settled)=={r['attempt_id'] for r in records}
    assert len({r['pid'] for r in records})==len(records)
    cumulative=dict(a['baseline_usage']);phase_checks=[];compact=[];scans=[];excluded=Counter()
    for r in records:
        aid=r['attempt_id'];slot=slots[r['case_id']];d=ROOT/r['evidence_dir']
        job=read(d/'input.json');claim=read(d/'worker_claim.json');command=read(d/'command.json')
        assert read(d/'outcome.json')==r
        assert r['tested_code_commit']==status['tested_code_commit']==job['tested_code_commit']
        assert r['profile_sha256']==a['profile_sha256']
        assert all(r[k] for k in ('gpu_verified','lease_verified','phase_meter_verified','provenance_verified'))
        assert r['exit_code']==0 and r['job_elapsed_seconds']<slot['reservation'][0]-8
        assert claim['pid']==r['pid'] and claim['attempt_id']==aid
        assert command['environment']['STAGE1_JOB_SHA256']==sha((d/'input.json').read_bytes())
        assert float(command['environment']['STAGE1_DEADLINE_MONOTONIC'])==claim['deadline_monotonic']
        reserved=dict(zip(('seconds','tokens'),slot['reservation']),cases=1)
        assert reserves[aid]['reserved']==reserved
        assert all(cumulative[k]+reserved[k]<=a['global_limits'][k] for k in cumulative)
        assert all(cumulative[k]-a['baseline_usage'][k]+reserved[k]<=a['additional_limits'][k] for k in cumulative)
        charge=settled[aid]['charged']
        assert charge['tokens']==r['charged_tokens']==sum(r['tokens_by_phase'].values()) and charge['cases']==1
        assert charge['seconds']==r['job_elapsed_seconds']
        for k in cumulative: cumulative[k]+=charge[k]
        assert all(math.isclose(cumulative[k],r['cumulative_budget'][k],abs_tol=1e-7) for k in cumulative)
        samples=read(d/'gpu_samples.json')
        assert samples and all(s['pid']==r['pid'] and s['gpu_uuid']==r['gpu_uuid'] for s in samples)
        assert 'offloaded 33/33 layers to GPU' in (d/'worker.log').read_text()
        assert max(s['used_vram_mib'] for s in samples)==r['peak_sampled_process_vram_mib']
        ctx=len(r['public_context_token_ids'][r['cover_context']])
        for phase,charged in r['tokens_by_phase'].items():
            if phase=='ordinary_control': count=ctx+len(r['control_ids'])
            else:
                trace=r['traces'][phase]
                count=ctx+len(trace['advanced_ids'])
                for step in trace['candidate_steps']:
                    assert step['examined']<=128 and step['eligible_found_capped_at_16']<=16
                # Availability aggregate counts encoder steps once, excluding repeat reconstruction.
                if phase=='encode':
                    scans.extend(trace['candidate_steps'])
                    for step in trace['candidate_steps']: excluded.update(step['rejected'])
            assert count==charged,(r['case_id'],phase,count,charged)
            phase_checks.append({'attempt_id':aid,'phase':phase,'tokens':count})
        carrier=ROOT/job['carrier_path'] if r['kind']=='replay' else d/'carrier.txt'
        if carrier.exists():
            wire=carrier.read_bytes();wire.decode('utf-8','strict');assert sha(wire)==r['transport_sha256']
        enc=r.get('traces',{}).get('encode',{})
        dec=r.get('traces',{}).get('fixture_decoder',r.get('traces',{}).get('receiver',{}))
        divergence={'tokenization':enc.get('first_transport_divergence'),
                    'candidate_order':first([s['ordered_ids_sha256'] for s in enc.get('candidate_steps',[])],
                                            [s['ordered_ids_sha256'] for s in dec.get('candidate_steps',[])]) if enc and dec else None}
        if r['kind'] in ('fixture','encrypted') and r['success']:
            assert enc['advanced_ids']==enc['retokenized_ids']==dec['received_ids']==dec['advanced_ids']
            assert enc['symbols']==dec['symbols'] and divergence['candidate_order'] is None
            frame=bytes(16*x+y for x,y in zip(dec['symbols'][::2],dec['symbols'][1::2]))
            assert int.from_bytes(frame[:4],'big')==len(frame)-4==r['envelope_bytes']
            assert sha(frame[4:])==r['envelope_sha256']
            assert r['carrier_tokens']==r['analytical_carrier_tokens']==2*(4+r['envelope_bytes'])
            if r['kind']=='fixture':
                source=by_id[r['fixture_source_attempt_id']]
                assert frame[4:]==base64.b64decode(source['serialized_base64'],validate=True)
                assert r['recovered_envelope_sha256']==source['envelope_sha256']
                assert not r['authenticated'] and not r['hpke_new_profile_binding']
            else:
                payload=bytes.fromhex(job['payload_hex']);assert job['payload_hex']==slot['payload_hex']
                assert sha(payload)==r['payload_sha256']==r['recovered_sha256']
                assert r['authenticated'] and r['hpke_new_profile_binding']
                assert r['observer']['envelope_sha256']==r['envelope_sha256'] and r['observer']['format_valid']
        if r['kind']=='replay':
            assert not set(job)&{'payload_hex','payload_sha256','expected_length','envelope_hex','source_attempt_id','encoder_trace','ranks','token_ids','cache'}
            source=by_id[r['source_attempt_id']]
            assert source['payload_bytes']==128 and source['pid']!=r['pid'] and r['transport_sha256']==source['transport_sha256']
            if r['success']: assert r['recovered_sha256']==source['payload_sha256'] and r['authenticated_message_recovery']
        if r.get('observer'): assert r['observer']['authenticated'] is False
        if r['kind']=='control':
            source=by_id[job['matched_attempt_id']]
            assert source['payload_bytes']==128 and source['cover_context']==r['cover_context']
            assert len(r['control_ids'])==job['target_tokens']==source['carrier_tokens']
        compact.append({'attempt_id':aid,'case_id':r['case_id'],'family':slot['family'],'success':r['success'],
                        'failure_category':r['failure_category'],'error':r.get('error'),'first_divergences':divergence,
                        'capacity_failure_step':next((s for s in enc.get('candidate_steps',[]) if s['eligible_found_capped_at_16']<16),None),
                        'invalid_choice':next((t['invalid_choice'] for t in r.get('traces',{}).values() if 'invalid_choice' in t),None),
                        'public_rejection':r.get('observer',{}).get('failure_category'),
                        'public_rejection_error':r.get('observer',{}).get('error'),
                        'public_declared_envelope_bytes':r.get('traces',{}).get('public_extraction',{}).get('declared_envelope_bytes'),
                        'raw_result':str((d/'result.json').relative_to(ROOT))})
    increment={k:cumulative[k]-a['baseline_usage'][k] for k in cumulative}
    assert all(math.isclose(cumulative[k],status['cumulative_usage'][k],abs_tol=1e-7) for k in cumulative)
    assert all(math.isclose(increment[k],status['incremental_usage'][k],abs_tol=1e-7) and increment[k]<=a['additional_limits'][k] for k in cumulative)
    fresh=[r for r in records if r['kind']=='encrypted'];fixtures=[r for r in records if r['kind']=='fixture']
    replays=[r for r in records if r['kind']=='replay'];controls=[r for r in records if r['kind']=='control']
    if len(fresh)==4:
        assert len({r['receiver_public_key_hex'] for r in fresh})==2
        assert len({base64.b64decode(r['serialized_base64'])[:32] for r in fresh})==4
        old_keys={r.get('receiver_public_key_hex') for r in history+rows(ROOT/'artifacts/stage2_pilot/cases.jsonl')}
        assert not {r['receiver_public_key_hex'] for r in fresh}&old_keys
    measured=[]
    for r in records:
        if r['kind'] not in ('fixture','encrypted'): continue
        slot=slots[r['case_id']]
        measured.append({'attempt_id':r['attempt_id'],'case_id':r['case_id'],'carrier_tokens':r.get('carrier_tokens'),
                         'carrier_utf8_bytes':r.get('transport_bytes'),'envelope_bytes':r.get('envelope_bytes'),
                         'net_payload_bits_per_token':r.get('net_payload_bits_per_token'),
                         'historical_intended_carrier_tokens':slot.get('historical_carrier_tokens'),
                         'token_expansion_vs_historical_fixture':r['carrier_tokens']/slot['historical_carrier_tokens'] if r.get('carrier_tokens') and 'historical_carrier_tokens' in slot else None,
                         'job_elapsed_seconds':r['job_elapsed_seconds'],'timings':r.get('timings',{})})
    summary={'schema_version':1,'starting_commit':a['starting_commit'],'gpu_tested_code_commit':status['tested_code_commit'],
             'profile_id':'public_utf8_rank16_v1','profile_sha256':a['profile_sha256'],
             'split':'development_only_excluded_from_future_heldout','planned_cases':10,'attempted_cases':len(reserves),
             'recorded_outcomes':len(records),'unused_slots':status['skipped'],
             'fixtures':{'attempted':len(fixtures),'exact_envelope_recovery':sum(r.get('envelope_exact_recovery',False) for r in fixtures),'new_profile_hpke_binding_claimed':False},
             'fresh_recovery':{str(n):{'attempted':sum(r.get('payload_bytes')==n for r in fresh),
                 'authenticated_exact':sum(r.get('payload_bytes')==n and r['authenticated_message_recovery'] for r in fresh)} for n in (32,128)},
             'fresh_recipient_key_pairs':len({r['receiver_public_key_hex'] for r in fresh if 'receiver_public_key_hex' in r}),
             'fresh_128_replays':{'attempted':len(replays),'authenticated_exact':sum(r['authenticated_message_recovery'] for r in replays)},
             'ordinary_controls':{'attempted':len(controls),'generated_utf8':sum(r['success'] for r in controls)},
             'public_format_diagnostics':[{'attempt_id':r['attempt_id'],'case_id':r['case_id'],'kind':r['kind'],**r['observer']} for r in records if 'observer' in r],
             'primary_failures':dict(Counter(r['failure_category'] for r in records if r['failure_category'])),
             'candidate_availability':{'aggregation':'encoder steps only; stop scan at 16 eligible; not total support in top128',
                 'steps':len(scans),'min_eligible_capped_at16':min((s['eligible_found_capped_at_16'] for s in scans),default=None),
                 'mean_examined':sum(s['examined'] for s in scans)/len(scans) if scans else None,
                 'max_examined':max((s['examined'] for s in scans),default=None),'rejected':dict(excluded)},
             'measurements':measured,'incremental_usage':increment,'cumulative_usage':cumulative,
             'peak_sampled_process_vram_mib':max((r['peak_sampled_process_vram_mib'] for r in records),default=None),
             'stop_reason':status['stop_reason'],'focused_codec_tests':7,'focused_allocation_checks':5,'new_full_cpu_suite_run':False,
             'engineering_verdict':'bounded_qualification_passed' if len(records)==10 and all(r['success'] for r in records) else 'qualification_incomplete_or_failed',
             'novelty_and_keyed_comparators':'unresolved; not assessed or executed'}
    save('summary.json',summary)
    save('compact_traces.json',{'schema_version':1,'records':compact})
    save('reconciliation.json',{'schema_version':1,'status':'PASS','no_model_inference':True,'checked_attempts':len(records),
         'historical_ledger_prefix_preserved':True,'prefix_sha256':anchor['sha256'],'prefix_bytes':anchor['bytes'],
         'historical_codecs_profiles_reports_and_artifacts_unchanged':True,'phase_charges_reconstructed':phase_checks,
         'reservations_settlements_outcomes_agree':True,'both_ceilings_enforced':True,
         'lease_hashes_and_unique_pids_verified':True,'pid_matched_gpu_samples_and_full_offload_verified':True})
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
