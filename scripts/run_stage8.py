#!/usr/bin/env python3
"""Fixed new namespace; historical statuses and attempts are never restarted."""
import argparse,base64,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger,amounts,append_json
from llm_stego_public_key.profile import canonical_json,validate_supported_profile
from run_smoke import execute,revision,validate_resume,write_new
from run_pilot import rows
ART=ROOT/'artifacts/stage8';LIMITS={'seconds':10800,'tokens':230000,'cases':88}
FATAL={'implementation_failure','rank_numerical_divergence','timeout_resource_failure','cryptographic_authentication_failure','framing_failure'}

def admit(usage,baseline,requested):
    amounts(requested)
    if any(usage[k]<baseline[k] or usage[k]-baseline[k]+requested[k]>LIMITS[k] for k in LIMITS):raise BudgetError('Complete Stage8 reservation does not fit')

class Stage8Ledger:
    def __init__(self,base,auth):self.base,self.authorization=base,auth
    def __getattr__(self,n):return getattr(self.base,n)
    def reserve(self,seconds,tokens,cases=1,**metadata):
        admit(self.usage(),self.authorization['baseline_usage'],dict(seconds=seconds,tokens=tokens,cases=cases))
        return self.base.reserve(seconds,tokens,cases,allocation_id=self.authorization['allocation_id'],**metadata)

def allocation_check(a):
    assert a['additional_limits']==LIMITS and len(a['slots'])==80 and len({s['case_id'] for s in a['slots']})==80
    for s in a['slots']:
        p=json.loads((ROOT/s['profile_path']).read_text());validate_supported_profile(p)
        context=len(p['cover_contexts'][s['context_index']].encode())+1;assert context+1984+1<=2048
        count=1984 if s['method']=='R' else 2*p['public_size_class']['envelope_bytes']
        bound=(3*(context+count) if s['kind']=='encrypted' else 2*(context+count) if s['kind']=='fixture' else context+count if s['kind']=='replay' else 2*context+count+p['tokens']['max_tokens'])
        assert bound<=s['reservation'][1],(s['case_id'],bound)
    b=a['baseline_usage'];q={'seconds':45,'tokens':128,'cases':1};edge={k:b[k]+LIMITS[k]-q[k] for k in LIMITS};admit(edge,b,q)
    for k in LIMITS:
        over=dict(edge);over[k]+=1
        try:admit(over,b,q)
        except BudgetError:pass
        else:raise AssertionError('Ceiling failed: '+k)
    print(json.dumps({'status':'PASS','slots':80,'ceiling':1984,'checks':'complete token reservations; context+extra position; three allocation boundaries','inference':False}))

def prefix_check(record,old):
    original=json.loads((ROOT/old['trace_path']).read_text())['encode']
    current=json.loads((ROOT/record['trace_path']).read_text())['encode'];n=len(original['advanced_ids'])
    divergence=None
    for i in range(n):
        for field,a,b in [('token_id',original['advanced_ids'][i],current.get('advanced_ids',[])[i] if i<len(current.get('advanced_ids',[])) else None),
            ('candidate_order',original['candidate_steps'][i]['ordered_ids_sha256'],current['candidate_steps'][i]['ordered_ids_sha256'] if i<len(current.get('candidate_steps',[])) else None),
            ('arithmetic_state_and_frequencies',original['arithmetic_steps'][i],current['arithmetic_steps'][i] if i<len(current.get('arithmetic_steps',[])) else None)]:
            if a!=b:divergence={'position':i,'field':field,'expected':a,'actual':b};break
        if divergence:break
    return {'case_id':record['case_id'],'attempt_id':record['attempt_id'],'historical_attempt_id':old['attempt_id'],'compared_tokens':n,'prefix_agreement':divergence is None,'first_divergence':divergence}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['diagnostic','main']);parser.add_argument('--allocation-check',action='store_true');args=parser.parse_args()
    a=json.loads((ART/'allocation.json').read_text())
    if args.allocation_check:allocation_check(a);return
    if args.phase is None:parser.error('--phase required')
    phase=args.phase;code=revision();status_path=ART/f'{phase}_status.json'
    if status_path.exists():raise RuntimeError('Stage8 phase stopped/completed; no implicit restart')
    frozen=['artifacts/stage8/allocation.json','artifacts/stage8/TEST_ONLY_keys.json','artifacts/stage8/environment.json','artifacts/stage8/context_window_check.json','docs/stage8_study_spec.md','artifacts/stage8/historical_diagnosis.json']
    if phase=='main':frozen.append('artifacts/stage8/main_release.json')
    for name in frozen:subprocess.check_call(['git','ls-files','--error-unmatch',name],cwd=ROOT,stdout=subprocess.DEVNULL)
    if subprocess.check_output(['git','diff','HEAD','--',*frozen],cwd=ROOT):raise RuntimeError('Frozen inputs changed')
    if hashlib.sha256((ROOT/a['analysis_spec_path']).read_bytes()).hexdigest()!=a['analysis_spec_sha256']:raise RuntimeError('Analysis specification changed')
    diagnosis=json.loads((ART/'historical_diagnosis.json').read_text())
    for case in diagnosis['cases']:
        for path,digest in case['inputs_sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise RuntimeError('Historical source artifact changed')
    slots=[s for s in a['slots'] if (s['stage8_phase']=='diagnostic')==(phase=='diagnostic')]
    if phase=='main':
        release=json.loads((ART/'main_release.json').read_text());diag=json.loads((ART/'diagnostic_status.json').read_text())
        if not diag.get('qualification_passed') or release['diagnostic_cases_sha256']!=hashlib.sha256((ART/'cases.jsonl').read_bytes()).hexdigest():raise RuntimeError('Diagnostic release mismatch')
        if release['decision']!='proceed_fixed_matrix' or release['repetitions'] not in [1,2]:raise RuntimeError('No valid main release')
        slots=[s for s in slots if s.get('repetition',0)<release['repetitions']]
        if [s['case_id'] for s in slots]!=release['selected_case_ids']:raise RuntimeError('Main allocation selection mismatch')
    auth=json.loads((ROOT/'configs/stage8/authorization.json').read_text())
    if hashlib.sha256(canonical_json(auth)).hexdigest()!=a['authorization_sha256']:raise BudgetError('Authorization mismatch')
    keys=json.loads((ART/'TEST_ONLY_keys.json').read_text())['keys'];runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
    oldrows=rows(ROOT/'artifacts/stage7/cases.jsonl');oldbyid={r['attempt_id']:r for r in oldrows}
    base=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',authorization=auth);ledger=Stage8Ledger(base,auth)
    status={'schema_version':1,'phase':phase,'tested_code_commit':code,'skipped':[],'allocation_id':auth['allocation_id'],'qualification_passed':False}
    try:
        history=[]
        for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix','stage6','stage7']:history+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
        results=rows(ART/'cases.jsonl');validate_resume(base,history+results);known={r['case_id']:r for r in results};diagnostic_checks=[]
        for slot in slots:
            if slot['case_id'] in known:raise RuntimeError('No implicit attempt re-execution')
            job={k:v for k,v in slot.items() if k not in ['reservation','key_index','source_case_id','fallback_tokens','historical_attempt_id']};source=None;old=None
            if slot['stage8_phase']=='diagnostic':
                old=oldbyid[slot['historical_attempt_id']];oldjob=json.loads((ROOT/old['evidence_dir']/'input.json').read_text())
                if old['kind']=='encrypted':
                    job['original_binding_profile_path']=oldjob['profile_path'];job['TEST_ONLY_private_key_hex']=oldjob['TEST_ONLY_private_key_hex']
                if slot['kind']=='fixture':
                    job['historical_envelope_hex']=base64.b64decode(old['serialized_base64']).hex() if old['kind']=='encrypted' else oldjob['synthetic_envelope_hex']
                elif not any(r.get('original_binding_authenticated') and r.get('exact_envelope_recovery') for r in known.values()):
                    status['stop_reason']='Neither historical HPKE packet completed at1984; stop GPU work';break
            if slot['kind']=='replay':
                source=known.get(slot['source_case_id'])
                available=source and (source.get('exact_envelope_recovery') if phase=='diagnostic' else source.get('authenticated_message_recovery'))
                if not available:
                    status['skipped'].append({'case_id':slot['case_id'],'reason':'Predetermined source unavailable; no replacement'});continue
                job['carrier_path']=source['evidence_dir']+'/carrier.txt'
                if phase=='diagnostic':source=dict(source,payload_sha256=old['payload_sha256'] if old['kind']=='encrypted' else old['envelope_sha256'])
            if slot['kind']=='control':
                associated=known[slot['associated_encrypted_case_id']];available=associated.get('wire_delivered') and associated.get('carrier_tokens')
                job['target_tokens']=associated['carrier_tokens'] if available else slot['fallback_tokens'];job['length_assignment']='realized_delivered_length' if available else 'predeclared_failed_source_fallback'
            if 'key_index' in slot:
                key=keys[slot['key_index']];job.update(TEST_ONLY_private_key_hex=key['TEST_ONLY_private_key_hex'],key_id=key['key_id'])
            r=execute(ledger,job,runtime,code,artifact_root=ART,reservation=slot['reservation'],worker_script=ROOT/'scripts/gpu_stage8_worker.py',replay_source=source)
            known[r['case_id']]=r
            if r['failure_category'] in FATAL or not all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified','context_window_verified']) or r['exit_code']!=0:
                status['stop_reason']='Fatal correctness/accounting/execution gate: '+slot['case_id'];break
            if slot['kind'] in ['encrypted','fixture'] and r['failure_category']=='tokenization_serialization_drift':status['stop_reason']='Canonical emission invariant failed';break
            if slot['kind']=='fixture':
                check=prefix_check(r,old);diagnostic_checks.append(check);append_json(ART/'diagnostic_checks.jsonl',check)
                if not check['prefix_agreement']:status['stop_reason']='Historical prefix divergence; stop before interpretation';break
                if r.get('original_binding_authenticated') and r['recovered_sha256']!=old['payload_sha256']:status['stop_reason']='Authenticated historical payload mismatch';break
            if phase=='diagnostic' and slot['kind']=='replay':
                agreement=r.get('recovered_envelope_sha256')==old['envelope_sha256']
                check={'case_id':r['case_id'],'attempt_id':r['attempt_id'],'envelope_hash_agreement':agreement,'original_binding_authenticated':r.get('original_binding_authenticated',False),'payload_hash_agreement':r.get('recovered_sha256')==old.get('payload_sha256') if old['kind']=='encrypted' else None}
                append_json(ART/'diagnostic_checks.jsonl',check)
                if not agreement or (old['kind']=='encrypted' and not check['payload_hash_agreement']):status['stop_reason']='Independent diagnostic receiver mismatch';break
        else:
            status['stop_reason']='Frozen phase completed'
            if phase=='diagnostic':status['qualification_passed']=all(x['prefix_agreement'] for x in diagnostic_checks) and len(diagnostic_checks)==4 and any(r['kind']=='replay' and r.get('original_binding_authenticated') and r.get('exact_recovery') for r in known.values())
    except (Exception,KeyboardInterrupt) as exc:status.update(stop_reason=type(exc).__name__+': '+str(exc),controller_exception=True)
    finally:
        records=rows(ART/'cases.jsonl');seen={r['case_id'] for r in records}|{r['case_id'] for r in status['skipped']}
        status['skipped'] += [{'case_id':s['case_id'],'reason':status['stop_reason']} for s in slots if s['case_id'] not in seen]
        status['lifetime_usage']=base.usage();status['stage8_usage']={k:base.usage()[k]-auth['baseline_usage'][k] for k in LIMITS};status['recorded_outcomes']=len(records)
        write_new(status_path,status);base.close();print(json.dumps(status),flush=True)

if __name__=='__main__':main()
