# Public-key LLM steganography: Stage 1 foundations

Development-only implementation of HPKE-encrypted byte records carried by explicitly adapted Calgacus rank transcoding. Cryptographic confidentiality and text-transport correctness are separate from concealment. All contexts and model/configuration data are public. HPKE base mode does not authenticate senders.

Start with [STAGE1_FOUNDATIONS_REPORT.md](STAGE1_FOUNDATIONS_REPORT.md), [protocol](docs/protocol.md), [source audit](docs/source_audit.md), and [novelty matrix](docs/novelty_matrix.md). This stage does not run the full research program.

CPU setup (Python 3.10 as tested):

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements-cpu.lock
.venv/bin/python -m pytest -q
```

Local assets are reused read-only from `../llm-rankcloak`. The frozen `configs/local_runtime.json` identifies their paths and selected GPU. `configs/public_profile.json` binds model/tokenizer/native hashes and exact public settings. No cloud or paid inference is used; no weights are distributed. A differently located but identical backend can be configured locally; a different binary/model does not satisfy this profile.

```bash
.venv/bin/python scripts/run_smoke.py --max-new-cases 20
.venv/bin/python scripts/build_report.py
.venv/bin/python scripts/verify_evidence.py
```

The smoke command runs only previously unattempted cases. It never resets accounting or retries failed cases. Completed evidence is immutable; repeated invocation on a completed allocation does not spend GPU budget. The CPU tests rerun independently. See the report for the tested revision and exact recorded commands. A future independent GPU replication must retain the existing ledger and receive a separately identified allocation; do not delete the bundled ledger to evade the cumulative ceilings.

`artifacts/stage1/TEST_ONLY_keys.json` and published RFC vectors contain intentionally public test secrets, never deployment credentials. Receiver interfaces accept actual UTF-8 text and agreed public configuration, never encoder token IDs or rank traces.
