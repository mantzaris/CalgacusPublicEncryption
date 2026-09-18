#!/usr/bin/env python3
"""Fixed Stage 6 allocation on the same append-only lifetime ledger and lock."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger,amounts
from llm_stego_public_key.profile import canonical_json,validate_supported_profile
from run_smoke import execute,revision,validate_resume,write_new
from run_pilot import rows
ART=ROOT/'artifacts/stage6'
LIMITS={'seconds':14400,'tokens':200000,'cases':160}
FATAL={'implementation_failure','rank_numerical_divergence','timeout_resource_failure'}


def admit(usage,baseline,requested):
    amounts(requested)
    if any(usage[k]<baseline[k] or usage[k]-baseline[k]+requested[k]>LIMITS[k] for k in LIMITS):
        raise BudgetError('Full Stage 6 reservation does not fit the additional allocation')


class Stage6Ledger:
    def __init__(self,base,authorization):self.base,self.authorization=base,authorization
    def __getattr__(self,name):return getattr(self.base,name)
    def reserve(self,seconds,tokens,cases=1,**metadata):
        admit(self.usage(),self.authorization['baseline_usage'],{'seconds':seconds,'tokens':tokens,'cases':cases})
        return self.base.reserve(seconds,tokens,cases,allocation_id=self.authorization['allocation_id'],**metadata)


def allocation_check(a):
    assert a['additional_limits']==LIMITS and len(a['slots'])==150
    assert len({s['case_id'] for s in a['slots']})==150
    assert sum(s['kind']=='control' for s in a['slots'])==96
    assert sum(s['kind']=='encrypted' and s['stage6_phase']=='main_fixed' for s in a['slots'])==32
    assert sum(s['stage6_phase']=='baseline' for s in a['slots'])==8
    assert sum(s['kind']=='replay' for s in a['slots'])==8
    b=a['baseline_usage'];admit(b,b,a['all_full_reservations'])
    for s in a['slots']:
        # ASCII byte bound >= context token count; full observed text scoring capped at 512.
        p=json.loads((ROOT/s['profile_path']).read_text());validate_supported_profile(p)
        c=len(p['cover_contexts'][s['context_index']].encode())+1
        if s['kind']=='encrypted' and s['method']!='Calgacus':bound=3*(2*(68+s['payload_bytes']+(4 if s['method']=='L' else 0))+c)
        elif s['kind']=='control':bound=s['target_tokens']+512+2*c
        elif s['kind']=='prediction':bound=c+6
        elif s['kind']=='replay':bound=400+c # actual preselected 32-byte replays have smaller bounds below
        else:bound=2*264+4*512+3*c+3*(len(p['source_context'].encode())+1)
        if s['kind']=='replay' and '-n32-' in s['source_case_id']:bound=208+c
        assert bound<=s['reservation'][1],(s['case_id'],bound,s['reservation'])
    q={'seconds':45,'tokens':128,'cases':1};edge={k:b[k]+LIMITS[k]-q[k] for k in LIMITS};admit(edge,b,q)
    for k in LIMITS:
        over=dict(edge);over[k]+=1
        try:admit(over,b,q)
        except BudgetError:pass
        else:raise AssertionError('Over-limit admission '+k)
    print(json.dumps({'status':'PASS','scope':'150 fixed cases, complete reservations, conservative token bounds and three budget boundaries','totals':a['all_full_reservations'],'inference':False}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--allocation-check',action='store_true');args=p.parse_args()
    a=json.loads((ART/'allocation.json').read_text())
    if args.allocation_check:allocation_check(a);return
    code=revision()
    frozen=['artifacts/stage6/allocation.json','artifacts/stage6/TEST_ONLY_keys.json','artifacts/stage6/environment.json','docs/stage6_study_spec.md']
    if subprocess.check_output(['git','diff','HEAD','--',*frozen],cwd=ROOT):raise RuntimeError('Frozen inputs changed')
    for name in frozen:subprocess.check_call(['git','ls-files','--error-unmatch',name],cwd=ROOT,stdout=subprocess.DEVNULL)
    if hashlib.sha256((ROOT/a['analysis_spec_path']).read_bytes()).hexdigest()!=a['analysis_spec_sha256']:raise RuntimeError('Analysis specification mismatch')
    if (ART/'run_status.json').exists():raise RuntimeError('Stage 6 already stopped/completed; no implicit restart')
    auth=json.loads((ROOT/'configs/stage6/authorization.json').read_text())
    if hashlib.sha256(canonical_json(auth)).hexdigest()!=a['authorization_sha256']:raise BudgetError('Allocation authority mismatch')
    runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
    keys=json.loads((ART/'TEST_ONLY_keys.json').read_text())['keys']
    base=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',authorization=auth);ledger=Stage6Ledger(base,auth)
    status={'schema_version':1,'tested_code_commit':code,'skipped':[],'allocation_id':auth['allocation_id']}
    try:
        previous=[]
        for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix']:previous+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
        results=rows(ART/'cases.jsonl');validate_resume(base,previous+results)
        if results and any(r['tested_code_commit']!=code for r in results):raise RuntimeError('No pooling different implementations through implicit resume')
        known={r['case_id']:r for r in results}
        for slot in a['slots']:
            if slot['case_id'] in known:continue
            job={k:v for k,v in slot.items() if k not in ['reservation','key_index','source_case_id','payload_setting_bytes']}
            source=None
            if slot['kind']=='replay':
                source=known.get(slot['source_case_id'])
                if source is None or not source.get('authenticated_message_recovery'):
                    status['skipped'].append({'case_id':slot['case_id'],'reason':'Predetermined source did not recover; no substitution'});continue
                job['carrier_path']=source['evidence_dir']+'/carrier.txt'
            if 'key_index' in slot:
                key=keys[slot['key_index']];job['TEST_ONLY_private_key_hex']=key['TEST_ONLY_private_key_hex'];job['key_id']=key['key_id']
            if slot['kind'] not in ['prediction','replay']:
                prediction=known[f"qualification-predict-{slot['context_index']}"]
                path=ROOT/prediction['evidence_dir']/'public_prediction.json';raw=path.read_bytes()
                if json.loads(raw)!=prediction['prediction']:raise RuntimeError('Public prediction changed')
                job.update(prediction_path=str(path.relative_to(ROOT)),prediction_sha256=hashlib.sha256(raw).hexdigest())
            r=execute(ledger,job,runtime,code,artifact_root=ART,reservation=slot['reservation'],worker_script=ROOT/'scripts/gpu_stage6_worker.py',replay_source=source)
            results.append(r);known[r['case_id']]=r
            if (r['failure_category'] in FATAL or not all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified']) or r['exit_code']!=0):
                status['stop_reason']='Fatal execution/accounting/numerical/provenance gate: '+slot['case_id'];break
            if slot['stage6_phase']=='qualification' and not r['success']:
                status['stop_reason']='Qualification failed; no main study or retries: '+slot['case_id'];break
            if slot['kind']=='encrypted' and slot['method'] in ['L','F'] and r['failure_category'] in ['cryptographic_authentication_failure','framing_failure']:
                status['stop_reason']='Unexpected canonical rank16 receiver failure: '+slot['case_id'];break
        else:status['stop_reason']='Frozen 150-slot allocation completed; unused investigation allowance not spent'
    except (Exception,KeyboardInterrupt) as exc:
        status.update(stop_reason=type(exc).__name__+': '+str(exc),controller_exception=True)
    finally:
        records=rows(ART/'cases.jsonl');seen={r['case_id'] for r in records}|{x['case_id'] for x in status['skipped']}
        for slot in a['slots']:
            if slot['case_id'] not in seen:status['skipped'].append({'case_id':slot['case_id'],'reason':status['stop_reason']})
        status['lifetime_usage']=base.usage();status['stage6_usage']={k:base.usage()[k]-auth['baseline_usage'][k] for k in LIMITS}
        status['recorded_outcomes']=len(records);write_new(ART/'run_status.json',status);base.close();print(json.dumps(status),flush=True)

if __name__=='__main__':main()
