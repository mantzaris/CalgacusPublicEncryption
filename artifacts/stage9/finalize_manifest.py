"""Host-only final evidence inventory; never starts a model or edits the ledger."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage9'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
base=read(ART/'starting_state.json')['tracked_files']
changed=[p for p,h in base.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
expected={'artifacts/project_budget.jsonl','artifacts/project_budget.checkpoint.json','src/llm_stego_public_key/profile.py','src/llm_stego_public_key/evaluation/budget.py'}
assert set(changed)==expected,changed
assert not subprocess.check_output(['git','diff','HEAD','--','src','scripts','tests','configs'],cwd=ROOT)
manifest=read(ROOT/'manifests/stage9_evidence.json')
for attempt in manifest['attempts']:
    for p,h in attempt['files'].items():assert sha(ROOT/p)==h,(p,'changed attempt')
reports=['STAGE9_STOPPING_RULE_REPORT.md','paper/PAPER_BLUEPRINT.md','paper/CLAIM_EVIDENCE_MATRIX.md','docs/stage9_study_spec.md','docs/stage9_observer_contract.md']
for path in reports:
    data=(ROOT/path).read_text()
    for target in re.findall(r'\]\(([^)]+)\)',data):
        if target.startswith(('http://','https://','#')):continue
        assert (ROOT/path).parent.joinpath(target.split('#')[0]).exists(),(path,target)
    assert 'in progress under the frozen allocation' not in data
extra=reports+['configs/stage9/R32.json','configs/stage9/authorization.json','configs/local_runtime.json','requirements-cpu.lock','pyproject.toml']
extra += [str(p.relative_to(ROOT)) for p in (ROOT/'src/llm_stego_public_key').rglob('*.py')]
extra += [str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*stage9*.py')]+['tests/test_stage9.py']
files={str(p.relative_to(ROOT)):sha(p) for p in ART.rglob('*') if p.is_file() and 'attempts' not in p.parts and '__pycache__' not in p.parts and p.name!='final_verification.txt'}
files.update({p:sha(ROOT/p) for p in extra})
manifest.update(files=files,host_analysis_and_reporting='Added after GPU revision; file hashes identify exact analysis. Final commit is reported in the completion response, avoiding a self-referential commit field.',
    verification=dict(unchanged_prior_files=len(base)-len(changed),expected_modified_prior_files=changed,all_attempt_hashes_verified=True,all_new_markdown_local_links_exist=True,no_inference_source_changes_after_freeze=True),
    commands=list(dict.fromkeys(manifest['commands']+['.venv/bin/python artifacts/stage9/reanalyze_history.py','.venv/bin/python scripts/run_stage9.py --allocation-check','.venv/bin/python artifacts/stage9/tables.py','MPLCONFIGDIR=/tmp/stage9-mpl ../llm-rankcloak/.venv/bin/python artifacts/stage9/plot.py','.venv/bin/python artifacts/stage9/finalize_manifest.py'])),
    paper_recommendation='Proceed to a narrowly scoped regular-paper draft; novelty and submission readiness unconfirmed; no additional experiments prescribed',remaining_parent=read(ART/'summary.json')['parent_remaining'])
(ROOT/'manifests/stage9_evidence.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status='PASS',unchanged_prior_files=len(base)-len(changed),attempts=len(manifest['attempts']),gpu_source=manifest['tested_revisions'],ledger_sha256=sha(ROOT/'artifacts/project_budget.jsonl'),new_inference=False),indent=2))
