#!/usr/bin/env python3
"""Stage 6 host-only asset checks and frozen public inputs; no model evaluation."""
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
ART=ROOT/'artifacts/stage6'


def main():
    if (ART/'allocation.json').exists(): raise RuntimeError('Stage 6 allocation already frozen')
    profile=json.loads((ROOT/'configs/stage6/L.json').read_text());validate_rank16_profile(profile)
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
    authorization=json.loads((ROOT/'configs/stage6/authorization.json').read_text())
    previous=[]
    for folder in ['stage1','stage2_pilot','stage3_transport','stage4_prefix']:
        previous+=rows(ROOT/'artifacts'/folder/'cases.jsonl')
    # Preparation is read-only with respect to the historical ledger/checkpoint.
    ledger=BudgetLedger(ROOT/'artifacts/project_budget.jsonl')
    try:
        validate_resume(ledger,previous)
        if ledger.usage()!=authorization['baseline_usage']: raise RuntimeError('Intervening project GPU work')
        raw=ledger.path.read_bytes();old=authorization['previous_checkpoint']
        if len(raw)!=old['bytes'] or hashlib.sha256(raw).hexdigest()!=old['sha256']: raise RuntimeError('Historical checkpoint mismatch')
    finally: ledger.close()
    profiles={m:json.loads((ROOT/f'configs/stage6/{m}.json').read_text()) for m in ['L','F','Calgacus']}
    for p in profiles.values(): validate_supported_profile(p)
    if any(len(c.encode('utf-8'))+1>64 for c in profile['cover_contexts']): raise RuntimeError('Conservative context bound exceeded')
    if set(profile['cover_contexts']) & set(baseline_profile['cover_contexts']): raise RuntimeError('Contexts not new')
    keys=[]
    for i in range(9):
        sk,pk=generate_key_pair();keys.append({'key_id':f'STAGE6_TEST_ONLY_{i}', 'TEST_ONLY_private_key_hex':sk.hex(),'public_key_hex':pk.hex()})
    write_new(ART/'TEST_ONLY_keys.json',{'schema_version':1,'warning':'TEST ONLY: public synthetic fixtures, never operational keys','keys':keys})
    slots=[]
    def slot(case,kind,method,c,res,phase='main_fixed'):
        v={'case_id':case,'kind':kind,'method':method,'context_index':c,'reservation':res,'stage6_phase':phase,
           'profile_path':f'configs/stage6/{method}.json','profile_sha256':hashlib.sha256(canonical_json(profiles[method])).hexdigest(),
           'split':'qualification_development_only' if phase=='qualification' else 'stage6_prospective_exploratory_fixed_not_final_test'}
        slots.append(v);return v
    for c in range(4):slot(f'qualification-predict-{c}','prediction','L',c,[45,128],'qualification')
    for n,c,res in [(0,0,[75,700]),(128,3,[120,1500])]:
        q=slot(f'qualification-F-{n}','encrypted','F',c,res,'qualification')
        q.update(payload_hex=hashlib.shake_256(f'Stage6 qualification {n}'.encode()).digest(n).hex(),key_index=8,payload_bytes=n)
    encrypted=[]
    for c in range(4):
        for n in [32,128]:
            for rep in range(2):
                pair=f'c{c}-n{n}-r{rep}'
                payload=hashlib.shake_256(f'ICISSP2027 Stage6 synthetic binary c={c} n={n} r={rep}'.encode()).digest(n)
                # Counterbalance L/F order by context+size+repetition, frozen before outcomes.
                methods=['L','F'] if (c+rep+(n==128))%2==0 else ['F','L']
                for method in methods:
                    q=slot(f'{method}-{pair}','encrypted',method,c,[90,1000] if n==32 else [120,1500])
                    q.update(pair_id=pair,payload_hex=payload.hex(),payload_sha256=hashlib.sha256(payload).hexdigest(),payload_bytes=n,key_index=2*c+rep,repetition=rep)
                    encrypted.append(q)
    for i,e in enumerate(encrypted):
        for j,family in enumerate('ABC'):
            n=e['payload_bytes'];q=slot(f"control-{e['case_id']}-{family}",'control',e['method'],e['context_index'],[65,900] if n==32 else [90,1100])
            q.update(pair_id=e['pair_id'],associated_encrypted_case_id=e['case_id'],payload_setting_bytes=n,
                     target_tokens=2*(68+n+(4 if e['method']=='L' else 0)),family=family,
                     sampling_seed=202609180000+10*i+j,recipient_public_key_hex=keys[e['key_index']]['public_key_hex'],repetition=e['repetition'])
    for c in range(4):
        for n in [32,128]:
            e=next(x for x in encrypted if x['context_index']==c and x['payload_bytes']==n and x['repetition']==0)
            q=slot(f'Calgacus-c{c}-n{n}','encrypted','Calgacus',c,[120,3300],'baseline')
            q.update(pair_id=e['pair_id'],payload_hex=e['payload_hex'],payload_sha256=e['payload_sha256'],payload_bytes=n,key_index=e['key_index'])
    for c in [0,2]:
        for n in [32,128]:
            for method in ['L','F']:
                q=slot(f'replay-{sum(x["kind"]=="replay" for x in slots):02}','replay',method,c,[50,320] if n==32 else [65,512],'fresh_receiver')
                q.update(source_case_id=f'{method}-c{c}-n{n}-r0',key_index=2*c)
    totals={'seconds':sum(s['reservation'][0] for s in slots),'tokens':sum(s['reservation'][1] for s in slots),'cases':len(slots)}
    if any(totals[k]>authorization['additional_limits'][k] for k in totals):raise RuntimeError('Full frozen reservations exceed Stage 6 allocation; reduce symmetrically before execution')
    allocation={'schema_version':1,'starting_commit':authorization['starting_commit'],'starting_working_tree':'clean',
        'authorization_sha256':hashlib.sha256(canonical_json(authorization)).hexdigest(),'baseline_usage':authorization['baseline_usage'],
        'additional_limits':authorization['additional_limits'],'lifetime_limits':authorization['lifetime_limits'],
        'all_full_reservations':totals,'slots':slots,'qualification_cases':6,'principal_cases':144,'unused_investigation_slots':10,
        'payload_formula':'SHAKE256(ASCII(ICISSP2027 Stage6 synthetic binary c={c} n={n} r={rep})).digest(n)',
        'key_assignment':'eight independent OS-generated main keys: 2*context_index+repetition; one separate qualification key',
        'cryptographic_randomness':'OS/library fresh X25519 ephemeral keys and message IDs; not seeded',
        'sampling':'NumPy PCG64 fixed unique seed per control; temperature 1; six-prefix predictions have no sampling',
        'analysis_spec_path':'docs/stage6_study_spec.md','analysis_spec_sha256':digest(ROOT/'docs/stage6_study_spec.md'),
        'retries':0,'resume':'only a clean completed-case prefix; orphan/overrun/fatal history fails closed',
        'stop':'qualification failure; accounting/lease/deadline/provenance/numerical/invariant or authenticated-incorrect failure; no repairs/retries; candidate exhaustion retained',
        'replay_policy':'predetermined contexts 0 and 2, repetition 0, both sizes/variants; unavailable slots unused'}
    write_new(ART/'allocation.json',allocation)
    write_new(ART/'environment.json',{'schema_version':1,'selected_gpu':selected,'gpu_inventory':devices,'runtime':runtime,'runtime_packages':required,
        'python':platform.python_version(),'platform':platform.platform(),'model_sha256':profile['model']['sha256'],'tokenizer_sha256':h.hexdigest(),
        'native_library_sha256':profile['backend']['native_library_sha256'],'cuda_library_sha256':cuda,
        'crypto_dependencies':{x:importlib.metadata.version(x) for x in ['pyhpke','cryptography']},
        'asset_checks':'PASS; unchanged frozen model/tokenizer/backend/CUDA identities','gpu_model_work_in_preparation':False})
    print(json.dumps({'asset_checks':'PASS','selected_gpu':selected,'baseline_usage':authorization['baseline_usage'],'frozen_slots':len(slots),'full_reservations':totals}),flush=True)

if __name__=='__main__':main()
