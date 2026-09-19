"""Link final host analysis/report artifacts; no inference or ledger mutations."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage8';path=ROOT/'manifests/stage8_evidence.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
s=read(ART/'summary.json');m=read(path)
release=read(ART/'main_release.json')
diag_count=read(ART/'diagnostic_status.json')['recorded_outcomes']
assert hashlib.sha256(b''.join((ART/'cases.jsonl').read_bytes().splitlines(keepends=True)[:diag_count])).hexdigest()==release['diagnostic_cases_sha256']
assert s['unsettled_attempts']==[] and s['all_gpu_lease_phase_provenance_verified'] and s['all_workers_clean_exit']
assert 'Report assembly in progress' not in (ROOT/'STAGE8_CAPACITY_COMPARISON_REPORT.md').read_text()
files=[p for p in ART.iterdir() if p.is_file() and p.name not in ['final_review.json']]
files += list((ART/'figures').glob('*'))
files += [ROOT/'STAGE8_CAPACITY_COMPARISON_REPORT.md',ROOT/'docs/stage8_capacity_diagnosis.md',ROOT/'docs/stage8_claims.md',ROOT/'docs/stage8_study_spec.md']
m['derived_outputs']={str(p.relative_to(ROOT)):sha(p) for p in files}
m['main_release']={'path':'artifacts/stage8/main_release.json','sha256':sha(ART/'main_release.json'),'selected_cases':read(ART/'main_release.json')['selected_case_ids']}
m['main_status']={'path':'artifacts/stage8/main_status.json','sha256':sha(ART/'main_status.json')}
m['post_test_work']='Host reconciliation, plots, tables and report; no algorithm, framing, sampling, model, profile or accounting change after the diagnostic freeze.'
m['qualification_gate_passed']=s['diagnostic_status']['qualification_passed']
m['data_separation']='Stage7 historical diagnosis; repeated-packet diagnostics; fresh main transmissions and matched controls; replays not independent messages. All contexts development-informed, no pooling into held-out data.'
m['additional_commands']=['.venv/bin/python artifacts/stage8/diagnose.py','.venv/bin/python artifacts/stage8/release_main.py','.venv/bin/python artifacts/stage8/tables.py','MPLCONFIGDIR=/tmp/stage8-mpl ../llm-rankcloak/.venv/bin/python artifacts/stage8/plot.py','.venv/bin/python artifacts/stage8/finalize_evidence.py']
# No self-hash: the manifest links its products; final_review links the manifest.
path.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
checks={}
for group in ['frozen_inputs','derived_outputs']:
 for name,h in m[group].items():assert sha(ROOT/name)==h,name
for attempt in m['attempts']:
 for name,h in attempt['files'].items():assert sha(ROOT/name)==h,name
assert sha(ROOT/'artifacts/project_budget.jsonl')==m['ledger_sha256']
checks.update(schema_version=1,status='PASS',manifest_sha256=sha(path),attempts=len(m['attempts']),historical_ledger_prefix_preserved=s['historical_ledger_prefix_preserved'],ledger_sha256=m['ledger_sha256'],gpu_tested_source_revisions=s['gpu_tested_code_commits'],stage8_usage=s['stage8_usage'],lifetime_usage=s['lifetime_usage'],no_new_inference=True,no_broad_cpu_suite=True,checks='Every frozen input, retained attempt file and derived-output digest; report completion; ledger reconciliation; distinct stages and tested sources')
(ART/'final_review.json').write_text(json.dumps(checks,indent=2,sort_keys=True)+'\n')
print(json.dumps(checks,indent=2))
