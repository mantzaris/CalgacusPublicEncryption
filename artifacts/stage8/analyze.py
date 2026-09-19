#!/usr/bin/env python3
"""Host-only reconciliation and frozen descriptive analysis; no model inference."""
import base64,collections,csv,hashlib,json,math,random,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage8';sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.codecs.arithmetic_core import PacketDecoder
from llm_stego_public_key.errors import FramingError

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def avg(v):return statistics.mean(v) if v else None

def quantile(v,q):
    if not v:return None
    a=sorted(v);x=(len(a)-1)*q;i=int(x);return a[i] if i+1==len(a) else a[i]+(a[i+1]-a[i])*(x-i)
def interval(v):return [quantile(v,.025),quantile(v,.975)]
def auc(a,b):return sum(1 if x>y else .5 if x==y else 0 for x in a for y in b)/(len(a)*len(b)) if a and b else None
def table(name,rows):
    if not rows:return
    with (ART/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    qual=read(ART/'diagnostic_status.json');status=read(ART/'main_status.json') if (ART/'main_status.json').exists() else qual
    allocation=read(ART/'allocation.json');auth=read(ROOT/'configs/stage8/authorization.json');slots={s['case_id']:s for s in allocation['slots']}
    release=read(ART/'main_release.json') if (ART/'main_release.json').exists() else None
    repetitions=release['repetitions'] if release else 0
    selected=set(release['selected_case_ids']) if release else set()
    oldrecords=[json.loads(l) for l in (ROOT/'artifacts/stage7/cases.jsonl').read_text().splitlines()]
    oldbyid={r['attempt_id']:r for r in oldrecords}
    records=[json.loads(l) for l in (ART/'cases.jsonl').read_text().splitlines()];byid={r['case_id']:r for r in records}
    raw=(ROOT/'artifacts/project_budget.jsonl').read_bytes();anchor=auth['previous_checkpoint'];cp=read(ROOT/'artifacts/project_budget.checkpoint.json')
    assert hashlib.sha256(raw[:anchor['bytes']]).hexdigest()==anchor['sha256']
    assert cp['sha256']==hashlib.sha256(raw).hexdigest() and cp['bytes']==len(raw)
    jobs={};reserves={};settled=set()
    for e in map(json.loads,raw.splitlines()):
        aid=e['attempt_id']
        if e['event']=='reserve':assert aid not in jobs;jobs[aid]=e['reserved'];reserves[aid]=e
        else:assert aid in jobs and aid not in settled;jobs[aid]=e['charged'];settled.add(aid)
    lifetime={k:sum(v[k] for v in jobs.values()) for k in ['seconds','tokens','cases']};usage={k:lifetime[k]-auth['baseline_usage'][k] for k in lifetime}
    assert lifetime==status['lifetime_usage'] and all(usage[k]<=auth['additional_limits'][k] for k in usage)
    new={aid for aid,e in reserves.items() if e.get('allocation_id')==auth['allocation_id']}
    assert new=={r['attempt_id'] for r in records} and len(new)==len(records) and new<=settled
    manifests=[];capacity=[];checks=[];candidate_steps=[];checkpoints=[];progress_summaries=[]
    for r in records:
        d=ROOT/r['evidence_dir'];j=read(d/'input.json');cmd=read(d/'command.json');claim=read(d/'worker_claim.json');tr=read(d/'traces.json')
        assert r['tested_code_commit']==j['tested_code_commit']==reserves[r['attempt_id']]['tested_code_commit']
        assert r['profile_sha256']==slots[r['case_id']]['profile_sha256']
        assert sha(d/'input.json')==cmd['environment']['STAGE1_JOB_SHA256']
        assert r['charged_tokens']==sum(r['tokens_by_phase'].values())==jobs[r['attempt_id']]['tokens']
        assert claim['pid']==r['pid'] and claim['attempt_id']==r['attempt_id']
        samples=read(d/'gpu_samples.json');assert samples and all(x['pid']==r['pid'] and x['gpu_uuid']==r['gpu_uuid'] for x in samples)
        assert 'offloaded 33/33 layers to GPU' in (d/'worker.log').read_text()
        if r.get('wire_delivered') and r['kind']!='replay':assert sha(d/'carrier.txt')==r['transport_sha256']
        if r['kind']=='encrypted':
            payload=bytes.fromhex(j['payload_hex']);env=base64.b64decode(r['serialized_base64'],validate=True)
            assert len(env)==68+len(payload)==r['envelope_bytes']
            assert hashlib.sha256(payload).hexdigest()==r['payload_sha256'] and hashlib.sha256(env).hexdigest()==r['envelope_sha256']
            assert hashlib.sha256(env[32:]).hexdigest()==r['ciphertext_sha256']
            if r.get('authenticated_message_recovery'):assert r['recovered_sha256']==r['payload_sha256']
        if r['kind']=='fixture':
            old=oldbyid[slots[r['case_id']]['historical_attempt_id']]
            assert r['envelope_sha256']==old['envelope_sha256']
            if r.get('exact_envelope_recovery'):assert r['recovered_envelope_sha256']==old['envelope_sha256']
            if r.get('original_binding_authenticated'):assert r['recovered_sha256']==old['payload_sha256']
        if r['kind']=='replay':
            assert not any(k in j for k in ['payload_hex','payload_sha256','payload_bytes','expected_length','encoder_trace','target_tokens'])
            if r.get('authenticated_message_recovery'):
                expected=(oldbyid[slots[r['case_id']]['historical_attempt_id']]['payload_sha256'] if r['stage8_phase']=='diagnostic' else byid[slots[r['case_id']]['source_case_id']]['payload_sha256'])
                assert r['recovered_sha256']==expected
        o=r.get('observer',{})
        if o.get('scorable'):
            t=tr['public_scoring'];assert len(t['received_ids'])==o['token_count']==len(t['symbols'])
            assert math.isclose(avg(t['nll_bits']),o['mean_nll_bits'],rel_tol=1e-12)
            assert math.isclose(avg([math.log2(x) for x in t['ranks']]),o['mean_log2_rank'],rel_tol=1e-12)
            env=None;err=None
            try:
                if not o['canonical_bytes'] or any(x is None for x in t['symbols']):raise FramingError('unsupported')
                n=read(ROOT/j['profile_path'])['public_size_class']['envelope_bytes']
                if r['method']=='R':
                    dec=PacketDecoder(n)
                    for symbol,freq in zip(t['symbols'],t['frequency_tables']):dec.step(symbol,freq)
                    env=dec.finish()
                else:
                    if len(t['symbols'])!=2*n:raise FramingError('size')
                    env=bytes((a<<4)|b for a,b in zip(t['symbols'][::2],t['symbols'][1::2]))
            except FramingError as exc:err=str(exc)
            assert (env is not None)==o['format_accepted']
            if env is not None:
                assert hashlib.sha256(env).hexdigest()==o['envelope_sha256']
                assert (int.from_bytes(env[:32],'little')<2**255-19)==o['kem_canonical']
                if r['kind']=='encrypted':assert o['envelope_sha256']==r['envelope_sha256']
        candidate_steps.extend(step for trace in tr.values() for step in trace.get('candidate_steps',[]))
        enc=tr.get('encode',{});terminal=enc.get('terminal',{})
        if r['method']=='R' and r['kind'] in ['encrypted','fixture']:
            capacity.append({'case_id':r['case_id'],'phase':r['stage8_phase'],'envelope_bytes':r.get('envelope_bytes'),
                'success':r['success'],'failure':r['failure_category'],'emitted_tokens':len(enc.get('advanced_ids',[])),
                'stable_bits':terminal.get('stable_bits'),'target_bits':8*r.get('envelope_bytes',0),'terminal':terminal,
                'wire_delivered':r['wire_delivered'],'carrier_tokens':r.get('carrier_tokens')})
        if r['kind'] in ['fixture','encrypted']:
            is_hpke=r['kind']=='encrypted' or oldbyid[slots[r['case_id']]['historical_attempt_id']]['kind']=='encrypted'
            exact_packet=r.get('exact_envelope_recovery',r.get('exact_recovery',False))
            authenticated=r.get('original_binding_authenticated',False) if r['kind']=='fixture' else r.get('authenticated_message_recovery',False)
            enc=tr.get('encode',{});ids=enc.get('advanced_ids',[]);steps=enc.get('arithmetic_steps',[])
            for budget in [512,1024,1536,1984]:
                reached=min(len(ids),budget)
                stable=(steps[reached-1]['stable_bits'] if reached else 0) if r['method']=='R' else 4*reached
                complete=bool(exact_packet and len(ids)<=budget)
                checkpoints.append({'case_id':r['case_id'],'phase':r['stage8_phase'],'method':r['method'],'payload_class_bytes':r['payload_setting_bytes'],
                    'budget':budget,'stable_bits':stable,'required_envelope_bits':8*r['envelope_bytes'],'complete_envelope_by_budget':complete,
                    'authenticated_by_budget':bool(authenticated and complete),'useful_payload_bits':8*r['payload_setting_bytes'] if authenticated and complete else (0 if is_hpke else None),
                    'successful_payload_bits_per_token':8*r['payload_setting_bytes']/len(ids) if authenticated and complete else (0 if is_hpke else None),
                    'envelope_bits_recovered':8*r['envelope_bytes'] if complete else 0,'is_hpke':is_hpke})
            if r['method']=='R':
                from diagnose import reference,blocks
                bits,reconstructed=reference(enc['symbols'],[x['frequencies'] for x in steps])
                for stored,rebuilt in zip(steps,reconstructed):
                    assert all(stored[k]==rebuilt[k] for k in ['low','high_inclusive','pending_underflow','stable_bits'])
                table('progress_'+r['case_id']+'.csv',reconstructed)
                progress_summaries.append({'case_id':r['case_id'],'phase':r['stage8_phase'],'tokens':len(ids),'mean_table_entropy':avg([x['table_entropy_bits'] for x in reconstructed]),
                    'mean_selected_information':avg([x['selected_information_bits'] for x in reconstructed]),'blocks128':blocks(reconstructed,128),'blocks256':blocks(reconstructed,256)})
        manifests.append({'case_id':r['case_id'],'attempt_id':r['attempt_id'],'tested_code_commit':r['tested_code_commit'],'profile_sha256':r['profile_sha256'],
            'files':{str(p.relative_to(ROOT)):sha(p) for p in d.iterdir() if p.is_file()}})
        checks.append({'case_id':r['case_id'],'pid':r['pid'],'gpu_uuid':r['gpu_uuid'],'peak_sampled_vram_mib':r['peak_sampled_process_vram_mib']})
    mainrows=[r for r in records if r['kind']=='encrypted' and r['stage8_phase']=='main_fixed'];controls=[r for r in records if r['kind']=='control']
    rng=random.Random(2026092008);draws=[]
    for _ in range(2000):
        draws.append([(c,rep) for c in rng.choices(list(range(4)),k=4) for rep in rng.choices([32,128],k=2)])
    recovery=[]
    for m in ['F','R']:
      for size in [32,128]:
        rr=[r for r in mainrows if r['method']==m and r['payload_bytes']==size];ok=[r for r in rr if r.get('authenticated_message_recovery')]
        groups=collections.defaultdict(list)
        for r in rr:groups[(r['context_index'],r['payload_setting_bytes'])].append(r)
        rates=[];useful=[]
        for draw in draws:
            sample=[r for group in draw for r in groups[group]]
            if sample:
                rates.append(sum(r.get('authenticated_message_recovery',False) for r in sample)/len(sample))
                useful.append(avg([r.get('attempt_useful_bits_per_transmitted_token',0) for r in sample]))
        delivered=sum(r.get('carrier_tokens',0) for r in rr if r['wire_delivered'])
        recovery.append({'method':m,'payload_bytes':size,'planned':4*repetitions,'attempted':len(rr),'authenticated_exact':len(ok),'capacity_failures':sum(r['failure_category']=='capacity_exhaustion' for r in rr),
            'recovery_fraction':len(ok)/len(rr) if rr else None,'recovery_cluster_interval':interval(rates),
            'carrier_token_min':min((r['carrier_tokens'] for r in ok),default=None),'carrier_token_max':max((r['carrier_tokens'] for r in ok),default=None),
            'mean_success_payload_bits_per_token':avg([r['successful_payload_bits_per_token'] for r in ok]),
            'mean_attempt_useful_bits_per_token':avg([r.get('attempt_useful_bits_per_transmitted_token',0) for r in rr]),'useful_rate_cluster_interval':interval(useful),
            'aggregate_recovered_bits_per_delivered_token':8*size*len(ok)/delivered if delivered else None,
            'recovered_bytes_per_charged_second':size*len(ok)/sum(r['job_elapsed_seconds'] for r in rr) if rr else None})
    metrics=['mean_nll_bits','mean_log2_rank','mean_admissible_nll_bits','member_fraction','format_accepted','format_and_kem_canonical','token_count','utf8_bytes']
    recognition=[];outcomes=[];boots={}
    for m in ['F','R']:
      for family in 'B':
        positives=[r for r in mainrows if r['method']==m];negatives=[r for r in controls if r['method']==m and r['family']==family]
        for role,rr in [('encrypted',positives),('control',negatives)]:
            outcomes.append({'method':m,'family':family,'role':role,'attempted':len(rr),'delivered':sum(r['wire_delivered'] for r in rr),
                'scorable':sum(r.get('observer',{}).get('scorable',False) for r in rr),'format_accepted':sum(r.get('observer',{}).get('format_accepted',False) for r in rr),
                'format_and_kem_canonical':sum(r.get('observer',{}).get('format_and_kem_canonical',False) for r in rr),
                'all_candidates_member':sum(r.get('observer',{}).get('all_candidates_member',False) for r in rr),
                'invalid_utf8':sum(r.get('serialization_status')=='invalid_utf8' for r in rr),'retokenization_drift':sum(r.get('serialization_status')=='retokenization_drift' for r in rr),
                'capacity_failures':sum(r.get('failure_category')=='capacity_exhaustion' for r in rr)})
        for metric in metrics:
            pairs=[];groups=collections.defaultdict(list)
            for p in positives:
                n=byid.get(f"control-{p['case_id']}-{family}")
                if n and all(r.get('observer',{}).get('scorable') and r['observer'].get(metric) is not None for r in [p,n]):
                    pair=(float(p['observer'][metric]),float(n['observer'][metric]));pairs.append((p,pair));groups[(p['context_index'],p['payload_setting_bytes'])].append(pair)
            bs=[]
            for draw in draws:
                sample=[x for g in draw for x in groups[g]]
                bs.append(auc([x for x,y in sample],[y for x,y in sample]))
            xs=[xy[0] for p,xy in pairs];ys=[xy[1] for p,xy in pairs];boots[(m,family,metric)]=bs
            recognition.append({'method':m,'family':family,'metric':metric,'matched_scorable_pairs':len(pairs),'encrypted_mean':avg(xs),'control_mean':avg(ys),
                'auc_higher_is_carrier':auc(xs,ys),'cluster_interval':interval([v for v in bs if v is not None]),
                'context_auc':{str(c):auc([xy[0] for p,xy in pairs if p['context_index']==c],[xy[1] for p,xy in pairs if p['context_index']==c]) for c in range(4)}})
    deltas=[]
    for fam in 'B':
      for metric in metrics:
        f=next(x for x in recognition if (x['method'],x['family'],x['metric'])==('F',fam,metric));r=next(x for x in recognition if (x['method'],x['family'],x['metric'])==('R',fam,metric))
        complete=f['matched_scorable_pairs']==r['matched_scorable_pairs']==8*repetitions and repetitions>0
        differences=[r-f for r,f in zip(boots['R',fam,metric],boots['F',fam,metric])] if complete else []
        deltas.append({'family':fam,'metric':metric,'R_minus_F_auc':r['auc_higher_is_carrier']-f['auc_higher_is_carrier'] if complete else None,'paired_interval':interval(differences),'complete_support':complete})
    size_recognition=[];joint_recognition=[]
    def metric_pairs(method,metric,size=None):
        out=[]
        for r in mainrows:
            if r['method']!=method or (size is not None and r['payload_bytes']!=size):continue
            control=byid.get('control-'+r['case_id']+'-B')
            if control and all(x.get('observer',{}).get('scorable') and x['observer'].get(metric) is not None for x in [r,control]):
                out.append((r,float(r['observer'][metric]),float(control['observer'][metric])))
        return out
    for method in ['F','R']:
      for size in [32,128]:
       for metric in metrics:
        pp=metric_pairs(method,metric,size);bs=[]
        for draw in draws:
            # Context draws are entries0,2,4,6; size/key resampling is not used
            # within this already size-conditioned stratum.
            sample=[x for c,_ in draw[::2] for x in pp if x[0]['context_index']==c]
            if sample:bs.append(auc([x[1] for x in sample],[x[2] for x in sample]))
        size_recognition.append({'method':method,'payload_bytes':size,'metric':metric,'pairs':len(pp),'auc':auc([x for r,x,y in pp],[y for r,x,y in pp]),'interval':interval(bs)})
    for metric in metrics:
        ff={r['pair_id']:(r,x,y) for r,x,y in metric_pairs('F',metric)};rr={r['pair_id']:(r,x,y) for r,x,y in metric_pairs('R',metric)}
        common=sorted(set(ff)&set(rr));groups=collections.defaultdict(list)
        for k in common:groups[(ff[k][0]['context_index'],ff[k][0]['payload_bytes'])].append(k)
        bs=[]
        for draw in draws:
            sample=[k for group in draw for k in groups[group]]
            if sample:bs.append(auc([rr[k][1] for k in sample],[rr[k][2] for k in sample])-auc([ff[k][1] for k in sample],[ff[k][2] for k in sample]))
        fa=auc([ff[k][1] for k in common],[ff[k][2] for k in common]);ra=auc([rr[k][1] for k in common],[rr[k][2] for k in common])
        joint_recognition.append({'metric':metric,'pairs':len(common),'pair_ids':common,'F_auc':fa,'R_auc':ra,'R_minus_F':ra-fa if fa is not None else None,'interval':interval(bs),
          'conditioning':'both methods and their length-matched B controls delivered/scorable, metric available; no authentication filter'})
    costgroups=collections.defaultdict(list)
    for r in records:costgroups[(r['stage8_phase'],r['kind'],r['method'],r.get('family') or '-',r['payload_setting_bytes'])].append(r)
    costs=[]
    for group,rr in costgroups.items():
        costs.append(dict(zip(['phase','kind','method','family','payload_bytes'],group),attempts=len(rr),charged_seconds=sum(r['job_elapsed_seconds'] for r in rr),evaluated_tokens=sum(r['charged_tokens'] for r in rr),
            mean_job_seconds=avg([r['job_elapsed_seconds'] for r in rr]),peak_sampled_vram_mib=max(r['peak_sampled_process_vram_mib'] for r in rr),
            **{f'mean_{name}':avg([r['timings'][name] for r in rr if name in r['timings']]) for name in ['load_and_verify_seconds','encode_seconds','receiver_seconds','public_scoring_seconds','control_generation_seconds']}))
    failures=[{'case_id':r['case_id'],'category':r['failure_category'],'serialization':r.get('serialization_status'),'error':r.get('error',r.get('receiver_error')),'first_transport_divergence':r.get('first_transport_divergence')} for r in records if r.get('failure_category') or r.get('serialization_status')=='retokenization_drift']
    historical=read(ART/'starting_state.json')['tracked_files'];changed=[p for p,h in historical.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    allowed={'src/llm_stego_public_key/profile.py','src/llm_stego_public_key/evaluation/budget.py','THIRD_PARTY_NOTICES.md','artifacts/project_budget.jsonl','artifacts/project_budget.checkpoint.json'}
    assert set(changed)<=allowed,changed
    summary={'schema_version':1,'starting_commit':auth['starting_commit'],'gpu_tested_code_commits':sorted({r['tested_code_commit'] for r in records}),
        'diagnostic_status':qual,'planned_slots':80,'main_planned_slots':len(selected),'diagnostic_attempts':len([r for r in records if r['stage8_phase']=='diagnostic']),'main_repetitions':repetitions,'main_executed':bool(mainrows),'attempted_cases':len(records),'main_encrypted_attempts':len(mainrows),'control_attempts':len(controls),
        'main_independent_recipient_keys':len({r['receiver_public_key_hex'] for r in mainrows}),
        'replays':[{'case_id':r['case_id'],'phase':r['stage8_phase'],'authenticated_exact':r.get('authenticated_message_recovery',False),'raw_envelope_exact':r.get('exact_recovery',False) if r['stage8_phase']=='diagnostic' else None,'original_binding_authenticated':r.get('original_binding_authenticated',False)} for r in records if r['kind']=='replay'],
        'recovery':recovery,'size_recognition':size_recognition,'joint_support_recognition':joint_recognition,'recognition':recognition,'recognition_counts':outcomes,'paired_auc_differences':deltas,'capacity':capacity,'costs':costs,'failures':failures,
        'candidate_search':{'steps':len(candidate_steps),'examined_total':sum(x['examined'] for x in candidate_steps),'examined_max':max((x['examined'] for x in candidate_steps),default=None),'all_steps_admitted_16':all(x['eligible_found_capped_at_16']==16 for x in candidate_steps)},
        'stage8_usage':usage,'lifetime_usage':lifetime,'unused_stage8_allowance':{k:auth['additional_limits'][k]-usage[k] for k in usage},
        'selected_gpu':read(ART/'environment.json')['selected_gpu'],'peak_sampled_vram_mib':max(r['peak_sampled_process_vram_mib'] for r in records),
        'phase_tokens':dict(sum((collections.Counter(r['tokens_by_phase']) for r in records),collections.Counter())),
        'historical_ledger_prefix_preserved':True,'historical_changed_paths':changed,'historical_data_pooled':False,
        'ledger_sha256':sha(ROOT/'artifacts/project_budget.jsonl'),'ledger_bytes':len(raw),'unsettled_attempts':sorted(set(jobs)-settled),
        'all_gpu_lease_phase_provenance_verified':all(all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified','context_window_verified']) for r in records),
        'all_workers_clean_exit':all(r['exit_code']==0 for r in records),'unique_worker_pids':len({r['pid'] for r in records}),
        'stop_reason':status['stop_reason'],'skipped':qual['skipped']+(status['skipped'] if status is not qual else []),
        'main_skipped_by_gate':[s['case_id'] for s in allocation['slots'] if s['stage8_phase']!='diagnostic' and s['case_id'] not in byid and (not release or s['case_id'] in selected)],
        'main_unselected_before_release':[s['case_id'] for s in allocation['slots'] if s['stage8_phase']!='diagnostic' and release and s['case_id'] not in selected],
        'checkpoints':checkpoints,'progress_summaries':progress_summaries,'remaining_parent_allowance':{k:auth['lifetime_limits'][k]-lifetime[k] for k in lifetime},
        'focused_cpu_tests':5,'broad_cpu_suite':False,'bootstrap':{'draws':2000,'seed':2026092008,'unit':'four contexts then size/recipient-key groups; repetitions/methods/controls/checkpoints retained jointly','limits':'conditional descriptive intervals; four contexts; degenerate intervals are not population guarantees'}}
    for name,obj in [('summary.json',summary),('recognition.json',recognition),('capacity.json',capacity),('failures.json',failures),('pid_evidence.json',checks)]:write(ART/name,obj)
    for name,rr in [('recovery.csv',recovery),('recognition.csv',recognition),('recognition_counts.csv',outcomes),('costs.csv',costs),('capacity.csv',capacity)]:table(name,rr)
    manifest={'schema_version':1,'starting_commit':auth['starting_commit'],'gpu_tested_code_commits':summary['gpu_tested_code_commits'],'historical_checkpoint':anchor,'ledger_sha256':summary['ledger_sha256'],
        'stage8_usage':usage,'lifetime_usage':lifetime,'attempts':manifests,'frozen_inputs':{str(p.relative_to(ROOT)):sha(p) for p in list((ROOT/'configs/stage8').glob('*.json'))+[ART/'allocation.json',ART/'TEST_ONLY_keys.json',ART/'environment.json',ROOT/'docs/stage8_study_spec.md',ROOT/'requirements-cpu.lock']},
        'commands':['.venv/bin/python -m pytest -q tests/test_stage8.py','.venv/bin/python scripts/prepare_stage8.py','.venv/bin/python scripts/run_stage8.py --allocation-check','.venv/bin/python scripts/run_stage8.py --phase diagnostic','.venv/bin/python scripts/run_stage8.py --phase main' if mainrows else 'Main not executed','.venv/bin/python artifacts/stage8/analyze.py'],
        'historical_diagnosis':{'path':'artifacts/stage8/historical_diagnosis.json','sha256':sha(ART/'historical_diagnosis.json')},
        'diagnostic_prefix_and_receiver_checks':{'path':'artifacts/stage8/diagnostic_checks.jsonl','sha256':sha(ART/'diagnostic_checks.jsonl')},
        'analysis_source_sha256':sha(Path(__file__)),'analysis_note':'Host-only implementation after GPU freeze; no model inference; earlier CPU results retain their original revisions'}
    write(ROOT/'manifests/stage8_evidence.json',manifest)
    table('size_recognition.csv',size_recognition)
    table('joint_support_recognition.csv',joint_recognition)
    table('checkpoints.csv',checkpoints)
    write(ART/'progress_summary.json',progress_summaries)
    table('diagnostic.csv',[{'case_id':r['case_id'],'kind':r['kind'],'payload_class_bytes':r['payload_setting_bytes'],'envelope_bytes':r.get('envelope_bytes'),'authenticated_exact':r.get('authenticated_message_recovery',False),'raw_envelope_exact':r.get('exact_envelope_recovery',r.get('exact_recovery',False)),'failure_category':r['failure_category'],'wire_delivered':r['wire_delivered'],'job_seconds':r['job_elapsed_seconds'],'evaluated_tokens':r['charged_tokens']} for r in records if r['stage8_phase']=='diagnostic'])
    print(json.dumps({'reconciliation':'PASS','attempts':len(records),'usage':usage,'lifetime':lifetime,'recovery':recovery,'failures':failures},indent=2))

if __name__=='__main__':main()
