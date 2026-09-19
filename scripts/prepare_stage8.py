#!/usr/bin/env python3
"""Stage 8 host-only asset checks and frozen public inputs; no model evaluation."""
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
ART=ROOT/'artifacts/stage8'


def main():
    if (ART/'allocation.json').exists(): raise RuntimeError('Stage 8 allocation already frozen')
    profile=json.loads((ROOT/'configs/stage8/R32.json').read_text());validate_supported_profile(profile)
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
    authorization=json.loads((ROOT/'configs/stage8/authorization.json').read_text())
    previous=[]
    for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix','stage6','stage7']:
        previous+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
    # Preparation is read-only with respect to the historical ledger/checkpoint.
    ledger=BudgetLedger(ROOT/'artifacts/project_budget.jsonl',authorization=json.loads((ROOT/'configs/stage7/authorization.json').read_text()))
    try:
        validate_resume(ledger,previous)
        if ledger.usage()!=authorization['baseline_usage']: raise RuntimeError('Intervening project GPU work')
        raw=ledger.path.read_bytes();old=authorization['previous_checkpoint']
        if len(raw)!=old['bytes'] or hashlib.sha256(raw).hexdigest()!=old['sha256']: raise RuntimeError('Historical checkpoint mismatch')
    finally: ledger.close()
    profiles={f'{m}{n}':json.loads((ROOT/f'configs/stage8/{m}{n}.json').read_text()) for m in ['F','R'] for n in [32,128]}
    for p in profiles.values(): validate_supported_profile(p)
    if any(len(c.encode('utf-8'))+1>64 for c in profile['cover_contexts']): raise RuntimeError('Conservative context bound exceeded')
    if set(profile['cover_contexts']) & set(baseline_profile['cover_contexts']): raise RuntimeError('Contexts not new')
    keys=[]
    for i in range(8):
        sk,pk=generate_key_pair();keys.append({'key_id':f'STAGE8_TEST_ONLY_{i}','TEST_ONLY_private_key_hex':sk.hex(),'public_key_hex':pk.hex()})
    write_new(ART/'TEST_ONLY_keys.json',{'schema_version':1,'warning':'Public TEST ONLY synthetic fixtures','keys':keys})
    slots=[]
    def slot(case,kind,method,c,n,res,phase):
        p=profiles[f'{method}{n}']
        v={'case_id':case,'kind':kind,'method':method,'context_index':c,'reservation':res,'stage8_phase':phase,
           'profile_path':f'configs/stage8/{method}{n}.json','profile_sha256':hashlib.sha256(canonical_json(p)).hexdigest(),
           'split':'repeated_historical_packet_development_only' if phase=='diagnostic' else 'stage8_prospective_development_informed_not_final_test'}
        slots.append(v);return v
    old=rows(ROOT/'artifacts/stage7/cases.jsonl')
    for r in old:
        n=r['payload_setting_bytes'];q=slot('diagnostic-'+r['case_id'],'fixture','R',r['context_index'],n,[360,4200],'diagnostic')
        q.update(historical_attempt_id=r['attempt_id'])
    for case in ['qual-HPKE-32','qual-HPKE-128','qual-synthetic-32','qual-synthetic-128']:
        r=next(x for x in old if x['case_id']==case)
        q=slot('diagnostic-replay-'+case,'replay','R',r['context_index'],r['payload_setting_bytes'],[210,2100],'diagnostic')
        q.update(source_case_id='diagnostic-'+case,historical_attempt_id=r['attempt_id'])
    encrypted=[]
    for c in range(4):
      for n in [32,128]:
       for rep in range(2):
        pair=f'c{c}-n{n}-r{rep}';data=hashlib.shake_256(f'ICISSP2027 Stage8 binary c={c} n={n} r={rep}'.encode()).digest(n)
        for method in (['F','R'] if (c+rep+(n==128))%2==0 else ['R','F']):
         q=slot(f'{method}-{pair}','encrypted',method,c,n,[540,6200] if method=='R' else ([90,900] if n==32 else [120,1500]),'main_fixed')
         q.update(pair_id=pair,payload_hex=data.hex(),payload_sha256=hashlib.sha256(data).hexdigest(),payload_bytes=n,key_index=2*c+int(n==128),repetition=rep)
         encrypted.append(q)
    for i,e in enumerate(encrypted):
        n=e['payload_bytes'];method=e['method']
        q=slot('control-'+e['case_id']+'-B','control',method,e['context_index'],n,[360,4200] if method=='R' else ([65,900] if n==32 else [90,1100]),'main_fixed')
        q.update(pair_id=e['pair_id'],associated_encrypted_case_id=e['case_id'],payload_setting_bytes=n,fallback_tokens=1984 if method=='R' else 2*(68+n),family='B',
                 sampling_seed=202609200000+i,recipient_public_key_hex=keys[e['key_index']]['public_key_hex'],repetition=e['repetition'])
    for c in [0,2]:
      for n in [32,128]:
       for method in ['F','R']:
        q=slot(f'replay-{method}-c{c}-n{n}','replay',method,c,n,[210,2100] if method=='R' else ([50,320] if n==32 else [65,512]),'fresh_receiver')
        q.update(source_case_id=f'{method}-c{c}-n{n}-r0',key_index=2*c+int(n==128))
    allocation={'schema_version':1,'starting_commit':authorization['starting_commit'],'baseline_usage':authorization['baseline_usage'],
      'authorization_sha256':hashlib.sha256(canonical_json(authorization)).hexdigest(),'additional_limits':authorization['additional_limits'],
      'lifetime_limits':authorization['lifetime_limits'],'slots':slots,'diagnostic_cases':8,'candidate_main_cases':72,'unscheduled_investigation_slots':8,
      'carrier_ceiling':1984,'possible_main_repetitions':[2,1],'key_assignment':'2*context+(payload==128); eight independent keys; group repeats together',
      'analysis_spec_path':'docs/stage8_study_spec.md','analysis_spec_sha256':digest(ROOT/'docs/stage8_study_spec.md'),
      'control_length_assignment':'delivered received token count; failed source fallback1984 R /200 or392 F; no omission',
      'replay_policy':'fixed sources, unavailable slots unused; diagnostic HPKE first',
      'retries':0,'main_release':'only after qualification and committed conservative resource forecast; symmetric reduction allowed before main'}
    write_new(ART/'allocation.json',allocation)
    write_new(ART/'environment.json',{'schema_version':1,'selected_gpu':selected,'gpu_inventory':devices,'runtime':runtime,'runtime_packages':required,
       'python':platform.python_version(),'platform':platform.platform(),'model_sha256':profile['model']['sha256'],'tokenizer_sha256':h.hexdigest(),
       'native_library_sha256':profile['backend']['native_library_sha256'],'cuda_library_sha256':cuda,
       'crypto_dependencies':{x:importlib.metadata.version(x) for x in ['pyhpke','cryptography']},'asset_checks':'PASS; no model inference'})
    print(json.dumps({'asset_checks':'PASS','gpu':selected,'frozen_slots':len(slots),'baseline_usage':authorization['baseline_usage']}))

if __name__=='__main__':main()
