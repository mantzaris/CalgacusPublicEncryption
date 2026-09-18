#!/usr/bin/env python3
"""Fixed public-prefix allocation on the existing authoritative project ledger."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger,amounts
from llm_stego_public_key.profile import canonical_json,validate_rank16_profile
from run_smoke import execute,revision,validate_resume,write_new
from run_pilot import rows
ART=ROOT/'artifacts/stage4_prefix'
LIMITS={'seconds':1000,'tokens':1400,'cases':21}
FATAL={'implementation_failure','rank_numerical_divergence','timeout_resource_failure'}


def admit(usage,baseline,requested):
    amounts(requested)
    if any(usage[k]<baseline[k] or usage[k]-baseline[k]+requested[k]>LIMITS[k] for k in LIMITS):
        raise BudgetError('Full Stage 4 reservation does not fit additional ceilings')


class PrefixLedger:
    def __init__(self,base,baseline): self.base,self.baseline=base,baseline
    def __getattr__(self,name): return getattr(self.base,name)
    def reserve(self,seconds,tokens,cases=1,**metadata):
        admit(self.usage(),self.baseline,{'seconds':seconds,'tokens':tokens,'cases':cases})
        return self.base.reserve(seconds,tokens,cases,**metadata)


def allocation_check(a):
    assert a['additional_limits']==LIMITS and len(a['slots'])==21
    assert len({s['case_id'] for s in a['slots']})==21
    assert [s['kind'] for s in a['slots']]==['prediction']*3+['control']*18
    assert all(s['reservation']==[45,64] and s['expected_evaluated_tokens']<=64 for s in a['slots'])
    total={'seconds':945,'tokens':1344,'cases':21};b=a['baseline_usage'];admit(b,b,total)
    assert all(b[k]+total[k]<=a['global_limits'][k] for k in LIMITS)
    q={'seconds':45,'tokens':64,'cases':1};edge={k:b[k]+LIMITS[k]-q[k] for k in LIMITS};admit(edge,b,q)
    for k in LIMITS:
        over=dict(edge);over[k]+=1
        try: admit(over,b,q)
        except BudgetError: pass
        else: raise AssertionError('Over-limit admission: '+k)
    print(json.dumps({'status':'PASS','checks':5,'scope':'fixed allocation/full budget/context fit; exact boundary and one-over each ceiling','inference':False}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--allocation-check',action='store_true');args=p.parse_args()
    a=json.loads((ART/'allocation.json').read_text())
    if args.allocation_check: allocation_check(a);return
    code=revision();frozen=[str((ART/n).relative_to(ROOT)) for n in ['allocation.json','budget_anchor.json','environment.json']]
    if subprocess.check_output(['git','diff','HEAD','--',*frozen],cwd=ROOT): raise RuntimeError('Frozen allocation changed')
    for path in frozen: subprocess.check_call(['git','ls-files','--error-unmatch',path],cwd=ROOT,stdout=subprocess.DEVNULL)
    if (ART/'run_status.json').exists(): raise RuntimeError('Stage 4 already stopped/completed; no resumption')
    profile=json.loads((ROOT/'configs/public_utf8_rank16_v1.json').read_text());validate_rank16_profile(profile)
    if hashlib.sha256(canonical_json(profile)).hexdigest()!=a['profile_sha256']: raise RuntimeError('Profile identity mismatch')
    runtime=json.loads((ROOT/'configs/local_runtime.json').read_text());anchor=json.loads((ART/'budget_anchor.json').read_text())
    if anchor['usage']!=a['baseline_usage']: raise BudgetError('Baseline/anchor mismatch')
    base=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',anchor=anchor);ledger=PrefixLedger(base,a['baseline_usage'])
    status={'schema_version':1,'tested_code_commit':code,'split':'development_only_excluded_from_future_heldout','skipped':[]}
    try:
        previous=[]
        for folder in ['stage1','stage2_pilot','stage3_transport']: previous+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
        results=rows(ART/'cases.jsonl');validate_resume(base,previous+results)
        if results or base.usage()!=a['baseline_usage']: raise BudgetError('Interrupted/intervening work; no implicit resumption')
        for slot in a['slots']:
            job={k:v for k,v in slot.items() if k!='reservation'}
            job['profile_sha256']=a['profile_sha256']
            if slot['kind']=='control':
                predicted=next(r for r in results if r['kind']=='prediction' and r['context_index']==slot['context_index'])
                cache=ROOT/predicted['evidence_dir']/'public_prediction.json'
                raw=cache.read_bytes()
                if json.loads(raw)!=predicted['prediction']: raise RuntimeError('Public prediction provenance mismatch')
                job.update(prediction_path=str(cache.relative_to(ROOT)),prediction_sha256=hashlib.sha256(raw).hexdigest())
            r=execute(ledger,job,runtime,code,artifact_root=ART,reservation=slot['reservation'],worker_script=ROOT/'scripts/gpu_prefix_worker.py')
            results.append(r)
            if (r['failure_category'] in FATAL or not all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified'])
                or r['exit_code']!=0 or len({x.get('pid') for x in results})!=len(results)):
                status['stop_reason']='Fatal execution/accounting/numerical/provenance gate: '+slot['case_id'];break
            if slot['kind']=='prediction' and not r['success']:
                status['stop_reason']='Public prediction unavailable; no retries: '+slot['case_id'];break
        else: status['stop_reason']='Fixed 21-case allocation exhausted; stop GPU work'
    except (Exception,KeyboardInterrupt) as exc:
        status.update(stop_reason=type(exc).__name__+': '+str(exc),controller_exception=True)
    finally:
        records=rows(ART/'cases.jsonl');known={r['case_id'] for r in records}
        for slot in a['slots']:
            if slot['case_id'] not in known:status['skipped'].append({'case_id':slot['case_id'],'reason':status['stop_reason']})
        status['cumulative_usage']=base.usage();status['incremental_usage']={k:base.usage()[k]-a['baseline_usage'][k] for k in LIMITS}
        status['recorded_outcomes']=len(records);write_new(ART/'run_status.json',status);base.close();print(json.dumps(status),flush=True)

if __name__=='__main__':main()
