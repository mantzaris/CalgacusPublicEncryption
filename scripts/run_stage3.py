#!/usr/bin/env python3
"""Fixed Stage 3 allocation on the one authoritative project ledger. No retries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger,amounts
from llm_stego_public_key.profile import canonical_json,validate_rank16_profile
from run_smoke import execute,revision,validate_resume,write_new
from run_pilot import rows,replay_job
ART=ROOT/'artifacts/stage3_transport'
LIMITS={'seconds':1200,'tokens':8000,'cases':10}
FATAL={'implementation_failure','rank_numerical_divergence','timeout_resource_failure'}


def admit(usage,baseline,requested):
    amounts(requested)
    if any(usage[k]<baseline[k] or usage[k]-baseline[k]+requested[k]>LIMITS[k] for k in LIMITS):
        raise BudgetError('Full Stage 3 reservation does not fit additional ceilings')


class Stage3Ledger:
    def __init__(self,base,baseline): self.base,self.baseline=base,baseline
    def __getattr__(self,name): return getattr(self.base,name)
    def reserve(self,seconds,tokens,cases=1,**metadata):
        admit(self.usage(),self.baseline,{'seconds':seconds,'tokens':tokens,'cases':cases})
        return self.base.reserve(seconds,tokens,cases,**metadata)


def allocation_check(a):
    expected=[[140,900]]*2+[[120,750],[160,1300]]*2+[[80,450]]*2+[[100,900]]*2
    assert [s['reservation'] for s in a['slots']]==expected and a['additional_limits']==LIMITS
    assert len({s['case_id'] for s in a['slots']})==10
    b=a['baseline_usage'];q={'seconds':140,'tokens':900,'cases':1}
    at={k:b[k]+LIMITS[k]-q[k] for k in LIMITS};admit(at,b,q)
    for k in LIMITS:
        over=dict(at);over[k]+=1
        try: admit(over,b,q)
        except BudgetError: pass
        else: raise AssertionError('Exceeded '+k)
    print(json.dumps({'status':'PASS','checks':5,'scope':'fixed reservations, exact boundary, one-over each resource','inference':False}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--allocation-check',action='store_true');args=p.parse_args()
    a=json.loads((ART/'allocation.json').read_text())
    if args.allocation_check: allocation_check(a);return
    code=revision()
    frozen=[str((ART/n).relative_to(ROOT)) for n in ['allocation.json','budget_anchor.json','TEST_ONLY_keys.json','environment.json']]
    if subprocess.check_output(['git','diff','HEAD','--',*frozen],cwd=ROOT): raise RuntimeError('Frozen allocation changed')
    for path in frozen: subprocess.check_call(['git','ls-files','--error-unmatch',path],cwd=ROOT,stdout=subprocess.DEVNULL)
    if (ART/'run_status.json').exists(): raise RuntimeError('Qualification finished or stopped; no resumption')
    profile=json.loads((ROOT/'configs/public_utf8_rank16_v1.json').read_text());validate_rank16_profile(profile)
    if hashlib.sha256(canonical_json(profile)).hexdigest()!=a['profile_sha256']: raise RuntimeError('Profile provenance changed')
    runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
    anchor=json.loads((ART/'budget_anchor.json').read_text())
    if anchor['usage']!=a['baseline_usage']: raise BudgetError('Allocation/anchor mismatch')
    base=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',anchor=anchor);ledger=Stage3Ledger(base,a['baseline_usage'])
    keys={k['key_id']:k for k in json.loads((ART/'TEST_ONLY_keys.json').read_text())['keys']}
    status={'schema_version':1,'tested_code_commit':code,'split':'development_only_excluded_from_future_heldout','skipped':[]}
    try:
        previous=rows(ROOT/'artifacts/stage1/cases.jsonl')+rows(ROOT/'artifacts/stage2_pilot/cases.jsonl')
        results=rows(ART/'cases.jsonl');validate_resume(base,previous+results)
        if results or base.usage()!=a['baseline_usage']: raise BudgetError('Intervening/interrupted work; retain charges and review')
        for slot in a['slots']:
            source=None;family=slot['family']
            if family in ('fresh_replay','control'):
                source=next((r for r in results if r['kind']=='encrypted' and r.get('key_id')==slot['key_id'] and r.get('payload_bytes')==128 and r['success']),None)
                if source is None:
                    status['skipped'].append({'case_id':slot['case_id'],'reason':'No successful 128-byte source; no replacement'})
                    continue
            if family=='fixture':
                job={k:slot[k] for k in ['kind','case_id','fixture_source_attempt_id','envelope_hex','context_index']}
            elif family=='fresh_encrypted':
                job={k:slot[k] for k in ['kind','case_id','payload_hex','context_index','key_id']}
                job['TEST_ONLY_private_key_hex']=keys[slot['key_id']]['TEST_ONLY_private_key_hex']
            elif family=='fresh_replay': job=replay_job(slot,source,profile)
            else:
                job={'kind':'control','case_id':slot['case_id'],'context_index':profile['cover_contexts'].index(source['cover_context']),
                     'sampling_seed':slot['sampling_seed'],'target_tokens':source['carrier_tokens'],'matched_attempt_id':source['attempt_id']}
            job['profile_sha256']=a['profile_sha256']
            r=execute(ledger,job,runtime,code,artifact_root=ART,reservation=slot['reservation'],
                      replay_source=source if family=='fresh_replay' else None,worker_script=ROOT/'scripts/gpu_rank16_worker.py')
            results.append(r)
            if (r['failure_category'] in FATAL or not all(r.get(k) for k in ['gpu_verified','lease_verified','phase_meter_verified','provenance_verified'])
                or r['exit_code']!=0 or len({x.get('pid') for x in results})!=len(results)):
                status['stop_reason']='Fatal execution/provenance/numerical gate: '+slot['case_id'];break
            if family!='control' and not r['success']:
                status['stop_reason']='Qualification failure; no retry: '+slot['case_id']+' ('+str(r['failure_category'])+')';break
        else: status['stop_reason']='Fixed allocation exhausted; stop GPU work'
    except (Exception,KeyboardInterrupt) as exc:
        status.update(stop_reason=type(exc).__name__+': '+str(exc),controller_exception=True)
    finally:
        records=rows(ART/'cases.jsonl');known={r['case_id'] for r in records}|{s['case_id'] for s in status['skipped']}
        for slot in a['slots']:
            if slot['case_id'] not in known: status['skipped'].append({'case_id':slot['case_id'],'reason':status['stop_reason']})
        status['cumulative_usage']=base.usage();status['incremental_usage']={k:base.usage()[k]-a['baseline_usage'][k] for k in LIMITS}
        status['recorded_outcomes']=len(records);write_new(ART/'run_status.json',status);base.close();print(json.dumps(status),flush=True)

if __name__=='__main__':main()
