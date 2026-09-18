#!/usr/bin/env python3
"""Host-only preparation: discover GPU, verify existing assets, preserve ledger, freeze cases."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_stego_public_key.cryptography.hpke import generate_key_pair
from llm_stego_public_key.evaluation.budget import BudgetLedger
from llm_stego_public_key.profile import canonical_json, validate_supported_profile
from run_smoke import write_new, validate_resume

ART = ROOT / 'artifacts/stage2_pilot'
HISTORICAL = [
 'bcb46cde-561b-48cb-ab40-73efd8b5dff4', 'e5f17a95-4bba-4511-bd77-d318cb600038',
 '28297d91-c3a6-4f08-b65f-4ad095921c28', '12de85ea-3e3e-4a4a-8997-27e551978366']

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''): h.update(chunk)
 return h.hexdigest()

def main():
 if (ART/'allocation.json').exists(): raise RuntimeError('Allocation exists; do not regenerate inputs')
 ART.mkdir(exist_ok=True, parents=True)
 profile=json.loads((ROOT/'configs/public_profile.json').read_text());validate_supported_profile(profile)
 runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
 gpu_csv=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,memory.total,driver_version','--format=csv,noheader,nounits'],text=True)
 devices=[dict(zip(['index','name','uuid','vram_mib','driver'],[s.strip() for s in l.split(',')])) for l in gpu_csv.splitlines()]
 selected=next((d for d in devices if d['uuid']==runtime['gpu_uuid']),None)
 if selected is None: raise RuntimeError('Configured supported GPU is not connected; no fallback')
 model=Path(runtime['model_path']);site=Path(runtime['reused_site_packages'])
 if digest(model)!=profile['model']['sha256']: raise RuntimeError('Model identity mismatch')
 import gguf
 reader=gguf.GGUFReader(str(model),'r');h=hashlib.sha256()
 for name,field in sorted(reader.fields.items()):
  if name.startswith('tokenizer.'):
   raw=name.encode();h.update(len(raw).to_bytes(4,'big')+raw)
   for part in field.parts:
    raw=part.tobytes();h.update(len(raw).to_bytes(8,'big')+raw)
 if h.hexdigest()!=profile['model']['tokenizer_sha256']: raise RuntimeError('Tokenizer mismatch')
 for name,expected in profile['backend']['native_library_sha256'].items():
  if digest(site/'llama_cpp/lib'/name)!=expected: raise RuntimeError('Native backend mismatch: '+name)
 env=json.loads((ROOT/'manifests/environment.json').read_text())
 for name,expected in env['cuda_libraries'].items():
  if digest(site/name)!=expected: raise RuntimeError('CUDA library mismatch: '+name)
 installed={d.metadata['Name'].lower().replace('_','-'):d.version for d in importlib.metadata.distributions(path=[str(site)])}
 required={'llama-cpp-python':profile['backend']['llama_cpp_python'],'numpy':profile['backend']['numpy'],**profile['backend']['cuda_packages']}
 for name,version in required.items():
  if installed.get(name)!=version: raise RuntimeError('Unsupported runtime package '+name)
 anchor=json.loads((ROOT/'configs/stage1_budget_anchor.json').read_text())
 old=BudgetLedger(ROOT/'artifacts/stage1/budget.jsonl',anchor=anchor)
 try:
  records=[json.loads(s) for s in (ROOT/'artifacts/stage1/cases.jsonl').read_text().splitlines()]
  validate_resume(old,records)
  prior=old.usage();raw=old.path.read_bytes()
  project=ROOT/'artifacts/project_budget.jsonl'
  with project.open('xb') as f: f.write(raw);f.flush();os.fsync(f.fileno())
  migration={'schema_version':1,'source':'artifacts/stage1/budget.jsonl','destination':'artifacts/project_budget.jsonl','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'prior_usage':prior,'old_launch_path':'run_smoke.py main retired; shared execute helper uses new ledger','shared_lock':'artifacts/project_budget.lock'}
  write_new(ART/'migration.json',migration)
  new=BudgetLedger(project,anchor=migration)
  try:
   assert new.usage()==prior and project.read_bytes()==raw
  finally:new.close()
 finally:old.close()
 keys=[]
 for i in range(2):
  sk,pk=generate_key_pair();keys.append({'key_id':f'pilot-{i}','TEST_ONLY_private_key_hex':sk.hex(),'public_key_hex':pk.hex()})
 write_new(ART/'TEST_ONLY_keys.json',{'schema_version':1,'warning':'PUBLIC INSECURE DEVELOPMENT TEST MATERIAL; never use for real data.','generation':'two independent OS-random library X25519 key pairs','keys':keys})
 slots=[]
 for i,aid in enumerate(HISTORICAL):
  row=next(r for r in records if r['attempt_id']==aid)
  slots.append({'case_id':f'pilot-historical-{i}','family':'historical_replay','kind':'replay','source_attempt_id':aid,'context_index':profile['cover_contexts'].index(row['cover_context']),'expected_rejection':i==3,'reservation':[60,600]})
 for u,size,context in [(0,32,0),(0,128,1),(1,32,2),(1,128,0)]:
  slots.append({'case_id':f'pilot-k{u}-n{size}','family':'fresh_encrypted','kind':'encrypted','key_id':f'pilot-{u}','payload_hex':bytes((167+29*u+7*j+size)%256 for j in range(size)).hex(),'payload_bytes':size,'context_index':context,'reservation':[120,2000],'public_observer':True})
 for i in range(2): slots.append({'case_id':f'pilot-control-{i}','family':'control','kind':'control','context_index':i,'sampling_seed':2026091901+i,'fallback_tokens':192,'reservation':[90,1200]})
 for i in range(2): slots.append({'case_id':f'pilot-fresh-replay-{i}','family':'fresh_replay','kind':'replay','key_id':f'pilot-{i}','reservation':[60,750]})
 baseline=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 write_new(ART/'allocation.json',{'schema_version':1,'starting_commit':baseline,'starting_working_tree':'clean before implementation','profile_sha256':hashlib.sha256(canonical_json(profile)).hexdigest(),'baseline_usage':prior,'pilot_limits':{'seconds':1200,'tokens':8000,'cases':12},'global_limits':{'seconds':7200,'tokens':25000,'cases':72},'slots':slots,'split':'development_only_excluded_from_future_heldout','retry_policy':'none','crypto_randomness':'OS/library fresh encapsulation and message IDs','control_policy':'first produced new carrier in same context, else 192 tokens','replay_policy':'first successful new carrier per new key','cpu_rerun':'waived by explicit user authorization; historical 109 CPU results reused, not credited to this extension'})
 write_new(ART/'environment.json',{'schema_version':1,'gpu_inventory':devices,'selected_gpu':selected,'runtime':runtime,'runtime_packages':required,'python':platform.python_version(),'platform':platform.platform(),'model_sha256':profile['model']['sha256'],'tokenizer_sha256':h.hexdigest(),'native_library_sha256':profile['backend']['native_library_sha256'],'cuda_library_sha256':env['cuda_libraries'],'asset_checks':'all matched; no model/CUDA initialization in preparation','gpu_work_in_preparation':False})
 print(json.dumps({'selected_gpu':selected,'prior_usage':prior,'frozen_slots':len(slots),'asset_checks':'PASS'}),flush=True)

if __name__=='__main__':main()
