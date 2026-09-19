#!/usr/bin/env python3
"""One frozen Stage9 run on the existing parent ledger; no retry/restart path."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger,amounts,append_json
from llm_stego_public_key.profile import canonical_json,validate_supported_profile
from run_smoke import execute,revision,validate_resume,write_new
from run_pilot import rows
ART=ROOT/'artifacts/stage9';LIMITS={'seconds':8640,'tokens':120000,'cases':32}
FATAL={'implementation_failure','rank_numerical_divergence','timeout_resource_failure','cryptographic_authentication_failure','framing_failure','tokenization_serialization_drift'}

class Stage9Ledger:
    def __init__(self,base,auth):self.base,self.authorization=base,auth
    def __getattr__(self,n):return getattr(self.base,n)
    def reserve(self,seconds,tokens,cases=1,**metadata):
        return self.base.reserve(seconds,tokens,cases,allocation_id=self.authorization['allocation_id'],**metadata)

def allocation_check(a):
    assert a['additional_limits']==LIMITS and len(a['slots'])==22 and len({s['case_id'] for s in a['slots']})==22
    total=dict(seconds=0,tokens=0,cases=0)
    for s in a['slots']:
        p=json.loads((ROOT/s['profile_path']).read_text());validate_supported_profile(p)
        context=len(p['cover_contexts'][s['context_index']].encode())+1
        assert context+1984+1<=2048
        passes=3 if s['kind']=='encrypted' else 2 if s['kind']=='control' else 1
        assert passes*(context+1984)<=s['reservation'][1]
        total['seconds']+=s['reservation'][0];total['tokens']+=s['reservation'][1];total['cases']+=1
    for k in LIMITS:assert total[k]<=LIMITS[k] and total[k]+a['baseline_usage'][k]<=a['lifetime_limits'][k]
    print(json.dumps(dict(status='PASS',full_reservations=total,stage9_limits=LIMITS,inference=False)))
    return total

def paired_check(fixed,stop):
    a=json.loads((ROOT/fixed['trace_path']).read_text())['control_generation'];b=json.loads((ROOT/stop['trace_path']).read_text())['control_generation']
    n=min(len(a['advanced_ids']),len(b['advanced_ids']));error=None
    for i in range(n):
        for key,x,y in [('token',a['advanced_ids'][i],b['advanced_ids'][i]),('candidate_order',a['candidate_steps'][i]['ordered_ids_sha256'],b['candidate_steps'][i]['ordered_ids_sha256']),('integer_state',a['arithmetic_steps'][i],b['arithmetic_steps'][i])]:
            if x!=y:error=dict(position=i,field=key);break
        if error:break
    return dict(schema_version=1,fixed_attempt=fixed['attempt_id'],stop_attempt=stop['attempt_id'],common_tokens=n,common_prefix_agreement=error is None,first_divergence=error)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--allocation-check',action='store_true');args=parser.parse_args()
    a=json.loads((ART/'allocation.json').read_text());allocation_check(a)
    if args.allocation_check:return
    code=revision();status_path=ART/'status.json'
    if status_path.exists() or rows(ART/'cases.jsonl'):raise RuntimeError('Stopped/completed/partially executed namespace; no implicit restart')
    frozen=['artifacts/stage9/'+p for p in ['allocation.json','TEST_ONLY_keys.json','environment.json','context_window_check.json','historical_reanalysis.json']]+['docs/stage9_study_spec.md','docs/stage9_observer_contract.md']
    for p in frozen:subprocess.check_call(['git','ls-files','--error-unmatch',p],cwd=ROOT,stdout=subprocess.DEVNULL)
    if subprocess.check_output(['git','diff','HEAD','--',*frozen],cwd=ROOT):raise RuntimeError('Frozen inputs changed')
    if hashlib.sha256((ROOT/a['analysis_spec_path']).read_bytes()).hexdigest()!=a['analysis_spec_sha256']:raise RuntimeError('Specification changed')
    if hashlib.sha256((ROOT/'docs/stage9_observer_contract.md').read_bytes()).hexdigest()!=a['observer_contract_sha256']:raise RuntimeError('Observer contract changed')
    hist=json.loads((ART/'historical_reanalysis.json').read_text())['cases']
    for r in hist:
        for p,h in r['inputs_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise RuntimeError('Historical evidence changed')
    auth=json.loads((ROOT/'configs/stage9/authorization.json').read_text())
    if hashlib.sha256(canonical_json(auth)).hexdigest()!=a['authorization_sha256']:raise BudgetError('Authorization mismatch')
    keys=json.loads((ART/'TEST_ONLY_keys.json').read_text())['keys'];runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
    base=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',authorization=auth);ledger=Stage9Ledger(base,auth)
    status=dict(schema_version=1,tested_code_commit=code,skipped=[],allocation_id=auth['allocation_id'])
    try:
        history=[]
        for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix','stage6','stage7','stage8']:history+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
        validate_resume(base,history)
        if base.usage()!=auth['baseline_usage']:raise BudgetError('Intervening usage: frozen full allocation requires review')
        known={}
        for slot in a['slots']:
            job={k:v for k,v in slot.items() if k not in ['reservation','key_index','source_case_id','fallback_tokens','historical_source_case_id']};source=None
            if slot['kind']=='replay':
                source=known[slot['source_case_id']]
                if not source.get('authenticated_message_recovery'):
                    status['skipped'].append(dict(case_id=slot['case_id'],reason='Predetermined source unavailable; no replacement'));continue
                job['carrier_path']=source['evidence_dir']+'/carrier.txt'
            if slot['kind']=='control':
                source_r=known[slot['associated_encrypted_case_id']]
                available=source_r.get('wire_delivered') and source_r.get('carrier_tokens')
                job['target_tokens']=1984 if slot['family']=='B-stop' else source_r['carrier_tokens'] if available else slot['fallback_tokens']
                job['length_assignment']='first_stable_target_or_ceiling' if slot['family']=='B-stop' else 'delivered_R_length' if available else 'predeclared1984_fallback'
            if 'key_index' in slot:
                key=keys[slot['key_index']];job.update(TEST_ONLY_private_key_hex=key['TEST_ONLY_private_key_hex'],key_id=key['key_id'])
            r=execute(ledger,job,runtime,code,artifact_root=ART,reservation=slot['reservation'],worker_script=ROOT/'scripts/gpu_stage9_worker.py',replay_source=source)
            known[r['case_id']]=r
            print(json.dumps({k:r.get(k) for k in ['case_id','success','failure_category','carrier_tokens','generated_tokens','job_elapsed_seconds','charged_tokens']}),flush=True)
            if r['failure_category'] in FATAL or not all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified','context_window_verified']) or r['exit_code']!=0:
                status['stop_reason']='Fatal execution/correctness gate: '+slot['case_id'];break
            if slot['kind']=='historical_prefix':
                old=next(x for x in hist if x['case_id']==slot['historical_source_case_id'])
                expected=dict(old['predicates'],ends_at_first_completion=True)
                observed=r.get('observer',{})
                fields=['stable_target_reached','first_completion_token','ends_at_first_completion','filler_consistent','canonical_replay_consistent','kem_canonical','envelope_sha256']
                differences={k:[expected[k],observed.get(k)] for k in fields if expected[k]!=observed.get(k)}
                append_json(ART/'historical_live_checks.jsonl',dict(case_id=r['case_id'],attempt_id=r['attempt_id'],agreement=not differences,differences=differences))
                if differences:status['stop_reason']='Unexpected historical public prefix divergence';break
            if slot.get('family')=='B-stop':
                check=paired_check(known['B-fixed-c'+str(slot['context_index'])],r);append_json(ART/'paired_checks.jsonl',check)
                if not check['common_prefix_agreement']:status['stop_reason']='Unexplained paired control trajectory divergence';break
        else:status['stop_reason']='Frozen Stage9 study completed'
    except (Exception,KeyboardInterrupt) as exc:status.update(stop_reason=type(exc).__name__+': '+str(exc),controller_exception=True)
    finally:
        records=rows(ART/'cases.jsonl');seen={r['case_id'] for r in records}|{r['case_id'] for r in status['skipped']}
        status['skipped'] += [dict(case_id=s['case_id'],reason=status['stop_reason']) for s in a['slots'] if s['case_id'] not in seen]
        status['lifetime_usage']=base.usage();status['stage9_usage']={k:base.usage()[k]-auth['baseline_usage'][k] for k in LIMITS};status['recorded_outcomes']=len(records)
        write_new(status_path,status);base.close();print(json.dumps(status),flush=True)

if __name__=='__main__':main()
