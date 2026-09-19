#!/usr/bin/env python3
"""Host-only reconciliation of the frozen Stage9 study; no model inference."""
import base64,collections,csv,hashlib,json,math,random,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage9';sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.evaluation.stopping_rule import decompose_public_symbols
from llm_stego_public_key.profile import canonical_json

def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def mean(x):return statistics.mean(x) if x else None
def auc(a,b):return sum(float(x>y)+.5*(x==y) for x in a for y in b)/(len(a)*len(b)) if a and b else None
def quantile(a,q):
    a=sorted(a);x=(len(a)-1)*q;i=int(x);return a[i] if i+1==len(a) else a[i]+(a[i+1]-a[i])*(x-i)
def csvout(name,rr):
    if not rr:return
    with (ART/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
PREDICATES=['valid_utf8','canonical_bytes','all_candidates_member','stable_target_reached','ends_at_first_completion','filler_consistent','canonical_replay_consistent','kem_canonical','format_accepted','format_and_kem_canonical']

def main():
    status=read(ART/'status.json');a=read(ART/'allocation.json');auth=read(ROOT/'configs/stage9/authorization.json');rr=rows(ART/'cases.jsonl');by={r['case_id']:r for r in rr};slots={s['case_id']:s for s in a['slots']}
    raw=(ROOT/'artifacts/project_budget.jsonl').read_bytes();cp=read(ROOT/'artifacts/project_budget.checkpoint.json');anchor=auth['previous_checkpoint']
    assert hashlib.sha256(raw[:anchor['bytes']]).hexdigest()==anchor['sha256']
    assert cp['bytes']==len(raw) and cp['sha256']==hashlib.sha256(raw).hexdigest()
    reserve={};charges={};settled=set()
    for e in map(json.loads,raw.splitlines()):
        aid=e['attempt_id']
        if e['event']=='reserve':assert aid not in reserve;reserve[aid]=e;charges[aid]=e['reserved']
        else:assert e['event']=='settle' and aid not in settled;charges[aid]=e['charged'];settled.add(aid)
    assert set(reserve)==settled
    new={aid for aid,e in reserve.items() if e.get('allocation_id')==auth['allocation_id']}
    assert new=={r['attempt_id'] for r in rr} and len(rr)==len(new)
    lifetime={k:sum(c[k] for c in charges.values()) for k in ['seconds','tokens','cases']};usage={k:sum(charges[aid][k] for aid in new) for k in lifetime}
    assert lifetime==status['lifetime_usage']
    assert all(math.isclose(usage[k],status['stage9_usage'][k],rel_tol=1e-12) and usage[k]<=auth['additional_limits'][k] and lifetime[k]<=auth['lifetime_limits'][k] for k in usage)
    baseline=read(ART/'starting_state.json')['tracked_files']
    preserved={p:h for p,h in baseline.items() if p.startswith(('artifacts/stage1/','artifacts/stage2_pilot/','artifacts/stage3_transport/','artifacts/stage4_prefix/','artifacts/stage6/','artifacts/stage7/','artifacts/stage8/','configs/stage7/','configs/stage8/','src/llm_stego_public_key/codecs/'))}
    assert all(sha(ROOT/p)==h for p,h in preserved.items())
    manifest=[];detail=[];cost=[];progress=[]
    sys.path.insert(0,str(ROOT/'artifacts/stage8'));from diagnose import reference
    for r in rr:
        d=ROOT/r['evidence_dir'];j=read(d/'input.json');tr=read(d/'traces.json');cmd=read(d/'command.json');claim=read(d/'worker_claim.json')
        assert r['tested_code_commit']==j['tested_code_commit']==reserve[r['attempt_id']]['tested_code_commit']
        assert r['profile_sha256']==slots[r['case_id']]['profile_sha256']==hashlib.sha256(canonical_json(read(ROOT/j['profile_path']))).hexdigest()
        assert sha(d/'input.json')==cmd['environment']['STAGE1_JOB_SHA256']
        assert r['charged_tokens']==sum(r['tokens_by_phase'].values())==charges[r['attempt_id']]['tokens']
        assert r['exit_code']==0 and all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified','context_window_verified'])
        assert claim['pid']==r['pid'] and claim['attempt_id']==r['attempt_id']
        samples=read(d/'gpu_samples.json');assert samples and all(s['pid']==r['pid'] and s['gpu_uuid']==r['gpu_uuid'] for s in samples)
        assert 'offloaded 33/33 layers to GPU' in (d/'worker.log').read_text()
        if r['kind'] in ['control','historical_prefix']:assert 'TEST_ONLY_private_key_hex' not in j and 'payload_hex' not in j
        if r['kind']=='replay':
            assert not any(k in j for k in ['payload_hex','payload_sha256','expected_length','target_tokens','encoder_trace'])
            source=by[slots[r['case_id']]['source_case_id']];assert r['recovered_sha256']==source['payload_sha256']
            enc=read(ROOT/source['trace_path'])['encode'];dec=tr['fresh_receiver']
            assert enc['advanced_ids']==dec['advanced_ids'] and enc['symbols']==dec['symbols'] and enc['arithmetic_steps']==dec['arithmetic_steps']
        if r['wire_delivered']:
            wire=ROOT/j['carrier_path'] if r['kind']=='replay' else d/'carrier.txt'
            assert sha(wire)==r['transport_sha256'];wire.read_bytes().decode('utf-8',errors='strict')
        if r['kind']=='encrypted':
            env=base64.b64decode(r['serialized_base64'],validate=True);payload=bytes.fromhex(j['payload_hex'])
            assert len(env)==100 and len(payload)==32
            assert hashlib.sha256(env).hexdigest()==r['envelope_sha256'] and hashlib.sha256(payload).hexdigest()==r['payload_sha256']
            if r['authenticated_message_recovery']:assert r['recovered_sha256']==r['payload_sha256']
        o=r.get('observer',{})
        if o.get('scorable'):
            t=tr['public_scoring'];newp=decompose_public_symbols(t['symbols'],t['frequency_tables'],100,canonical=o['canonical_bytes'])
            assert all(o[k]==v for k,v in newp.items())
            assert len(t['received_ids'])==o['token_count'] and math.isclose(mean(t['nll_bits']),o['mean_nll_bits'],rel_tol=1e-12)
            if r['kind']=='encrypted':assert o['envelope_sha256']==r['envelope_sha256']
            # Compare public reconstruction with generation only outside observer.
            if r['kind']=='control':
                g=tr['control_generation'];assert t['received_ids']==g['advanced_ids'] and t['symbols']==g['symbols']
                assert t['frequency_tables']==[s['frequencies'] for s in g['arithmetic_steps']]
                assert o['first_completion_token']==r['generation_completion']['first_completion_token']
        if r['kind'] in ['encrypted','control']:
            g=tr['encode' if r['kind']=='encrypted' else 'control_generation'];n=len(g['advanced_ids']);steps=g['arithmetic_steps']
            bits,states=reference(g['symbols'],[s['frequencies'] for s in steps])
            first=next((i+1 for i,s in enumerate(states) if s['stable_bits']>=800),None)
            if r['kind']=='encrypted':
                target=[(b>>i)&1 for b in env for i in range(7,-1,-1)]+[1]+[0]*64
                assert bits==target[:len(bits)]
                assert all(all(x[k]==y[k] for k in ['low','high_inclusive','stable_bits','pending_underflow']) for x,y in zip(steps,states))
                assert r['wire_delivered']==(first is not None)
            else:
                assert first==r['generation_completion']['first_completion_token']
                if r['family']=='B-stop':assert r['wire_delivered']==(first is not None) and (first is None or first==n)
            progress.append(dict(case_id=r['case_id'],kind=r['kind'],family=r.get('family'),context_index=r['context_index'],first_completion=first,emitted_tokens=n,stable_bits_at_end=states[-1]['stable_bits'],stable_curve=[s['stable_bits'] for s in states],independent_integer_reference=True))
        detail.append(dict(case_id=r['case_id'],phase=r['stage9_phase'],kind=r['kind'],family=r.get('family'),context=r['context_index'],delivered=r['wire_delivered'],authenticated_exact=r['authenticated_message_recovery'],failure=r['failure_category'],tokens=r.get('carrier_tokens',r.get('generated_tokens',len(tr.get('encode',{}).get('advanced_ids',[])))),first_completion=o.get('first_completion_token',r.get('generation_completion',{}).get('first_completion_token')),stable_bits=o.get('stable_bits',r.get('generation_completion',{}).get('stable_bits')),**{k:o.get(k) for k in PREDICATES},mean_nll_bits=o.get('mean_nll_bits'),mean_log2_rank=o.get('mean_log2_rank'),utf8_bytes=r.get('transport_bytes')))
        cost.append(dict(case_id=r['case_id'],kind=r['kind'],family=r.get('family'),job_seconds=r['job_elapsed_seconds'],evaluated_tokens=r['charged_tokens'],peak_sampled_vram_mib=r['peak_sampled_process_vram_mib'],load_seconds=r['timings']['load_and_verify_seconds'],encode_seconds=r['timings'].get('encode_seconds'),generation_seconds=r['timings'].get('control_generation_seconds'),receiver_seconds=r['timings'].get('receiver_seconds',r['timings'].get('fresh_receiver_seconds')),observer_seconds=r['timings'].get('public_scoring_seconds')))
        manifest.append(dict(case_id=r['case_id'],attempt_id=r['attempt_id'],tested_code_commit=r['tested_code_commit'],profile_sha256=r['profile_sha256'],files={str(p.relative_to(ROOT)):sha(p) for p in d.iterdir() if p.is_file()}))
    principal=[r for r in rr if r['stage9_phase']=='prospective'];grouped={g:[r for r in principal if ('R' if r['kind']=='encrypted' else r['family'])==g] for g in ['R','B-fixed','B-stop']}
    counts={};predcounts={}
    for g,rs in grouped.items():
        delivered=[r for r in rs if r['wire_delivered']];scorable=[r for r in rs if r.get('observer',{}).get('scorable')]
        completed=sum(bool(r.get('observer',{}).get('stable_target_reached',r.get('generation_target_reached',False))) for r in rs)
        counts[g]=dict(planned=6,attempted=len(rs),stable_packet_completed=completed,delivered=len(delivered),scorable=len(scorable),authenticated_exact=sum(r['authenticated_message_recovery'] for r in rs),capacity_aborts=sum(r['failure_category']=='capacity_exhaustion' for r in rs),successful_generation=sum(r['success'] for r in rs))
        predcounts[g]={k:dict(true=sum(r['observer'].get(k) is True for r in scorable),false=sum(r['observer'].get(k) is False for r in scorable),unavailable=sum(r['observer'].get(k) is None for r in scorable),delivered_scorable_denominator=len(scorable)) for k in PREDICATES}
    pairs=[]
    for c in range(6):
        fixed=by.get(f'B-fixed-c{c}');stop=by.get(f'B-stop-c{c}')
        if not fixed or not stop:continue
        a_trace=read(ROOT/fixed['trace_path'])['control_generation'];b_trace=read(ROOT/stop['trace_path'])['control_generation'];n=min(len(a_trace['advanced_ids']),len(b_trace['advanced_ids']))
        assert a_trace['advanced_ids'][:n]==b_trace['advanced_ids'][:n] and a_trace['arithmetic_steps'][:n]==b_trace['arithmetic_steps'][:n]
        assert [s['ordered_ids_sha256'] for s in a_trace['candidate_steps'][:n]]==[s['ordered_ids_sha256'] for s in b_trace['candidate_steps'][:n]]
        first=fixed.get('observer',{}).get('first_completion_token')
        counterfactual=None
        if first is not None:
            public=read(ROOT/fixed['trace_path'])['public_scoring']
            counterfactual=decompose_public_symbols(public['symbols'][:first],public['frequency_tables'][:first],100)
        pairs.append(dict(context=c,common_tokens=n,common_prefix_agreement=True,fixed_first_prefix_counterfactual=counterfactual,counterfactual_scope='Pure public-table derived prefix, not another live sample' if counterfactual else None,fixed_tokens=fixed.get('carrier_tokens'),stop_generated_tokens=stop.get('generated_tokens'),stop_delivered=stop['wire_delivered'],fixed_format=fixed.get('observer',{}).get('format_accepted'),stop_format=stop.get('observer',{}).get('format_accepted'),fixed_first_completion=fixed.get('observer',{}).get('first_completion_token'),stop_first_completion=stop.get('generation_completion',{}).get('first_completion_token')))
    recognition=[];rng=random.Random(2026092199);draws=[rng.choices(range(6),k=6) for _ in range(2000)]
    for family in ['B-fixed','B-stop']:
        for metric in ['mean_nll_bits','mean_log2_rank','mean_admissible_nll_bits','token_count','utf8_bytes']:
            support={c:(by[f'R-c{c}']['observer'][metric],by[f'{family}-c{c}']['observer'][metric]) for c in range(6) if all(by.get(k,{}).get('observer',{}).get('scorable') and by[k]['observer'].get(metric) is not None for k in [f'R-c{c}',f'{family}-c{c}'])}
            item=dict(control_family=family,metric=metric,orientation='higher_is_R',matched_contexts=list(support),pairs=len(support),raw_context_pairs=support,paired_differences={c:x-y for c,(x,y) in support.items()},auc=None,cluster_interval=None)
            if len(support)>=4:
                bs=[]
                for draw in draws:
                    sample=[support[c] for c in draw if c in support]
                    if sample:bs.append(auc([x for x,y in sample],[y for x,y in sample]))
                item.update(auc=auc([x for x,y in support.values()],[y for x,y in support.values()]),cluster_interval=[quantile(bs,.025),quantile(bs,.975)],bootstrap_valid=len(bs))
            else:item['reason']='Fewer than four delivered paired contexts; raw scores only as frozen'
            recognition.append(item)
    recovery=grouped['R'];success=[r for r in recovery if r['authenticated_message_recovery']]
    uncertainty={}
    for group,rs in grouped.items():
        cc={r['context_index']:bool(r.get('observer',{}).get('stable_target_reached',r.get('generation_target_reached',False))) for r in rs}
        bs=[mean([cc[c] for c in draw if c in cc]) for draw in draws];bs=[x for x in bs if x is not None]
        uncertainty[group]=dict(context_bootstrap_interval=[quantile(bs,.025),quantile(bs,.975)] if bs else None,warning='Six selected contexts; empirical cluster interval is not a population guarantee')
    phases=collections.Counter();failures=collections.Counter()
    for r in rr:phases.update(r['tokens_by_phase']);failures.update([r['failure_category']] if r['failure_category'] else [])
    summary=dict(schema_version=1,starting_commit=a['starting_commit'],gpu_tested_revisions=sorted({r['tested_code_commit'] for r in rr}),status=status['stop_reason'],counts=counts,predicate_counts=predcounts,
        retrospective_jobs=sum(r['kind']=='historical_prefix' for r in rr),fresh_receiver_attempts=sum(r['kind']=='replay' for r in rr),fresh_receiver_recoveries=sum(r['kind']=='replay' and r['authenticated_message_recovery'] for r in rr),skipped=status['skipped'],failures=dict(failures),
        usage=usage,lifetime_usage=lifetime,parent_remaining={k:auth['lifetime_limits'][k]-lifetime[k] for k in lifetime},stage9_remaining={k:auth['additional_limits'][k]-usage[k] for k in lifetime},tokens_by_phase=dict(phases),gpu=read(ART/'environment.json')['selected_gpu'],peak_sampled_vram_mib=max(r['peak_sampled_process_vram_mib'] for r in rr),
        useful_rate=dict(mean_success_bits_per_token=mean([256/r['carrier_tokens'] for r in success]),mean_attempt_bits_per_token=mean([256/r['carrier_tokens'] if r['authenticated_message_recovery'] else 0 for r in recovery]),recovered_bytes_per_job_second=32*len(success)/sum(r['job_elapsed_seconds'] for r in recovery)),
        probability_rounding={g:dict(mean_message_tv=mean([r['observer']['probability_rounding_mean_tv'] for r in rs if r.get('observer',{}).get('scorable')]),max_step_tv=max((r['observer']['probability_rounding_max_tv'] for r in rs if r.get('observer',{}).get('scorable')),default=None)) for g,rs in grouped.items()},completion_uncertainty=uncertainty,verification=dict(historical_files_unchanged=len(preserved),historical_ledger_prefix_preserved=True,all_reservations_settled=True,all_gpu_lease_phase_provenance_verified=True,independent_arithmetic_checks=True,paired_prefix_checks=len(pairs)),split='prospective development; no historical pooling; not final held-out evaluation')
    put(ART/'summary.json',summary);put(ART/'recognition.json',recognition);put(ART/'paired_trajectories.json',pairs);put(ART/'progress.json',progress)
    csvout('predicates.csv',detail);csvout('costs.csv',cost);csvout('paired_trajectories.csv',pairs)
    topfiles={str(p.relative_to(ROOT)):sha(p) for p in ART.iterdir() if p.is_file() and p.name not in ['analysis_output.txt','controller_output.txt']}
    put(ROOT/'manifests/stage9_evidence.json',dict(schema_version=1,starting_commit=a['starting_commit'],tested_revisions=summary['gpu_tested_revisions'],allocation_path='artifacts/stage9/allocation.json',authorization='configs/stage9/authorization.json',ledger_anchor=anchor,ledger_final_checkpoint=cp,ledger_path='artifacts/project_budget.jsonl',attempts=manifest,files=topfiles,commands=['.venv/bin/python scripts/prepare_stage9.py','.venv/bin/python -m pytest -q tests/test_stage9.py','.venv/bin/python scripts/run_stage9.py','.venv/bin/python artifacts/stage9/analyze.py'],source_attribution='docs/stage7_comparator_audit.md',dependency_identity='artifacts/stage9/environment.json'))
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
