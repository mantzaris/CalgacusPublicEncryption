"""Finalize hashes after report/analysis writers close; host-only."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage7'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((ART/'summary.json').read_text());manifest_path=ROOT/'manifests/stage7_evidence.json';m=json.loads(manifest_path.read_text())
m['outputs']={str(p.relative_to(ROOT)):sha(p) for p in ART.rglob('*') if p.is_file() and 'attempts' not in p.parts}
m['report_and_claims']={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'STAGE7_COMPARATOR_REPORT.md',ROOT/'docs/stage7_claims.md',ROOT/'docs/stage7_comparator_audit.md']}
m['claim_evidence']={'independent_core_and_boundary_validation':['tests/test_stage7.py','artifacts/stage7/focused_checks.txt'],
 'live_synthetic_inverse':['artifacts/stage7/cases.jsonl','artifacts/stage7/qualification.csv'],
 'capacity_abort_and_stopping':['artifacts/stage7/capacity.json','artifacts/stage7/qualification_status.json'],
 'no_main_recognition_results':['artifacts/stage7/summary.json','artifacts/stage7/recognition.csv'],
 'resource_and_provenance':['artifacts/stage7/pid_evidence.json','artifacts/stage7/environment.json','artifacts/project_budget.jsonl','artifacts/project_budget.checkpoint.json']}
m['unexecuted_main_slots']=s['main_skipped_by_gate'];m['final_readiness']='BLOCKED: live HPKE capacity qualification and fresh-process receiver gate not passed'
manifest_path.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
rows=[json.loads(l) for l in (ART/'cases.jsonl').read_text().splitlines()]
assert len(rows)==4 and sum(r['charged_tokens'] for r in rows)==6865
assert not s['main_executed'] and len(s['main_skipped_by_gate'])==104
assert not any(r.get('authenticated_message_recovery') for r in rows)
assert sum(r.get('exact_envelope_recovery',False) for r in rows)==1
assert sum(r['failure_category']=='capacity_exhaustion' for r in rows)==3
print(json.dumps({'manifest':'PASS','attempts':4,'synthetic_exact':1,'hpke_exact':0,'capacity_failures':3,'main_unexecuted_slots':104,'historical_prefix_preserved':s['historical_ledger_prefix_preserved']}))
