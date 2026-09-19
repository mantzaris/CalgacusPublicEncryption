#!/usr/bin/env python3
"""Stage 9 host-only asset checks and frozen public inputs; no model evaluation."""
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
from llm_stego_public_key.cryptography.hpke import generate_key_pair
from llm_stego_public_key.profile import canonical_json,validate_rank16_profile,validate_supported_profile
ART=ROOT/'artifacts/stage9'


def main():
    if (ART/'allocation.json').exists(): raise RuntimeError('Stage 9 allocation already frozen')
    profile=json.loads((ROOT/'configs/stage9/R32.json').read_text());validate_supported_profile(profile)
    baseline_profile=json.loads((ROOT/'configs/public_profile.json').read_text());validate_supported_profile(baseline_profile)
    assert all(profile[k]==baseline_profile[k] for k in ['model','backend','inference','hpke','record'])
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
    authorization=json.loads((ROOT/'configs/stage9/authorization.json').read_text())
    previous=[]
    for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix','stage6','stage7','stage8']:
        previous+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
    # Preparation is read-only with respect to the historical ledger/checkpoint.
    ledger=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',authorization=json.loads((ROOT/'configs/stage7/authorization.json').read_text()))
    try:
        validate_resume(ledger,previous)
        if ledger.usage()!=authorization['baseline_usage']: raise RuntimeError('Intervening project GPU work')
        raw=ledger.path.read_bytes();old=authorization['previous_checkpoint']
        if len(raw)!=old['bytes'] or hashlib.sha256(raw).hexdigest()!=old['sha256']: raise RuntimeError('Historical checkpoint mismatch')
    finally: ledger.close()
    contexts=profile['cover_contexts']
    historical_contexts=set()
    for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix','stage6','stage7','stage8']:
        for row in rows(ROOT/'artifacts'/folder/'cases.jsonl'):
            if row.get('cover_context'):historical_contexts.add(row['cover_context'])
    assert not set(contexts)&historical_contexts
    keys=[]
    for i in range(6):
        sk,pk=generate_key_pair();keys.append({'key_id':f'STAGE9_TEST_ONLY_{i}','TEST_ONLY_private_key_hex':sk.hex(),'public_key_hex':pk.hex()})
    write_new(ART/'TEST_ONLY_keys.json',{'schema_version':1,'warning':'Public TEST ONLY synthetic fixtures','keys':keys})
    slots=[]
    def slot(case,kind,c,res,phase,path='configs/stage9/R32.json'):
        p=json.loads((ROOT/path).read_text());validate_supported_profile(p)
        v=dict(case_id=case,kind=kind,method='R',context_index=c,reservation=res,stage9_phase=phase,profile_path=path,
            profile_sha256=hashlib.sha256(canonical_json(p)).hexdigest(),split='retrospective_derived_historical_prefix' if phase=='retrospective' else 'stage9_prospective_development_not_final_test')
        slots.append(v);return v
    history=json.loads((ART/'historical_reanalysis.json').read_text())['cases']
    for c in [1,3]:
        old=next(r for r in history if r['case_id']==f'control-R-c{c}-n32-r0-B')
        q=slot('historical-prefix-c'+str(c),'historical_prefix',c,[210,2100],'retrospective',old['profile_path'])
        q.update(original_carrier_path=old['wire_path'],original_carrier_sha256=old['inputs_sha256'][old['wire_path']],prefix_tokens=old['predicates']['first_completion_token'],historical_source_case_id=old['case_id'])
    for c in range(6):
        data=hashlib.shake_256(f'ICISSP2027 Stage9 binary context={c}'.encode()).digest(32)
        q=slot(f'R-c{c}','encrypted',c,[540,6200],'prospective');q.update(payload_hex=data.hex(),payload_sha256=hashlib.sha256(data).hexdigest(),payload_bytes=32,key_index=c,pair_id=f'c{c}')
        for family in ['B-fixed','B-stop']:
            q=slot(f'{family}-c{c}','control',c,[360,4200],'prospective');q.update(pair_id=f'c{c}',family=family,sampling_seed=202609210000+c,associated_encrypted_case_id=f'R-c{c}',fallback_tokens=1984)
    for c in [0,3]:
        q=slot(f'replay-R-c{c}','replay',c,[210,2100],'fresh_receiver');q.update(source_case_id=f'R-c{c}',key_index=c)
    write_new(ART/'allocation.json',dict(schema_version=1,starting_commit=authorization['starting_commit'],baseline_usage=authorization['baseline_usage'],
        additional_limits=authorization['additional_limits'],lifetime_limits=authorization['lifetime_limits'],authorization_sha256=hashlib.sha256(canonical_json(authorization)).hexdigest(),
        slots=slots,analysis_spec_path='docs/stage9_study_spec.md',analysis_spec_sha256=digest(ROOT/'docs/stage9_study_spec.md'),observer_contract_sha256=digest(ROOT/'docs/stage9_observer_contract.md'),retries=0))
    write_new(ART/'environment.json',{'schema_version':1,'selected_gpu':selected,'gpu_inventory':devices,'runtime':runtime,'runtime_packages':required,
       'python':platform.python_version(),'platform':platform.platform(),'model_sha256':profile['model']['sha256'],'tokenizer_sha256':h.hexdigest(),
       'native_library_sha256':profile['backend']['native_library_sha256'],'cuda_library_sha256':cuda,
       'crypto_dependencies':{x:importlib.metadata.version(x) for x in ['pyhpke','cryptography']},'asset_checks':'PASS; no model inference'})
    print(json.dumps({'asset_checks':'PASS','gpu':selected,'frozen_slots':len(slots),'baseline_usage':authorization['baseline_usage']}))

if __name__=='__main__':main()
