#!/usr/bin/env python3
"""One-shot host preparation; verifies existing assets, never loads/evaluates a model."""
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
from llm_stego_public_key.cryptography.hpke import generate_key_pair,deserialize
from llm_stego_public_key.evaluation.budget import BudgetLedger
from llm_stego_public_key.profile import canonical_json,validate_rank16_profile,validate_supported_profile
ART=ROOT/'artifacts/stage3_transport'


def main():
    if (ART/'allocation.json').exists(): raise RuntimeError('Frozen allocation already exists')
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
    old=rows(ROOT/'artifacts/stage1/cases.jsonl');prior_rows=old+rows(ROOT/'artifacts/stage2_pilot/cases.jsonl')
    ledger=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',anchor=json.loads((ROOT/'artifacts/stage2_pilot/migration.json').read_text()))
    try:
        validate_resume(ledger,prior_rows);usage=ledger.usage();raw=ledger.path.read_bytes()
        anchor={'schema_version':1,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'usage':usage,'path':'artifacts/project_budget.jsonl'}
        write_new(ART/'budget_anchor.json',anchor)
        keys=[]
        for u in range(2):
            sk,pk=generate_key_pair();keys.append({'key_id':f'rank16-{u}','TEST_ONLY_private_key_hex':sk.hex(),'public_key_hex':pk.hex()})
        write_new(ART/'TEST_ONLY_keys.json',{'schema_version':1,'warning':'PUBLIC INSECURE DEVELOPMENT TEST KEYS; never use for real data','keys':keys})
        slots=[]
        for i,aid in enumerate(['12de85ea-3e3e-4a4a-8997-27e551978366','21732f7e-11f4-48da-8b5c-2f7b622a7770']):
            source=next(r for r in old if r['attempt_id']==aid);envelope=deserialize(source['serialized_base64'])
            assert hashlib.sha256(envelope).hexdigest()==source['envelope_sha256']
            slots.append({'case_id':f'rank16-fixture-{i}','family':'fixture','kind':'fixture','fixture_source_attempt_id':aid,
                          'envelope_hex':envelope.hex(),'envelope_sha256':source['envelope_sha256'],
                          'context_index':profile['cover_contexts'].index(source['cover_context']),
                          'reservation':[140,900],'historical_carrier_tokens':len(source['encoder_trace']['carrier_ids'])})
        for u,n,context in [(0,32,0),(0,128,1),(1,32,2),(1,128,0)]:
            slots.append({'case_id':f'rank16-k{u}-n{n}','family':'fresh_encrypted','kind':'encrypted','key_id':f'rank16-{u}',
                          'payload_bytes':n,'payload_hex':bytes((193+31*u+11*j+n)%256 for j in range(n)).hex(),
                          'context_index':context,'reservation':[120,750] if n==32 else [160,1300]})
        for u in range(2):
            slots.append({'case_id':f'rank16-replay-{u}','family':'fresh_replay','kind':'replay','key_id':f'rank16-{u}','reservation':[80,450]})
        for u in range(2):
            slots.append({'case_id':f'rank16-control-{u}','family':'control','kind':'control','key_id':f'rank16-{u}',
                          'sampling_seed':2026092001+u,'reservation':[100,900]})
        write_new(ART/'allocation.json',{'schema_version':1,'starting_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                'starting_working_tree':'clean before implementation','profile_sha256':hashlib.sha256(canonical_json(profile)).hexdigest(),
                'baseline_usage':usage,'additional_limits':{'seconds':1200,'tokens':8000,'cases':10},
                'global_limits':{'seconds':7200,'tokens':25000,'cases':72},'slots':slots,
                'split':'development_only_excluded_from_future_heldout','retries':0,
                'stop_policy':'fixture or non-control failure stops qualification; control framing rejection expected; fatal execution/numerical/invariant failures stop all GPU work',
                'replay_selection':'128-byte success for each key only; no substitutions',
                'controls':'context and emitted token count of new 128-byte carrier for same key; no fallback',
                'payload_formula':'byte j = (193 + 31*u + 11*j + n) mod 256',
                'crypto_randomness':'fresh OS/library recipient keys, HPKE ephemeral randomness and 16-byte message IDs',
                'cpu_scope':'only focused new-codec contracts and fixed-allocation arithmetic; no broad suite'})
    finally: ledger.close()
    helper_paths=['../ImageCalgacus/imagecalgacus/text_backend.py','../ImageCalgacus/imagecalgacus/fixed_rank.py','../llm-rankcloak/rankcloak/model_io.py','../llm-rankcloak/rankcloak/revision_runner.py']
    helpers={p:{'sha256':digest(ROOT/p)} for p in helper_paths}
    for repo in ['../ImageCalgacus','../llm-rankcloak']:
        helpers[repo]={'commit':subprocess.check_output(['git','-C',str(ROOT/repo),'rev-parse','HEAD'],text=True).strip(),
                       'tracked_working_tree':subprocess.check_output(['git','-C',str(ROOT/repo),'status','--short','--untracked-files=no'],text=True)}
    write_new(ART/'environment.json',{'schema_version':1,'selected_gpu':selected,'gpu_inventory':devices,'runtime':runtime,'runtime_packages':required,
               'python':platform.python_version(),'platform':platform.platform(),'model_sha256':profile['model']['sha256'],'tokenizer_sha256':h.hexdigest(),
               'native_library_sha256':profile['backend']['native_library_sha256'],'cuda_library_sha256':cuda,'local_helpers':helpers,
               'asset_checks':'PASS; all existing hashes matched','gpu_model_work_in_preparation':False})
    print(json.dumps({'asset_checks':'PASS','selected_gpu':selected,'baseline_usage':usage,'frozen_slots':len(slots)}),flush=True)

if __name__=='__main__':main()
