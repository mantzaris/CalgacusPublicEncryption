#!/usr/bin/env python3
"""Hash final host-analysis/report outputs after their writers have exited."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'artifacts/stage6'
path=ROOT/'manifests/stage6_evidence.json'
m=json.loads(path.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
outputs=[p for p in ART.iterdir() if p.is_file()]+list((ART/'figures').glob('*'))
m['outputs']={str(p.relative_to(ROOT)):sha(p) for p in sorted(outputs) if p.is_file()}
m['reports']={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'STAGE6_FRAMING_STUDY_REPORT.md',ROOT/'docs/stage6_claims.md',ROOT/'docs/stage6_study_spec.md']}
m['finalize_manifest_command']='.venv/bin/python artifacts/stage6/finalize_manifest.py'
m['claim_links']=[
 {'claim':'main actual-UTF8 exact recovery, rates and expansion','selection':{'stage6_phase':'main_fixed','kind':'encrypted'},'records':'artifacts/stage6/cases.jsonl','outputs':['artifacts/stage6/recovery.csv','artifacts/stage6/figures/recovery_useful_rate.png']},
 {'claim':'public recognition under three matched cover generators','selection':{'stage6_phase':'main_fixed','methods':['L','F']},'records':'artifacts/stage6/cases.jsonl','outputs':['artifacts/stage6/recognition.json','artifacts/stage6/paired_differences.json','artifacts/stage6/figures/recognition_auc.png','artifacts/stage6/figures/body_score_distributions.png']},
 {'claim':'failed baseline transmissions and delivered control drift','records':'artifacts/stage6/failures.json','outputs':['artifacts/stage6/failures.csv','artifacts/stage6/figures/costs_failures.png']},
 {'claim':'independent receiver reconstruction','selection':{'kind':'replay'},'records':'artifacts/stage6/cases.jsonl','outputs':['artifacts/stage6/pid_evidence.json','artifacts/stage6/summary.json']},
 {'claim':'inclusive resources and historical preservation','records':'artifacts/project_budget.jsonl','outputs':['artifacts/project_budget.checkpoint.json','artifacts/stage6/costs.csv','artifacts/stage6/historical_preservation.json','artifacts/stage6/analysis_output.txt']},
 {'claim':'focused prelaunch checks; no full suite','records':'artifacts/stage6/prelaunch_provenance.json','outputs':['artifacts/stage6/focused_checks.txt','artifacts/stage6/allocation_check.txt']}
]
m['claim_link_defaults']={'configuration':'artifacts/stage6/allocation.json','commands':'artifacts/stage6/commands.json','gpu_tested_code_commits':m['gpu_tested_code_commits'],'analysis_source_sha256':sha(ART/'analyze.py')}
m['ledger_sha256']=sha(ROOT/'artifacts/project_budget.jsonl')
path.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
for name,h in m['outputs'].items():assert sha(ROOT/name)==h
for name,h in m['reports'].items():assert sha(ROOT/name)==h
for name,h in m['frozen_inputs'].items():assert sha(ROOT/name)==h
for attempt in m['attempts']:
 for name,h in attempt['files'].items():assert sha(ROOT/name)==h
print('PASS: final manifest hashes all reports, analysis outputs, figures and immutable attempt files.')
