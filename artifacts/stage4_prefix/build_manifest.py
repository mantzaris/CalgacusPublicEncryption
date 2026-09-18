#!/usr/bin/env python3
"""Hash and index Stage 4 evidence. No inference or budget writes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts/stage4_prefix'
TESTED = '32edd3bf54712a8134659f298b8958462024c2a0'
START = 'fe3aeaddd7df1d4fb3b19c49ccc84251a519d39f'
def read(p): return json.loads(p.read_text())
def meta(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
def write(name, value): (ART/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
records = [json.loads(l) for l in (ART/'cases.jsonl').read_text().splitlines()]
anchor = read(ART/'budget_anchor.json')
events = [json.loads(l) for l in (ROOT/anchor['path']).read_bytes()[anchor['bytes']:].splitlines()]
commands = [
    {'phase': 'focused_new_contracts_before_commit', 'command': 'PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_public_prefix.py -v > artifacts/stage4_prefix/focused_checks.txt 2>&1', 'output': 'focused_checks.txt', 'gpu_inference': False},
    {'phase': 'host_only_preparation_before_commit', 'command': '.venv/bin/python scripts/prepare_stage4.py > artifacts/stage4_prefix/preparation.txt', 'output': 'preparation.txt', 'gpu_inference': False},
    {'phase': 'focused_allocation_before_commit', 'command': '.venv/bin/python scripts/run_stage4.py --allocation-check > artifacts/stage4_prefix/allocation_check.txt', 'output': 'allocation_check.txt', 'gpu_inference': False},
    {'phase': 'fixed_gpu_allocation', 'command': '.venv/bin/python scripts/run_stage4.py > artifacts/stage4_prefix/controller.log 2>&1', 'output': 'controller.log', 'gpu_inference': True, 'tested_code_commit': TESTED},
    {'phase': 'artifact_only_reconciliation', 'command': '.venv/bin/python artifacts/stage4_prefix/reconcile.py > artifacts/stage4_prefix/reconciliation.txt 2>&1', 'output': 'reconciliation.txt', 'gpu_inference': False},
    {'phase': 'evidence_index', 'command': '.venv/bin/python artifacts/stage4_prefix/build_manifest.py', 'output': 'evidence_manifest.json', 'gpu_inference': False},
]
write('commands.json', {'schema_version': 1, 'cwd': str(ROOT), 'commands': commands,
    'note': 'Precommit focused checks and preparer used files subsequently frozen unchanged in tested commit. GPU attempts independently record their exact command, environment and clean source revision. Completed allocation cannot be implicitly rerun.'})
source_paths = ['src/llm_stego_public_key/evaluation/public_prefix.py', 'scripts/gpu_prefix_worker.py',
    'scripts/prepare_stage4.py', 'scripts/run_stage4.py', 'tests/test_public_prefix.py',
    'src/llm_stego_public_key/codecs/public_utf8_rank16.py', 'src/llm_stego_public_key/codecs/llama_backend.py',
    'src/llm_stego_public_key/codecs/calgacus.py', 'src/llm_stego_public_key/evaluation/budget.py',
    'src/llm_stego_public_key/evaluation/worker_lease.py', 'src/llm_stego_public_key/profile.py',
    'scripts/run_smoke.py', 'scripts/run_pilot.py', 'scripts/gpu_worker.py',
    'configs/public_utf8_rank16_v1.json', 'configs/public_profile.json', 'configs/local_runtime.json',
    'docs/public_prefix_observer.md', 'pyproject.toml', 'requirements-cpu.lock']
sources = []
for path in source_paths:
    frozen = subprocess.check_output(['git', 'show', TESTED+':'+path], cwd=ROOT)
    assert frozen == (ROOT/path).read_bytes(), path
    sources.append(dict(meta(ROOT/path), source_revision=TESTED))
attempts = []
for r in records:
    d = ROOT/r['evidence_dir']
    inputs = [meta(d/'input.json'), meta(ROOT/'configs/public_utf8_rank16_v1.json'), meta(ROOT/'configs/local_runtime.json')]
    if r['kind'] == 'prediction':
        inputs += [dict(meta(ROOT/h['path']), role='historical UTF-8 opened only after public prediction') for h in r['historical_reanalysis']]
    else:
        inputs.append(dict(meta(ROOT/r['prediction_path']), role='cached public observer prediction, not generator input'))
    attempts.append({'attempt_id': r['attempt_id'], 'case_id': r['case_id'], 'kind': r['kind'],
        'tested_code_commit': r['tested_code_commit'], 'inputs': inputs, 'command': meta(d/'command.json'),
        'outputs': [meta(p) for p in sorted(d.iterdir()) if p.is_file() and p.name not in ['input.json', 'command.json']],
        'derived_result_index': 'artifacts/stage4_prefix/cases.jsonl',
        'payload_key_or_authentication_input': False})
references = ['STAGE4_PREFIX_REPORT.md', 'docs/novelty_matrix.md', 'manifests/related_materials.json',
    'manifests/environment.json', 'artifacts/project_budget.jsonl', 'artifacts/project_budget.checkpoint.json',
    'STAGE3_TRANSPORT_REPORT.md', 'artifacts/stage3_transport/cases.jsonl']
files = [p for p in ART.rglob('*') if p.is_file() and p.name != 'evidence_manifest.json' and '__pycache__' not in p.parts]
manifest = {'schema_version': 1, 'repository': 'https://github.com/mantzaris/CalgacusPublicEncryption',
    'branch': 'main', 'starting_commit': START, 'starting_working_tree': 'clean', 'gpu_tested_code_commit': TESTED,
    'evidence_commit': 'Containing commit; determine with git log -1 -- artifacts/stage4_prefix/evidence_manifest.json',
    'split': 'development_only_excluded_from_future_heldout',
    'execution_window_utc': [datetime.datetime.fromtimestamp(events[i]['time_unix'], datetime.timezone.utc).isoformat() for i in (0,-1)],
    'frozen_sources_and_configuration': sources, 'attempts': attempts,
    'artifact_files': [meta(p) for p in sorted(files)], 'linked_references_and_ledger': [meta(ROOT/p) for p in references],
    'result_links': {
        'structural_framing': ['src/llm_stego_public_key/codecs/public_utf8_rank16.py', 'tests/test_public_prefix.py', 'artifacts/stage4_prefix/focused_checks.txt'],
        'predictions_and_probabilities': ['artifacts/stage4_prefix/public_predictions.json', 'artifacts/stage4_prefix/cases.jsonl'],
        'control_outcomes_and_exact_snippets': ['artifacts/stage4_prefix/control_outcomes.json', 'artifacts/stage4_prefix/cases.jsonl'],
        'historical_acceptance_only': ['artifacts/stage4_prefix/historical_reanalysis.json'],
        'resource_totals': ['artifacts/stage4_prefix/summary.json', 'artifacts/stage4_prefix/run_status.json', 'artifacts/project_budget.jsonl'],
        'reconciliation': ['artifacts/stage4_prefix/reconciliation.json', 'artifacts/stage4_prefix/reconciliation.txt', 'artifacts/stage4_prefix/reconcile.py'],
        'commands': ['artifacts/stage4_prefix/commands.json']},
    'self_hash_excluded': True,
    'limitations': ['Historical carrier recovery belongs to its original Stage 3 source revision.',
        'Observer acceptance is not ciphertext authentication.', 'Preexisting CPU suites not rerun or attributed to Stage 4.',
        'No new private keys or encrypted transmissions; public predictions and control snippets only.']}
write('evidence_manifest.json', manifest)
print(json.dumps({'manifest': 'artifacts/stage4_prefix/evidence_manifest.json', 'attempts': len(attempts), 'artifact_files': len(files), 'tested_source': TESTED}))
