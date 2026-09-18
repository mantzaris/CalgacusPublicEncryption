#!/usr/bin/env python3
"""Stage 7 qualification/main controller using the shared lifetime governor."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger,amounts
from llm_stego_public_key.profile import canonical_json,validate_supported_profile
from run_smoke import execute,revision,validate_resume,write_new
from run_pilot import rows
ART=ROOT/'artifacts/stage7';LIMITS={'seconds':14400,'tokens':300000,'cases':128}
FATAL={'implementation_failure','rank_numerical_divergence','timeout_resource_failure','cryptographic_authentication_failure','framing_failure'}

def admit(usage,baseline,requested):
    amounts(requested)
    if any(usage[k]<baseline[k] or usage[k]-baseline[k]+requested[k]>LIMITS[k] for k in LIMITS):raise BudgetError('Complete Stage 7 reservation does not fit')

class Stage7Ledger:
    def __init__(self,base,auth):self.base,self.authorization=base,auth
    def __getattr__(self,n):return getattr(self.base,n)
    def reserve(self,seconds,tokens,cases=1,**metadata):
        admit(self.usage(),self.authorization['baseline_usage'],dict(seconds=seconds,tokens=tokens,cases=cases))
        return self.base.reserve(seconds,tokens,cases,allocation_id=self.authorization['allocation_id'],**metadata)

def allocation_check(a):
    assert a['additional_limits']==LIMITS and len(a['slots'])==110
    assert len({s['case_id'] for s in a['slots']})==110
    for s in a['slots']:
        p=json.loads((ROOT/s['profile_path']).read_text());validate_supported_profile(p)
        context=len(p['cover_contexts'][s['context_index']].encode())+1
        assert context+1536<=p['inference']['n_ctx'] and context<=64
        count=1536 if s['method']=='R' else 2*p['public_size_class']['envelope_bytes']
        if s['kind']=='encrypted':bound=3*(context+count)
        elif s['kind']=='fixture':bound=2*(context+count)
        elif s['kind']=='replay':bound=context+count
        else:bound=2*context+count+p['tokens']['max_tokens']
        assert bound<=s['reservation'][1],(s['case_id'],bound)
    b=a['baseline_usage'];q={'seconds':45,'tokens':128,'cases':1};edge={k:b[k]+LIMITS[k]-q[k] for k in LIMITS};admit(edge,b,q)
    for k in LIMITS:
        over=dict(edge);over[k]+=1
        try:admit(over,b,q)
        except BudgetError:pass
        else:raise AssertionError('Admission ceiling '+k)
    print(json.dumps({'status':'PASS','slots':110,'scope':'full reservations; conservative prompt+all-pass token bounds; context window; three allocation ceilings','inference':False}))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['qualification','main']);parser.add_argument('--allocation-check',action='store_true');args=parser.parse_args()
    a=json.loads((ART/'allocation.json').read_text())
    if args.allocation_check:allocation_check(a);return
    if args.phase is None:parser.error('--phase required')
    code=revision();phase=args.phase
    frozen=['artifacts/stage7/allocation.json','artifacts/stage7/TEST_ONLY_keys.json','artifacts/stage7/environment.json','docs/stage7_study_spec.md']
    if phase=='main':frozen.append('artifacts/stage7/main_release.json')
    for name in frozen:subprocess.check_call(['git','ls-files','--error-unmatch',name],cwd=ROOT,stdout=subprocess.DEVNULL)
    if subprocess.check_output(['git','diff','HEAD','--',*frozen],cwd=ROOT):raise RuntimeError('Frozen inputs changed')
    if hashlib.sha256((ROOT/a['analysis_spec_path']).read_bytes()).hexdigest()!=a['analysis_spec_sha256']:raise RuntimeError('Specification hash mismatch')
    status_path=ART/f'{phase}_status.json'
    if status_path.exists():raise RuntimeError('Phase already stopped; no retry authorization')
    if phase=='main':
        release=json.loads((ART/'main_release.json').read_text());qual=json.loads((ART/'qualification_status.json').read_text())
        if not qual.get('qualification_passed') or release['qualification_cases_sha256']!=hashlib.sha256((ART/'cases.jsonl').read_bytes()).hexdigest():raise RuntimeError('Qualification release mismatch')
        if release['decision']!='proceed_fixed_matrix':raise RuntimeError('Main release not granted')
    auth=json.loads((ROOT/'configs/stage7/authorization.json').read_text())
    if hashlib.sha256(canonical_json(auth)).hexdigest()!=a['authorization_sha256']:raise BudgetError('Authorization mismatch')
    keys=json.loads((ART/'TEST_ONLY_keys.json').read_text())['keys'];runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
    base=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',authorization=auth);ledger=Stage7Ledger(base,auth)
    status={'schema_version':1,'tested_code_commit':code,'phase':phase,'skipped':[],'allocation_id':auth['allocation_id']}
    slots=[s for s in a['slots'] if (s['stage7_phase']=='qualification')==(phase=='qualification')]
    try:
        history=[]
        for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix','stage6']:history+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
        results=rows(ART/'cases.jsonl');validate_resume(base,history+results);known={r['case_id']:r for r in results}
        for slot in slots:
            if slot['case_id'] in known:raise RuntimeError('Implicit re-execution/resume prohibited')
            job={k:v for k,v in slot.items() if k not in ['reservation','key_index','source_case_id','fallback_tokens']};source=None
            if slot['kind']=='replay':
                source=known.get(slot['source_case_id'])
                if not source or not source.get('authenticated_message_recovery'):
                    status['skipped'].append({'case_id':slot['case_id'],'reason':'Predetermined source unavailable; no substitution'});continue
                job['carrier_path']=source['evidence_dir']+'/carrier.txt'
            if slot['kind']=='control':
                source_setting=known[slot['associated_encrypted_case_id']]
                available=source_setting.get('wire_delivered') and source_setting.get('carrier_tokens')
                job['target_tokens']=source_setting['carrier_tokens'] if available else slot['fallback_tokens']
                job['length_assignment']='realized_delivered_length' if available else 'predeclared_failed_source_fallback'
            if 'key_index' in slot:
                key=keys[slot['key_index']];job.update(TEST_ONLY_private_key_hex=key['TEST_ONLY_private_key_hex'],key_id=key['key_id'])
            r=execute(ledger,job,runtime,code,artifact_root=ART,reservation=slot['reservation'],worker_script=ROOT/'scripts/gpu_stage7_worker.py',replay_source=source)
            known[r['case_id']]=r
            if r['failure_category'] in FATAL or not all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified']) or r['exit_code']!=0:
                status['stop_reason']='Fatal correctness/accounting/execution gate: '+slot['case_id'];break
            if slot['kind'] in ['encrypted','fixture'] and r['failure_category']=='tokenization_serialization_drift':
                status['stop_reason']='Canonical emission failed: '+slot['case_id'];break
        else:
            status['stop_reason']='Frozen phase completed; no replacements'
            if phase=='qualification':
                status['qualification_passed']=bool(known.get('qual-HPKE-32',{}).get('exact_recovery') and known.get('qual-replay-32',{}).get('exact_recovery') and known.get('qual-synthetic-32',{}).get('exact_envelope_recovery'))
                if not status['qualification_passed']:status['stop_reason']='No qualified meaningful small payload; comparative GPU study blocked'
    except (Exception,KeyboardInterrupt) as exc:status.update(stop_reason=type(exc).__name__+': '+str(exc),controller_exception=True)
    finally:
        records=rows(ART/'cases.jsonl');seen={r['case_id'] for r in records}|{r['case_id'] for r in status['skipped']}
        status['skipped'] += [{'case_id':s['case_id'],'reason':status['stop_reason']} for s in slots if s['case_id'] not in seen]
        status['lifetime_usage']=base.usage();status['stage7_usage']={k:base.usage()[k]-auth['baseline_usage'][k] for k in LIMITS}
        status['recorded_outcomes']=len(records);write_new(status_path,status);base.close();print(json.dumps(status),flush=True)

if __name__=='__main__':main()
