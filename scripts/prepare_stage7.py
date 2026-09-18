#!/usr/bin/env python3
"""Stage 7 host-only asset checks and frozen public inputs; no model evaluation."""
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
ART=ROOT/'artifacts/stage7'


def main():
    if (ART/'allocation.json').exists(): raise RuntimeError('Stage 7 allocation already frozen')
    profile=json.loads((ROOT/'configs/stage7/R32.json').read_text());validate_supported_profile(profile)
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
    authorization=json.loads((ROOT/'configs/stage7/authorization.json').read_text())
    previous=[]
    for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix','stage6']:
        previous+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
    # Preparation is read-only with respect to the historical ledger/checkpoint.
    ledger=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',authorization=json.loads((ROOT/'configs/stage6/authorization.json').read_text()))
    try:
        validate_resume(ledger,previous)
        if ledger.usage()!=authorization['baseline_usage']: raise RuntimeError('Intervening project GPU work')
        raw=ledger.path.read_bytes();old=authorization['previous_checkpoint']
        if len(raw)!=old['bytes'] or hashlib.sha256(raw).hexdigest()!=old['sha256']: raise RuntimeError('Historical checkpoint mismatch')
    finally: ledger.close()
    profiles={f'{m}{n}':json.loads((ROOT/f'configs/stage7/{m}{n}.json').read_text()) for m in ['F','R'] for n in [32,128]}
    for p in profiles.values(): validate_supported_profile(p)
    if any(len(c.encode('utf-8'))+1>64 for c in profile['cover_contexts']): raise RuntimeError('Conservative context bound exceeded')
    if set(profile['cover_contexts']) & set(baseline_profile['cover_contexts']): raise RuntimeError('Contexts not new')
    keys=[]
    for i in range(9):
        sk,pk=generate_key_pair();keys.append({'key_id':f'STAGE7_TEST_ONLY_{i}','TEST_ONLY_private_key_hex':sk.hex(),'public_key_hex':pk.hex()})
    write_new(ART/'TEST_ONLY_keys.json',{'schema_version':1,'warning':'TEST ONLY public synthetic experiment fixtures','keys':keys})
    slots=[]
    def slot(case,kind,method,c,n,res,phase):
        p=profiles[f'{method}{n}']
        v={'case_id':case,'kind':kind,'method':method,'context_index':c,'reservation':res,'stage7_phase':phase,
           'profile_path':f'configs/stage7/{method}{n}.json','profile_sha256':hashlib.sha256(canonical_json(p)).hexdigest(),
           'split':'stage7_qualification_development_only' if phase=='qualification' else 'stage7_prospective_fixed_not_final_test'}
        slots.append(v);return v
    for n,c in [(32,0),(128,1)]:
        q=slot(f'qual-synthetic-{n}','fixture','R',c,n,[300,3300],'qualification')
        data=hashlib.shake_256(f'Stage7 synthetic packet {n}'.encode()).digest(68+n)
        q.update(synthetic_envelope_hex=data.hex(),synthetic_envelope_sha256=hashlib.sha256(data).hexdigest())
    for n,c in [(32,2),(128,3)]:
        q=slot(f'qual-HPKE-{n}','encrypted','R',c,n,[420,5000],'qualification')
        q.update(payload_hex=hashlib.shake_256(f'Stage7 qualification HPKE {n}'.encode()).digest(n).hex(),payload_bytes=n,key_index=8)
    for n,c in [(32,2),(128,3)]:
        q=slot(f'qual-replay-{n}','replay','R',c,n,[180,1650],'qualification')
        q.update(source_case_id=f'qual-HPKE-{n}',key_index=8)
    encrypted=[]
    for c in range(4):
      for n in [32,128]:
       for rep in range(2):
        pair=f'c{c}-n{n}-r{rep}'
        data=hashlib.shake_256(f'ICISSP2027 Stage7 binary c={c} n={n} r={rep}'.encode()).digest(n)
        methods=['F','R'] if (c+rep+(n==128))%2==0 else ['R','F']
        for method in methods:
         res=[420,5000] if method=='R' else ([90,900] if n==32 else [120,1500])
         q=slot(f'{method}-{pair}','encrypted',method,c,n,res,'main_fixed')
         q.update(pair_id=pair,payload_hex=data.hex(),payload_sha256=hashlib.sha256(data).hexdigest(),payload_bytes=n,key_index=2*c+rep,repetition=rep)
         encrypted.append(q)
    for i,e in enumerate(encrypted):
      for j,family in enumerate('AB'):
       n=e['payload_bytes'];method=e['method']
       res=[300,3300] if method=='R' else ([65,900] if n==32 else [90,1100])
       q=slot(f"control-{e['case_id']}-{family}",'control',method,e['context_index'],n,res,'main_fixed')
       q.update(pair_id=e['pair_id'],associated_encrypted_case_id=e['case_id'],payload_setting_bytes=n,
                fallback_tokens=1536 if method=='R' else 2*(68+n),family=family,sampling_seed=202609190000+10*i+j,
                recipient_public_key_hex=keys[e['key_index']]['public_key_hex'],repetition=e['repetition'])
    for c in [0,2]:
      for n in [32,128]:
       for method in ['F','R']:
        q=slot(f'replay-{method}-c{c}-n{n}','replay',method,c,n,[180,1650] if method=='R' else ([50,320] if n==32 else [65,512]),'fresh_receiver')
        q.update(source_case_id=f'{method}-c{c}-n{n}-r0',key_index=2*c)
    allocation={'schema_version':1,'starting_commit':authorization['starting_commit'],'baseline_usage':authorization['baseline_usage'],
        'authorization_sha256':hashlib.sha256(canonical_json(authorization)).hexdigest(),
        'additional_limits':authorization['additional_limits'],'lifetime_limits':authorization['lifetime_limits'],'slots':slots,
        'qualification_cases':6,'main_cases':104,'unallocated_cases':18,
        'qualification_allowance_max':16,'extra_investigation_allowance_max':8,
        'payload_formula':'SHAKE256(ASCII(ICISSP2027 Stage7 binary c={c} n={n} r={rep})).digest(n)',
        'key_assignment':'2*context+repetition, eight independent keys; key8 qualification only',
        'control_lengths':'received token count of associated successfully delivered encrypted carrier; otherwise fixed fallback 1536 R or 2*(68+n) F; no controls omitted',
        'crypto_randomness':'fresh OS/library randomness; independent across methods; no PRNG substitution',
        'sampling':'PCG64 unique predeclared seeds; temperature1; A all vocabulary EOS ordinary no early stop; B exact conditional probabilities on shared16; no resampling',
        'replay_policy':'contexts0,2 repetition0 both methods/sizes; failed sources unavailable with no substitution',
        'analysis_spec_path':'docs/stage7_study_spec.md','analysis_spec_sha256':digest(ROOT/'docs/stage7_study_spec.md'),
        'retries':0,'reservations':'Full per-case reservations enforced at admission, never reduced to fit; main forecast release required after qualification'}
    write_new(ART/'allocation.json',allocation)
    write_new(ART/'environment.json',{'schema_version':1,'selected_gpu':selected,'gpu_inventory':devices,'runtime':runtime,'runtime_packages':required,
        'python':platform.python_version(),'platform':platform.platform(),'model_sha256':profile['model']['sha256'],'tokenizer_sha256':h.hexdigest(),
        'native_library_sha256':profile['backend']['native_library_sha256'],'cuda_library_sha256':cuda,
        'crypto_dependencies':{x:importlib.metadata.version(x) for x in ['pyhpke','cryptography']},
        'asset_checks':'PASS; frozen model/tokenizer/backend/CUDA hashes verified; no model inference'})
    print(json.dumps({'asset_checks':'PASS','selected_gpu':selected,'baseline_usage':authorization['baseline_usage'],'frozen_slots':len(slots)}))

if __name__=='__main__':main()
