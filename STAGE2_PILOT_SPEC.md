# Authorized Stage 2 diagnostic pilot specification

The user authorized this fixed pilot from main `24fd553e6b79fcfdbe7dc6b6abca71cac440ea8a`. The prior requirement for another CPU test/static-check cycle is waived: reuse the 109-test reviewed foundation, perform only focused hardware/asset/accounting/allocation checks, then execute. Historical CPU results are not attributed to the new extension. Execution results belong in `STAGE2_PILOT_REPORT.md`. It is not the full research matrix. Engineering readiness is conditional; scientific novelty is unresolved. No comparator is assumed runnable because an interface exists.

## Questions and frozen method

1. Do the repaired reservation lease, absolute deadline, source/profile gate and cumulative accounting work with the actual local backend?
2. Do three previously successful saved UTF-8 carriers still decode in independent receiver processes, while a known drifted carrier remains rejected?
3. On four fresh encrypted development messages, where does text serialization fail, and does the public format check agree with the retained extraction?

Use only C2 (the existing full-vocabulary HPKE/Base64 Calgacus adapter) and C0 (ordinary full-vocabulary temperature-one model sampling). No new codec, token filtering, normalization, model, training, corpus search, cryptographic primitive, or detector is introduced. Reference notebook behavior was already inspected; this pilot adds no C1 examples. Arithmetic and keyed comparators remain out of scope until separately audited implementations exist.

The supported profile is exactly `configs/public_profile.json`: QuantFactory Meta-Llama-3-8B-Instruct Q4_K_M; GGUF SHA-256 `86c8ea6c8b755687d0b723176fcd0b2411ef80533d23e2a5030f845d13ab2db7`; embedded tokenizer hash `5c8950bef385be95db5feda8c8afadba6a5c0b903e6ceaa39efe6cfe3d84f3f3`; llama-cpp-python 0.3.23 and the recorded native binary hashes; NumPy 2.2.6; CUDA runtime 12.4. All inference remains on the recorded RTX 5000 Ada (32,760 MiB, driver 590.48.01). Hardware identity and binary hashes must be checked again before execution. Source context is `Canonical Base64 data:`; cover indices 0, 1, 2 are the exact garden, library and rainfall strings in the frozen profile. Use no chat template, batch/microbatch 1, serial prefill, cleared native/Python caches, float32-logit/ascending-ID tie order, full GPU offload and unchanged precision/determinism settings.

HPKE base mode uses the existing suite, 16-byte random message ID, u32 big-endian length and no padding. Source is canonical padded Base64 of the full encapsulation/ciphertext. Cryptographic randomness remains fresh OS/library randomness; sampling seeds are not cryptographic keys. Receivers take saved UTF-8, public settings and the test private key; expected hashes stay in the evaluator. Public observers take only public codec/text/context and cannot authenticate tags.

## Fixed allocation: at most 12 GPU cases

| Order / family | Count | Inputs and endpoints |
|---|---:|---|
| Mandatory historical successful replays | 3 | Fresh processes for original carrier attempts `bcb46cde-561b-48cb-ab40-73efd8b5dff4` (32 bytes, context 0), `e5f17a95-4bba-4511-bd77-d318cb600038` (128 bytes, context 1), and `28297d91-c3a6-4f08-b65f-4ad095921c28` (32 bytes, context 2). Compare payload hashes outside receivers. |
| Mandatory historical negative replay | 1 | Saved carrier `12de85ea-3e3e-4a4a-8997-27e551978366` (128 bytes, context 2). Record extracted bytes, framing rejection and trace divergence. Expected rejection is a diagnostic outcome, never counted as authenticated message recovery. |
| Fresh C2 transmissions | 4 | Two new independent test receiver keys A/B, each with 32 and 128 bytes. Fixed order/context: A32/0, A128/1, B32/2, B128/0. Encode, save exact UTF-8, receive, and run public extraction; all operations count within the same case. |
| Ordinary C0 controls | 2 | Contexts 0 and 1, matched to the first new C2 produced carrier in that context; if absent, use the preregistered 192-token fallback and label it unmatched. PCG64 seeds 2026091901 and 2026091902, temperature 1, full vocabulary, fixed token count, no EOS stop. Run public extraction. |
| Fresh-carrier independent receiver replays | Up to 2 | First successful new carrier for each new key in fixed order. Do not substitute another message for a failed attempt. Unavailable successes leave these slots unused. |

New payloads are synthetic binary development data: for new key index `u` in `{0,1}`, length `n` in `{32,128}`, byte `j` is `(167 + 29*u + 7*j + n) mod 256`. Freeze actual payload/context/key mappings before any inference. Test keys and carrier IDs are excluded from observer inputs. Four transmissions provide only two independent recipient keys, not four independent units. This allocation estimates no publication-grade detector rate or recovery interval.

Historical cases, new pilot payloads, keys, contexts, their families and resulting carriers are marked development-only and excluded from any final-test set. No final-test data is opened or selected during this pilot.

## Budgets, accounting and forecast

Additional pilot ceilings are **1,200 conservative GPU-job seconds (0.3334 hours), 8,000 charged model-evaluated tokens, and 12 cases**, stopping at whichever limit is reached first. These are ceilings, not targets. Tokens include source scoring, prefill, all receiver/public inversions, controls, warmups, failures and any attempted launch. There are no discretionary retries.

Carry forward the complete historical usage: 632.4426544 seconds, 10,230 tokens and 21 cases. Thus the combined upper bounds would be **1,832.4426544 seconds, 18,230 tokens and 33 cases**, also below the original 7,200-second / 25,000-token / 72-case global ceilings. An existing ledger must never be reinitialized at zero or its prior events removed.

Before execution, implement and inspect the smallest fixed-allocation controller needed for this specification; the completed Stage 1 controller does not implement this new allocation. Maintain one authoritative cumulative ledger, preserve the entire historical prefix, and enforce both global and pilot-delta ceilings before reservation. If moving the authoritative ledger to a project-level path to keep the original artifact file frozen, the migration must copy and verify the complete historical prefix/usage and retire the old launch path, with one shared lock and explicit migration evidence. The source review did not implement a migration or pilot runner; this authorized task adds that minimal extension.

Per-case reservation maxima: historical replays 60 seconds / 600 tokens each; fresh C2 120 seconds / 2,000 tokens each; controls 90 seconds / 1,200 tokens each; new receiver replays 60 seconds / 750 tokens each. These simultaneous worst-case token reservations exceed the pilot ceiling; admit jobs sequentially only when both remaining ceilings cover their full reservation. Settle observed usage after clean exit; abandoned attempts retain full reservations. Stop early rather than lower a required reservation or borrow from another allocation. The inherited deadline is eight seconds inside each wall reservation and is armed before expensive imports. No standalone ungoverned warmup or worker invocation is allowed.

Historical encrypted jobs took at most 49.6287 seconds including startup and, in that case, public inversion. A deliberately conservative forecast of 12 times that maximum with 50% contingency is about **893.3 seconds (0.2482 GPU-hours)**. Shorter replay jobs may reduce cost; the 1,200-second cap remains authoritative. These figures are conditional estimates for this profile and include failed cases; they are not a throughput forecast for unimplemented comparators.

## Gates and stopping rules

Before any GPU allocation: authorization is granted; freeze the new case manifest, source commit and both budget ceilings; perform the focused reservation-boundary check in place of the waived CPU/static-check rerun; verify unchanged model/tokenizer/native/CUDA hashes. Do not claim that the new live path has already passed.

Execute the four mandatory replay cases first. Require exact authenticated recovery for all three formerly successful carriers, expected rejection for the known drifted carrier, a distinct receiver PID, matching GPU UUID/full offload, accurate phase metering, a unique reservation/claim, clean process exit, and preserved original records. If any gate fails unexpectedly, stop the entire pilot before fresh cases. Authentication success on the known failed carrier also requires investigation rather than being silently called an improvement.

Stop all further GPU work on any budget breach, malformed accounting, missing outcome, lease/deadline failure, nonzero exit, timeout, missing GPU evidence or unexplained rank/numerical mismatch. Retain every attempt, including incomplete ones, and require manual review before resuming. An unexpected successful plaintext/hash mismatch is fatal. Categorize known transport/framing failures without erasing them.

Fresh serialization/capacity failures remain in intention-to-send denominators. If both 128-byte examples fail, exclude 128-byte expansion from any proposed later study until an explicitly different transport profile is reviewed. If fewer than two of four new transmissions recover exactly, end new-carrier work and recommend a transport-design review instead of a larger study. No repair/retry loop, parameter search or extra cases are permitted. Unused control/replay slots are reported as skipped by the stop rule, not successful cases.

Required failure categories: capacity exhaustion; tokenization/serialization drift (distinguish invalid UTF-8 from retokenization mismatch); rank/numerical divergence; framing failure; authentication failure; replay rejection; timeout/resource failure; implementation/provenance failure. Preserve primary cause and downstream rejection separately.

## Outputs and later-study decision

Use `artifacts/stage2_pilot/` only after authorization: frozen allocation and separation manifest; append-only immutable-ID cases; cumulative and pilot budget snapshots; exact source/dependency/configuration provenance; per-attempt commands/lease claims, saved text or invalid-byte hex, compact token/rank traces, payload/envelope hashes and lengths, receiver results, public-only observer outputs, phase timings and PID-specific VRAM/offload evidence. Link each outcome to its source commit and retain all failures. A pilot report must distinguish matched/unmatched controls, intended/attempted cases, expected rejection, authenticated recovery and independently checked equality.

A larger study remains stopped until serialization reliability or a deliberately negative research question is defensible, unexplained failures are absent, comparator implementations and secret-key assumptions are audited, latest-manuscript overlap/priority is cleared, and the measured forecast fits a separately approved budget. Passing this pilot would establish none of concealment, sender authentication, edit robustness or novelty by itself.
