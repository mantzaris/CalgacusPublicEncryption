#!/usr/bin/env python3
"""Host-only analysis of frozen Stage 6 records. Never imports a model/backend.

Run only after the governed controller stops. Analysis implementation is evidence
processing, separate from the GPU-tested transport/observer revision.
"""
import collections
import base64
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'artifacts/stage6'
METRICS=['prefix_match','format_accepted','format_and_kem_canonical','member_fraction',
         'mean_nll_bits','mean_log2_rank','after_eight_nll_bits','encrypted_body_nll_bits',
         'encrypted_body_log2_rank','token_count','utf8_bytes']


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
def avg(x):return statistics.mean(x) if x else None

def quantile(v,q):
    a=sorted(v)
    if not a:return None
    k=(len(a)-1)*q;i=int(k)
    return a[i] if i==len(a)-1 else a[i]+(a[i+1]-a[i])*(k-i)

def interval(x):return [quantile(x,.025),quantile(x,.975)]

def auc(x,y):
    if not x or not y:return None
    return sum(1 if a>b else .5 if a==b else 0 for a in x for b in y)/(len(x)*len(y))

def value(record,metric):
    o=record.get('observer',{})
    if metric=='prefix_match':return int(o.get('prefix',{}).get('prefix_match',False))
    v=o.get(metric)
    return float(v) if v is not None else None

def write_csv(name,data,fields=None):
    if not data:return
    fields=fields or list(data[0])
    with (ART/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(data)

def fmt(x):return 'NA' if x is None else (f'{x:.4f}' if isinstance(x,float) else str(x))

def main():
    status=read(ART/'run_status.json') # never analyze an in-flight append as a final result
    allocation=read(ART/'allocation.json');auth=read(ROOT/'configs/stage6/authorization.json')
    records=[json.loads(l) for l in (ART/'cases.jsonl').read_text().splitlines()]
    slots={s['case_id']:s for s in allocation['slots']};byid={r['case_id']:r for r in records}
    raw=(ROOT/'artifacts/project_budget.jsonl').read_bytes();anchor=auth['previous_checkpoint']
    assert hashlib.sha256(raw[:anchor['bytes']]).hexdigest()==anchor['sha256']
    checkpoint=read(ROOT/'artifacts/project_budget.checkpoint.json')
    assert checkpoint['bytes']==len(raw) and checkpoint['sha256']==hashlib.sha256(raw).hexdigest()
    events=[json.loads(l) for l in raw.splitlines()];jobs={};reserve={};settled=set()
    for e in events:
        if e['event']=='reserve':
            assert e['attempt_id'] not in jobs; jobs[e['attempt_id']]=e['reserved'];reserve[e['attempt_id']]=e
        else:
            assert e['attempt_id'] in jobs and e['attempt_id'] not in settled
            jobs[e['attempt_id']]=e['charged'];settled.add(e['attempt_id'])
    lifetime={k:sum(j[k] for j in jobs.values()) for k in ['seconds','tokens','cases']}
    incremental={k:lifetime[k]-auth['baseline_usage'][k] for k in lifetime}
    assert all(incremental[k]<=auth['additional_limits'][k] for k in incremental)
    assert lifetime==status['lifetime_usage']
    new_attempts=[a for a,e in reserve.items() if e.get('allocation_id')==auth['allocation_id']]
    assert len(records)==len({r['attempt_id'] for r in records})
    assert set(new_attempts)=={r['attempt_id'] for r in records},'Missing attempted outcomes must be reported before reconciliation'
    pid_evidence=[]; manifests=[]
    for r in records:
        d=ROOT/r['evidence_dir'];job=read(d/'input.json');command=read(d/'command.json');claim=read(d/'worker_claim.json')
        assert r['tested_code_commit']==job['tested_code_commit']
        assert r['profile_sha256']==slots[r['case_id']]['profile_sha256']
        assert math.isclose(r['charged_tokens'],jobs[r['attempt_id']]['tokens'])
        assert r['charged_tokens']==sum(r.get('tokens_by_phase',{}).values())
        assert claim['pid']==r['pid'] and claim['attempt_id']==r['attempt_id']
        assert hashlib.sha256((d/'input.json').read_bytes()).hexdigest()==command['environment']['STAGE1_JOB_SHA256']
        samples=read(d/'gpu_samples.json');assert samples
        assert all(s['pid']==r['pid'] and s['gpu_uuid']==r['gpu_uuid'] for s in samples)
        assert 'offloaded 33/33 layers to GPU' in (d/'worker.log').read_text()
        for name in ['carrier.txt','carrier.invalid.bin']:
            if (d/name).exists() and r.get('transport_sha256'):assert sha(d/name)==r['transport_sha256']
        if r['kind']=='encrypted':
            payload=bytes.fromhex(job['payload_hex'])
            assert len(payload)==r['payload_bytes'] and hashlib.sha256(payload).hexdigest()==r['payload_sha256']
            envelope=base64.b64decode(r['serialized_base64'],validate=True)
            assert base64.b64encode(envelope).decode('ascii')==r['serialized_base64']
            assert len(envelope)==r['envelope_bytes']==68+len(payload)
            assert hashlib.sha256(envelope).hexdigest()==r['envelope_sha256']
            assert hashlib.sha256(envelope[32:]).hexdigest()==r['ciphertext_sha256']
            assert envelope[:32].hex()==r['encapsulation_hex']
            if r.get('authenticated_message_recovery'):assert r['recovered_sha256']==r['payload_sha256']
        traces=read(d/'traces.json')
        if r.get('observer',{}).get('scorable'):
            o=r['observer'];t=traces['public_scoring']
            assert len(t['received_ids'])==o['token_count']==len(t['ranks'])==len(t['nll_bits'])==len(t['symbols'])
            assert math.isclose(statistics.mean(t['nll_bits']),o['mean_nll_bits'],rel_tol=1e-12)
            assert math.isclose(statistics.mean(math.log2(x) for x in t['ranks']),o['mean_log2_rank'],rel_tol=1e-12)
            assert math.isclose(sum(x is not None for x in t['symbols'])/len(t['symbols']),o['member_fraction'])
            if r['method'] in ['L','F'] and o['format_accepted']:
                raw_frame=bytes((a<<4)|b for a,b in zip(t['symbols'][::2],t['symbols'][1::2]))
                env=raw_frame[4:] if r['method']=='L' else raw_frame
                if r['method']=='L':assert int.from_bytes(raw_frame[:4],'big')==len(env)
                assert 68<=len(env)<=196 and hashlib.sha256(env).hexdigest()==o['envelope_sha256']
                assert (int.from_bytes(env[:32],'little')<2**255-19)==o['kem_canonical']
                if r['kind']=='encrypted':assert o['envelope_sha256']==r['envelope_sha256']
        if r['kind']=='replay':
            source=byid[slots[r['case_id']]['source_case_id']]
            assert r.get('recovered_sha256')==source['payload_sha256'] or not r.get('authenticated_message_recovery')
            assert not any(k in job for k in ['payload_hex','payload_sha256','payload_bytes','target_tokens','encoder_trace','expected_length'])
        pid_evidence.append({'case_id':r['case_id'],'pid':r['pid'],'gpu_uuid':r['gpu_uuid'],
                             'peak_sampled_vram_mib':r['peak_sampled_process_vram_mib'],'phase_meter_verified':r['phase_meter_verified']})
        manifests.append({'case_id':r['case_id'],'attempt_id':r['attempt_id'],'tested_code_commit':r['tested_code_commit'],
            'profile_sha256':r['profile_sha256'],'files':{str(p.relative_to(ROOT)):sha(p) for p in d.iterdir() if p.is_file()}})
    main_rows=[r for r in records if r['stage6_phase']=='main_fixed' and r['kind']=='encrypted']
    controls=[r for r in records if r['kind']=='control']
    baseline=[r for r in records if r['stage6_phase']=='baseline']
    qualification=[r for r in records if r['stage6_phase']=='qualification']
    replay=[r for r in records if r['kind']=='replay']
    # Freeze one set of hierarchical draws; preserve all related records within blocks.
    rng=random.Random(2026091866)
    draws=[]
    for _ in range(2000):
        groups=[]
        for c in rng.choices(list(range(4)),k=4):
            for rep in rng.choices([0,1],k=2):groups.append((c,rep))
        draws.append(groups)
    recovery=[]
    for method in ['L','F','Calgacus']:
        for size in [32,128]:
            rr=[r for r in main_rows+baseline if r['method']==method and r.get('payload_bytes')==size]
            planned=sum(s['kind']=='encrypted' and s['stage6_phase'] in ['main_fixed','baseline'] and s['method']==method and s['payload_bytes']==size for s in slots.values())
            success=[r for r in rr if r.get('authenticated_message_recovery')]
            def use(r):return r.get('attempt_useful_bits_per_transmitted_token',0.)
            groups=collections.defaultdict(list)
            for r in rr:groups[(r['context_index'],slots[r['case_id']].get('repetition',0))].append(r)
            boot=[];bootrate=[]
            if method!='Calgacus':
                for draw in draws:
                    sampled=[r for g in draw for r in groups[g]]
                    if sampled:
                        boot.append(avg([use(r) for r in sampled]));bootrate.append(sum(r.get('authenticated_message_recovery',False) for r in sampled)/len(sampled))
            delivered_tokens=sum(r.get('carrier_tokens',0) for r in rr if r['wire_delivered'])
            recovery.append({'method':method,'payload_bytes':size,'planned':planned,'attempted':len(rr),'delivered':sum(r['wire_delivered'] for r in rr),
                'authenticated_exact':len(success),'recovery_fraction':len(success)/len(rr) if rr else None,
                'recovery_cluster_interval':interval(bootrate),'mean_success_payload_bits_per_token':avg([r['successful_payload_bits_per_token'] for r in success]),
                'mean_attempt_useful_bits_per_transmitted_token':avg([use(r) for r in rr]),'attempt_rate_cluster_interval':interval(boot),
                'aggregate_recovered_bits_per_delivered_token':8*size*len(success)/delivered_tokens if delivered_tokens else None,
                'recovered_bytes_per_charged_second':size*len(success)/sum(r['job_elapsed_seconds'] for r in rr) if rr else None})
    recognition=[];outcomes=[];paired_deltas=[]
    for method in ['L','F']:
        positives=[r for r in main_rows if r['method']==method]
        for family in 'ABC':
            negatives=[r for r in controls if r['method']==method and r['family']==family]
            for role,rr in [('encrypted',positives),('control',negatives)]:
                outcomes.append({'method':method,'family':family,'role':role,'attempted':len(rr),'delivered':sum(r['wire_delivered'] for r in rr),
                    'scorable':sum(r.get('observer',{}).get('scorable',False) for r in rr),
                    'prefix_matches':sum(r.get('observer',{}).get('prefix',{}).get('prefix_match',False) for r in rr),
                    'format_accepted':sum(r.get('observer',{}).get('format_accepted',False) for r in rr),
                    'format_and_kem_canonical':sum(r.get('observer',{}).get('format_and_kem_canonical',False) for r in rr),
                    'all_candidates_member':sum(r.get('observer',{}).get('all_candidates_member',False) for r in rr),
                    'invalid_utf8':sum(r.get('serialization_status')=='invalid_utf8' for r in rr),
                    'retokenization_drift':sum(r.get('serialization_status')=='retokenization_drift' for r in rr),
                    'candidate_exhaustion':sum(r.get('failure_category')=='capacity_exhaustion' for r in rr),
                    'observer_candidate_unavailable_messages':sum(bool(r.get('observer',{}).get('candidate_unavailable_positions')) for r in rr),
                    'observer_candidate_unavailable_positions':sum(len(r.get('observer',{}).get('candidate_unavailable_positions',[])) for r in rr)})
            for metric in METRICS:
                pairs=[]
                for p in positives:
                    n=byid.get(f"control-{p['case_id']}-{family}")
                    if n and p.get('observer',{}).get('scorable') and n.get('observer',{}).get('scorable') and value(p,metric) is not None and value(n,metric) is not None:
                        pairs.append((p,n))
                groups=collections.defaultdict(list)
                for p,n in pairs:groups[(p['context_index'],slots[p['case_id']]['repetition'])].append((value(p,metric),value(n,metric)))
                boots=[]
                for draw in draws:
                    pp=[pair for g in draw for pair in groups[g]]
                    if pp:boots.append(auc([x for x,y in pp],[y for x,y in pp]))
                xs=[value(p,metric) for p,n in pairs];ys=[value(n,metric) for p,n in pairs]
                recognition.append({'method':method,'family':family,'metric':metric,'matched_scorable_pairs':len(pairs),
                    'encrypted_mean':avg(xs),'control_mean':avg(ys),'encrypted_median':statistics.median(xs) if xs else None,'control_median':statistics.median(ys) if ys else None,
                    'auc_higher_is_stego':auc(xs,ys),'auc_cluster_interval':interval(boots),
                    'context_auc':{str(c):auc([value(p,metric) for p,n in pairs if p['context_index']==c],[value(n,metric) for p,n in pairs if p['context_index']==c]) for c in range(4)},
                    'bootstrap_values':boots})
    for family in 'ABC':
        for metric in METRICS:
            l=next(x for x in recognition if x['method']=='L' and x['family']==family and x['metric']==metric)
            f=next(x for x in recognition if x['method']=='F' and x['family']==family and x['metric']==metric)
            # Same frozen group draws; only compare identical complete support.
            comparable=l['matched_scorable_pairs']==f['matched_scorable_pairs']==16
            diffs=[a-b for a,b in zip(f['bootstrap_values'],l['bootstrap_values'])] if comparable else []
            paired_deltas.append({'family':family,'metric':metric,'F_minus_L_auc':f['auc_higher_is_stego']-l['auc_higher_is_stego'] if comparable else None,
                                  'paired_cluster_interval':interval(diffs),'complete_support':comparable})
    for r in recognition:r.pop('bootstrap_values')
    costs=[]
    def kind_group(r):return (r['stage6_phase'],r['kind'],r['method'],r.get('family') or '-',r.get('payload_bytes',slots[r['case_id']].get('payload_setting_bytes')))
    groups=collections.defaultdict(list)
    for r in records:groups[kind_group(r)].append(r)
    for group,rr in groups.items():
        costs.append(dict(zip(['stage6_phase','kind','method','family','payload_setting_bytes'],group),
            attempts=len(rr),charged_seconds=sum(r['job_elapsed_seconds'] for r in rr),evaluated_tokens=sum(r['charged_tokens'] for r in rr),
            median_job_seconds=statistics.median(r['job_elapsed_seconds'] for r in rr),max_job_seconds=max(r['job_elapsed_seconds'] for r in rr),
            peak_sampled_vram_mib=max(r['peak_sampled_process_vram_mib'] for r in rr),
            mean_load_and_verify_seconds=avg([r['timings']['load_and_verify_seconds'] for r in rr if 'load_and_verify_seconds' in r['timings']]),
            mean_control_generation_seconds=avg([r['timings']['control_generation_seconds'] for r in rr if 'control_generation_seconds' in r['timings']]),
            mean_encode_seconds=avg([r['timings']['encode_seconds'] for r in rr if 'encode_seconds' in r['timings']]),
            mean_receiver_seconds=avg([r['timings']['receiver_seconds'] for r in rr if 'receiver_seconds' in r['timings']]),
            mean_public_scoring_seconds=avg([r['timings']['public_scoring_seconds'] for r in rr if 'public_scoring_seconds' in r['timings']])))
    failures=[{'case_id':r['case_id'],'attempt_id':r['attempt_id'],'method':r['method'],'kind':r['kind'],
               'failure_category':r['failure_category'],'serialization_status':r.get('serialization_status'),
               'first_transport_divergence':r.get('first_transport_divergence'),'first_rank_divergence':r.get('first_rank_divergence'),
               'error':r.get('error',r.get('receiver_error'))} for r in records if r.get('failure_category') or r.get('serialization_status')=='retokenization_drift']
    phase_tokens=collections.Counter();phase_seconds=collections.Counter();candidates=collections.Counter()
    for r in records:
        phase_tokens.update(r['tokens_by_phase']);phase_seconds.update(r['timings'])
        for cost in r.get('candidate_costs',{}).values():
            candidates.update({k:cost[k] for k in ['steps','examined_total']});candidates.update(cost['rejected'])
    summary={'schema_version':1,'starting_commit':auth['starting_commit'],'gpu_tested_code_commits':sorted({r['tested_code_commit'] for r in records}),
        'planned_slots':150,'attempted_cases':len(records),'qualification':{'attempted':len(qualification),'completed':sum(r['success'] for r in qualification)},
        'main_encrypted_attempts':len(main_rows),
        'independent_main_recipient_public_keys':len({r['receiver_public_key_hex'] for r in main_rows}),
        'distinct_encrypted_envelope_hashes':len({r['envelope_sha256'] for r in records if r['kind']=='encrypted' and r.get('envelope_sha256')}),
        'payload_and_envelope_hashes_reconciled':True,'control_attempts':len(controls),'baseline_attempts':len(baseline),
        'fresh_process_replays':{'attempted':len(replay),'authenticated_exact':sum(r.get('authenticated_message_recovery',False) for r in replay),
            'cases':[{'case_id':r['case_id'],'source_case_id':slots[r['case_id']]['source_case_id'],'exact':r.get('authenticated_message_recovery',False)} for r in replay]},
        'recovery':recovery,'recognition_outcomes':outcomes,'recognition_auc':recognition,'paired_auc_differences':paired_deltas,
        'costs':costs,'failures':failures,'candidate_costs':dict(candidates),
        'candidate_search':{'mean_examined_per_step':candidates['examined_total']/candidates['steps'] if candidates['steps'] else None,
            'max_examined_on_any_step':max((cost['examined_max'] or 0 for r in records for cost in r.get('candidate_costs',{}).values()),default=0),
            'public_scoring_unavailable_positions':sum(len(r.get('observer',{}).get('candidate_unavailable_positions',[])) for r in records)},
        'phase_evaluated_tokens':dict(phase_tokens),'phase_seconds':dict(phase_seconds),
        'stage6_usage':incremental,'lifetime_usage':lifetime,'stage6_unused_allowance':{k:auth['additional_limits'][k]-incremental[k] for k in incremental},
        'selected_gpu':read(ART/'environment.json')['selected_gpu'],'peak_sampled_vram_mib':max(r['peak_sampled_process_vram_mib'] for r in records),
        'historical_prefix_preserved':True,'ledger_sha256':hashlib.sha256(raw).hexdigest(),'ledger_bytes':len(raw),
        'all_gpu_lease_phase_provenance_verified':all(all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified']) for r in records),
        'all_workers_clean_exit':all(r['exit_code']==0 for r in records),'unique_worker_pids':len({r['pid'] for r in records}),
        'unsettled_attempt_ids':sorted(set(jobs)-settled),'skipped':status['skipped'],'stop_reason':status['stop_reason'],
        'analysis':{'hierarchical_bootstrap_draws':2000,'seed':2026091866,'unit':'context, then repetition/key block; lengths/variants/controls retained jointly',
            'auc_population':'matched pairs with both delivered outputs scorable, independent of authentication success',
            'limits':'only four selected contexts; conditional/descriptive intervals, possibly degenerate; no operational false-positive or general concealment estimate'},
        'historical_data_pooled':False,'full_cpu_suite_run':False,'new_focused_tests':11}
    write(ART/'summary.json',summary);write(ART/'recognition.json',recognition);write(ART/'paired_differences.json',paired_deltas)
    write(ART/'pid_evidence.json',pid_evidence);write(ART/'failures.json',failures)
    write_csv('recovery.csv',recovery);write_csv('recognition.csv',recognition);write_csv('recognition_counts.csv',outcomes);write_csv('costs.csv',costs)
    write_csv('failures.csv',failures,['case_id','attempt_id','method','kind','failure_category','serialization_status','first_transport_divergence','first_rank_divergence','error'])
    with (ART/'tables.md').open('w') as f:
        f.write('# Retained Stage 6 results\n\n## Attempt-level recovery and useful rate\n\n| Method | Payload bytes | Exact / attempted | Mean useful bits/token over attempts | Mean successful bits/token |\n|---|---:|---:|---:|---:|\n')
        for r in recovery:f.write(f"| {r['method']} | {r['payload_bytes']} | {r['authenticated_exact']}/{r['attempted']} | {fmt(r['mean_attempt_useful_bits_per_transmitted_token'])} | {fmt(r['mean_success_payload_bits_per_token'])} |\n")
        f.write('\n## Recognition (matched, scorable delivered pairs)\n\n| Method | Control | Score | Pairs | AUC | Cluster interval |\n|---|---|---|---:|---:|---|\n')
        for r in recognition:
            if r['metric'] in ['prefix_match','format_accepted','format_and_kem_canonical','mean_nll_bits','encrypted_body_nll_bits','token_count']:
                f.write(f"| {r['method']} | {r['family']} | {r['metric']} | {r['matched_scorable_pairs']} | {fmt(r['auc_higher_is_stego'])} | {r['auc_cluster_interval']} |\n")
        f.write('\nIntervals resample four context blocks and two repetitions within blocks; collapsed intervals are not population guarantees. Hidden aborts are reported separately.\n\n## Resources and failures\n\n')
        f.write('Stage 6 usage: '+json.dumps(incremental)+'. Lifetime: '+json.dumps(lifetime)+'.\n\n')
        for r in costs:f.write(f"- {r['stage6_phase']} / {r['method']} / {r['family']} / {r['payload_setting_bytes']}: {r['attempts']} cases, {r['charged_seconds']:.3f} seconds, {r['evaluated_tokens']} tokens.\n")
        f.write('\nFailures: '+json.dumps(collections.Counter(r['failure_category'] or r['serialization_status'] for r in failures))+'.\n')
    manifest={'schema_version':1,'starting_commit':auth['starting_commit'],'gpu_tested_code_commits':summary['gpu_tested_code_commits'],
        'historical_checkpoint':anchor,'authorization_file':'configs/stage6/authorization.json','ledger':'artifacts/project_budget.jsonl','checkpoint':'artifacts/project_budget.checkpoint.json',
        'ledger_sha256':summary['ledger_sha256'],'stage6_usage':incremental,'lifetime_usage':lifetime,
        'analysis_source':'artifacts/stage6/analyze.py','analysis_source_sha256':sha(Path(__file__)),
        'analysis_implementation_timing':'Host analysis source added after the GPU code freeze; frozen scientific analysis specification unchanged',
        'analysis_command':'.venv/bin/python artifacts/stage6/analyze.py','experiment_command':'.venv/bin/python scripts/run_stage6.py',
        'frozen_inputs':{str(p.relative_to(ROOT)):sha(p) for p in list((ROOT/'configs/stage6').glob('*.json'))+[ART/'allocation.json',ART/'TEST_ONLY_keys.json',ART/'environment.json',ROOT/'docs/stage6_study_spec.md',ROOT/'requirements-cpu.lock']},
        'attempts':manifests,'outputs':{str(p.relative_to(ROOT)):sha(p) for p in ART.iterdir() if p.is_file() and p.name not in ['controller.log','analysis_output.txt']},
        'security_scope':'Public predicates never authenticate; no concealment, sender-authentication or novelty proof',
        'historical_records_unchanged_except_append_only_ledger_and_extended_checkpoint':True}
    write(ROOT/'manifests/stage6_evidence.json',manifest)
    print(json.dumps({'status':'PASS','case_count':len(records),'stage6_usage':incremental,'lifetime_usage':lifetime,'unsettled':summary['unsettled_attempt_ids'],'recovery':recovery},indent=2))

if __name__=='__main__':main()
