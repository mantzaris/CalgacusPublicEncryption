"""Retrospective public-table arithmetic reanalysis; no inference."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.evaluation.stopping_rule import decompose_public_symbols
rows=[json.loads(x) for x in (ROOT/'artifacts/stage8/cases.jsonl').read_text().splitlines()]
out=[]
for r in rows:
    if r['kind']!='control' or r['method']!='R':continue
    p=ROOT/r['trace_path'];trace=json.loads(p.read_text())['public_scoring'];wire=ROOT/r['evidence_dir']/'carrier.txt'
    result=decompose_public_symbols(trace['symbols'],trace['frequency_tables'],68+r['payload_setting_bytes'],canonical=r['observer']['canonical_bytes'])
    out.append(dict(case_id=r['case_id'],source_attempt_id=r['attempt_id'],source_gpu_revision=r['tested_code_commit'],profile_path=json.loads((ROOT/r['evidence_dir']/'input.json').read_text())['profile_path'],context_index=r['context_index'],transmitted_tokens=len(trace['symbols']),wire_path=str(wire.relative_to(ROOT)),inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest(),str(wire.relative_to(ROOT)):hashlib.sha256(wire.read_bytes()).hexdigest()},old_format_error=r['observer'].get('format_error'),predicates=result))
result=dict(schema_version=1,scope='Retrospective public scoring tables; not live reception or independent samples',cases=out)
(ROOT/'artifacts/stage9/historical_reanalysis.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
for r in out:print(r['case_id'],r['transmitted_tokens'],r['predicates'])
