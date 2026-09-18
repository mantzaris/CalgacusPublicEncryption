#!/usr/bin/env python3
"""Stage 4 host-only asset checks and frozen public inputs; no model evaluation."""
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from prepare_pilot import digest
from run_smoke import validate_resume,write_new
from run_pilot import rows
from llm_stego_public_key.evaluation.budget import BudgetLedger
from llm_stego_public_key.profile import canonical_json,validate_rank16_profile,validate_supported_profile
ART=ROOT/'artifacts/stage4_prefix'


def main():
    if (ART/'allocation.json').exists(): raise RuntimeError('Stage 4 allocation already frozen')
    profile=json.loads((ROOT/'configs/public_utf8_rank16_v1.json').read_text());validate_rank16_profile(profile)
    baseline_profile=json.loads((ROOT/'configs/public_profile.json').read_text());validate_supported_profile(baseline_profile)
    assert all(profile[k]==baseline_profile[k] for k in ['model','backend','inference','hpke','record','cover_contexts'])
    runtime=json.loads((ROOT/'configs/local_runtime.json').read_text());site=Path(runtime['reused_site_packages']);model=Path(runtime['model_path'])
    csv=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,memory.total,driver_version','--format=csv,noheader,nounits'],text=True)
    devices=[dict(zip(['index','name','uuid','vram_mib','driver'],map(str.strip,line.split(',')))) for line in csv.splitlines()]
    selected=next((d for d in devices if d['uuid']==runtime['gpu_uuid']),None)
    if selected is None: raise RuntimeError('Configured GPU unavailable; no fallback')
    if digest(model)!=profile['model']['sha256']: raise RuntimeError('Model hash mismatch')
    import gguf
    reader=gguf.GGUFReader(str(model),'r');h=hashlib.sha256()
    for name,field in sorted(reader.fields.items()):
        if name.startswith('tokenizer.'):
            raw=name.encode();h.update(len(raw).to_bytes(4,'big')+raw)
            for part in field.parts:
                raw=part.tobytes();h.update(len(raw).to_bytes(8,'big')+raw)
    if h.hexdigest()!=profile['model']['tokenizer_sha256']: raise RuntimeError('Tokenizer hash mismatch')
    for name,expected in profile['backend']['native_library_sha256'].items():
        if digest(site/'llama_cpp/lib'/name)!=expected: raise RuntimeError('Backend identity mismatch: '+name)
    cuda=json.loads((ROOT/'manifests/environment.json').read_text())['cuda_libraries']
    for name,expected in cuda.items():
        if digest(site/name)!=expected: raise RuntimeError('CUDA binary mismatch: '+name)
    installed={d.metadata['Name'].lower().replace('_','-'):d.version for d in importlib.metadata.distributions(path=[str(site)])}
    required={'llama-cpp-python':profile['backend']['llama_cpp_python'],'numpy':profile['backend']['numpy'],**profile['backend']['cuda_packages']}
    if any(installed.get(k)!=v for k,v in required.items()): raise RuntimeError('Runtime version mismatch')
    stage3=rows(ROOT/'artifacts/stage3_transport/cases.jsonl')
    previous=rows(ROOT/'artifacts/stage1/cases.jsonl')+rows(ROOT/'artifacts/stage2_pilot/cases.jsonl')+stage3
    ledger=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',anchor=json.loads((ROOT/'artifacts/stage3_transport/budget_anchor.json').read_text()))
    try:
        validate_resume(ledger,previous);usage=ledger.usage();raw=ledger.path.read_bytes()
        write_new(ART/'budget_anchor.json',{'schema_version':1,'path':'artifacts/project_budget.jsonl','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'usage':usage})
        context_evidence=[];slots=[];profile_hash=hashlib.sha256(canonical_json(profile)).hexdigest()
        for c,cover in enumerate(profile['cover_contexts']):
            known=[r for r in stage3 if r['profile_sha256']==profile_hash and cover in r['public_context_token_ids']]
            ids=known[0]['public_context_token_ids'][cover]
            assert all(r['public_context_token_ids'][cover]==ids for r in known)
            count=len(ids)+6
            if count>64 or count>profile['inference']['n_ctx']: raise RuntimeError('Frozen context/six-token operation exceeds reservation')
            context_evidence.append({'context_index':c,'context':cover,'context_token_ids':ids,'six_token_evaluation_count':count,
                'basis':'retained public context tokenization, unchanged model/tokenizer/backend hashes; verified again by every worker'})
            carriers=[]
            for r in stage3:
                if r['kind'] in ('fixture','encrypted') and r['cover_context']==cover:
                    path=r['evidence_dir']+'/carrier.txt'
                    if digest(ROOT/path)!=r['transport_sha256']: raise RuntimeError('Historical carrier hash mismatch')
                    carriers.append(path)
            slots.append({'case_id':f'prefix-predict-c{c}','kind':'prediction','context_index':c,'historical_carrier_paths':carriers,
                          'expected_evaluated_tokens':count,'reservation':[45,64]})
        for c in range(3):
            for family in ('A','B','C'):
                for seed in (2026092101,2026092102):
                    slots.append({'case_id':f'prefix-c{c}-{family}-s{seed}','kind':'control','family':family,'context_index':c,
                                  'sampling_seed':seed,'expected_evaluated_tokens':context_evidence[c]['six_token_evaluation_count'],'reservation':[45,64]})
        write_new(ART/'allocation.json',{'schema_version':1,'starting_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'starting_working_tree':'clean before implementation','profile_sha256':profile_hash,'observer_id':'public_zero6_v1','baseline_usage':usage,
            'additional_limits':{'seconds':1000,'tokens':1400,'cases':21},'global_limits':{'seconds':7200,'tokens':25000,'cases':72},
            'slots':slots,'public_context_prelaunch_checks':context_evidence,'split':'development_only_excluded_from_future_heldout',
            'retries':0,'seeds':[2026092101,2026092102],'rng':'NumPy PCG64; reproducibility only, not cryptographic keys',
            'generators':{'A':'full-vocabulary temperature-one sampling','B':'temperature-one probabilities renormalized over unchanged first 16 admissible IDs','C':'uniform index in unchanged first 16 admissible IDs'},
            'sample_space':'six latent emissions followed by exact detokenization and UTF-8 tokenization, or explicit abort; all allocated attempts retained',
            'observer':'compare actual received first six token IDs only; invalid UTF-8 and insufficient tokens do not match; no full message-length or ciphertext/tag validation',
            'abort_policy':'candidate exhaustion or invalid text retained, counted as nonmatch in intention-to-generate denominator; runtime failure separately inconclusive and stops execution',
            'stop_policy':'stop on prediction failure, invariant/numerical, accounting, lease, timeout or provenance failure; retain ordinary serialization failures/candidate exhaustion without retries'})
    finally:ledger.close()
    write_new(ART/'environment.json',{'schema_version':1,'selected_gpu':selected,'gpu_inventory':devices,'runtime':runtime,'runtime_packages':required,
        'python':platform.python_version(),'platform':platform.platform(),'model_sha256':profile['model']['sha256'],'tokenizer_sha256':h.hexdigest(),
        'native_library_sha256':profile['backend']['native_library_sha256'],'cuda_library_sha256':cuda,
        'asset_checks':'PASS; existing frozen model/tokenizer/backend/CUDA identities matched','gpu_model_work_in_preparation':False})
    print(json.dumps({'asset_checks':'PASS','selected_gpu':selected,'baseline_usage':usage,'frozen_slots':len(slots),
        'context_plus_six_tokens':[c['six_token_evaluation_count'] for c in context_evidence],
        'all_full_reservations':{'seconds':45*21,'tokens':64*21,'cases':21}}),flush=True)

if __name__=='__main__':main()
