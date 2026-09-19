"""Vocabulary-only host check: no model tensor evaluation, no GPU job."""
import ctypes,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['CUDA_VISIBLE_DEVICES']=''
r=json.loads((ROOT/'configs/local_runtime.json').read_text());site=Path(r['reused_site_packages'])
for lib in ['nvidia/cuda_runtime/lib/libcudart.so.12','nvidia/cublas/lib/libcublasLt.so.12','nvidia/cublas/lib/libcublas.so.12']:ctypes.CDLL(str(site/lib),mode=ctypes.RTLD_GLOBAL)
from llama_cpp import Llama
vocab=Llama(model_path=r['model_path'],vocab_only=True,n_gpu_layers=0,verbose=False)
contexts=json.loads((ROOT/'configs/stage9/R32.json').read_text())['cover_contexts']+json.loads((ROOT/'configs/stage8/R32.json').read_text())['cover_contexts']
rows=[]
for c in contexts:
    ids=[vocab.token_bos()]+vocab.tokenize(c.encode(),add_bos=False,special=False)
    assert len(ids)+1984+1<=2048
    rows.append(dict(context=c,context_token_ids_including_bos=ids,actual_context_tokens=len(ids),total_positions=len(ids)+1984+1))
vocab.close()
p=ROOT/'artifacts/stage9/context_window_check.json'
with p.open('x') as f:json.dump(dict(schema_version=1,mode='vocabulary only; vocab_only=True; no eval calls',contexts=rows),f,indent=2);f.write('\n')
print(json.dumps(rows))
