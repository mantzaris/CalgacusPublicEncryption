# Stage 1 source audit

## Evidence boundaries and starting state

The starting repository at `7d5b2dce89b8c7463f04b3b4c7980b6b1e19dddb` on `main` contained only `LICENSE`. The user supplied an untracked research plan, read completely and preserved byte-for-byte; its original hash and git state are in `manifests/starting_state.json`. No supplied results or existing project implementation were present. Related repositories were read without modification. No previous numerical result is counted as reproduced here.

## Calgacus primary sources

Paper: [arXiv:2510.20075v6](https://arxiv.org/abs/2510.20075v6), January 16, 2026, Norelli and Bronstein. Sections 3, 3.1 and Appendix A describe conditional rank transfer, contextual reconstruction, dependence on inference conditions, and predictability/fluency limits. The high-entropy hash example and rank/probability mismatch are prior observations. The paper does not establish the cryptographic security of this project's composition.

Official repository: [noranta4/calgacus](https://github.com/noranta4/calgacus/tree/116123d4b7a74b3d56d15623355f9acf32a87165), commit `116123d4b7a74b3d56d15623355f9acf32a87165`, MIT. Exact notebook, README and LICENSE are in `vendor/calgacus/`; SHA-256 hashes are in `manifests/upstream_sources.json`. All source cells were inspected. Saved notebook displays are upstream demonstrations, not new results. Only the two audited cell-10 function definitions are executed by our reference harness; install/download cells and example presets are never executed.

The README recommends NVIDIA Ada and `llama-cpp-python==0.3.12` for exact paper stegotexts. The current notebook installation cell instead pins **0.3.16** (cu121 wheels). Imports require NumPy and huggingface_hub, without notebook pins. Its selected default is Gradient Llama-3-8B-Instruct-1048k Q6_K. Other models are selectable. The local supported model here is a different Llama-3-8B-Instruct Q4_K_M artifact with backend 0.3.23. Neither reference cases nor the adapter reproduce the paper's exact numerical environment.

| Contract | Actual notebook cell 10 / cell 8 | Supported adapted profile |
|---|---|---|
| Contexts | Source default `Some English text:`; UI default `A text:`; cover is selected prompt; optional source prefix | Explicit public Base64 source context and three frozen cover contexts |
| Tokenization | `tokenize(prompt)[1:]`; `tokenize(' '+text)[1:]`; assumes initial BOS | One BOS for context; source/carrier separately tokenized without BOS or special-token interpretation |
| Special tokens | Full model vocabulary; no explicit exclusion or EOS stop | Full vocabulary, no exclusion; render special markers explicitly, record any resulting retokenization failure |
| Ranks | One-based; evaluate token then read preceding score; `argsort(logits)[::-1]` | One-based; read preceding logits then evaluate token; same conditional rank concept |
| Ties | NumPy default sort, no declared stable total order | Descending native float32 logits, then ascending token ID; explicit departure |
| Precision | Quantized selectable GGUF; unstabilized exponentiation used only for logged probabilities | Q4_K_M weights; native float32 logits; no softmax needed for rank order; float64 stable softmax for controls |
| Cache/state | `model.reset()`; prompt evaluated in one call; no explicit native cache clearing | Reset plus `kv_cache_clear`; single-token prefill and replay, batch/microbatch 1 |
| Inference | 4096 context, full GPU offload, flash attention, seed 1337 | 2048 context, full GPU offload, no flash attention, graphs/fusion disabled, forced cuBLAS compute32F, seed 1337 |
| Serialization | Ignore invalid source UTF-8; decode prompt+generated tokens, remove prompt by character length, `.strip()`; fallback display on decode error | Strict UTF-8; detokenize only carrier tokens; no stripping, added spaces, normalization or replacement decoding |
| Length | Exactly rank-count iterations; no token cap inside functions, rank lower bound unchecked | 512 source/received-token cap, 65,536-byte transport cap; model context checked; no EOS stopping or tail |
| Receiver | Retokenizes displayed text with inserted leading space | Reads actual UTF-8 bytes; retokenizes independently; no saved IDs/ranks/state input |

The adapted full-vocabulary encoder deliberately does **not** repair text ambiguity by filtering or normalizing. A carrier whose retokenization differs is retained, its first differing token recorded, and it remains a failure even if an inner cryptographic check happens to succeed. Invalid UTF-8 bytes are retained as diagnostic hex and do not become a transmitted text success. Reference functions retain upstream semantics, but the local runtime changes remain explicitly labelled.

## Reuse from local projects

RankCloak commit `ce853d42d6ba64065cb63c6bdfc0d825c62734cd`, MIT: inspect `rankcloak/model_io.py` (CUDA library preload, reset plus native cache clear, exact-byte tokenization) and `revision_runner.py` (descending-logit/ascending-ID rank convention). Those small implementation practices are reused in the isolated adapter, with attribution in `THIRD_PARTY_NOTICES.md`; its large experiment framework and token-ID receiver are not imported. Its existing model and CUDA-enabled environment are reused read-only. The cross-modal manuscript's saved-artifact boundary and source/receiver separation inform the design; its coding/filtering algorithms are not silently substituted for Calgacus.

## HPKE library audit

Selected library: **pyhpke 0.6.5**, MIT, with **cryptography 46.0.7**. Upstream inspected commit and installed-source hashes are in the provenance manifest. This is an established implementation, not a claim of independent third-party security certification. Its `CipherSuite.new` forms the RFC suite ID; `kem.py` handles DHKEM context `enc || pkR`; `kdf.py` applies `HPKE-v1` labels; `cipher_suite.py` constructs the base-mode key schedule; `encryption_context.py` XORs the internally derived base nonce with the sequence number; `recipient_context.py` returns only after AEAD open succeeds. X25519 and ChaCha20-Poly1305 use PyCA cryptography. One new context per message uses sequence zero. No application nonce is invented.

The library's high-level `CipherSuite.seal/open` methods are stubs. We use `create_sender_context(...).seal` and `create_recipient_context(...).open`. No PSK or sender key is passed, selecting mode zero. Deterministic ephemeral keys are used **only** inside the published-vector tests. Normal sends rely on the library's OS-random ephemeral key generation and OS-random 16-byte message IDs.

Vector provenance: [RFC 9180 Appendix A.2.1](https://www.rfc-editor.org/rfc/rfc9180.html#appendix-A.2.1) and the [CFRG vector source](https://github.com/cfrg/draft-irtf-cfrg-hpke/blob/b1f7cb0cdeab6906c61b3d6574e8bdfdbe1cd3fb/test-vectors.json). The exact `(mode, kem, kdf, aead)=(0,32,1,3)` entry is retained, including 257 sequential ciphertexts and exporter vectors. Tests compare published key derivation, encapsulation, shared secret, nonce, ciphertexts and exported bytes; receiver tests open the published ciphertexts directly. This tests the chosen suite, not every HPKE mode or all possible inputs.

## Backend provenance limits

The frozen profile hashes every local llama.cpp shared library and the complete GGUF. The tokenizer hash separately covers every embedded `tokenizer.*` metadata field with explicit length framing. Package versions, host inventory, CUDA library hashes and native system-info output are retained. The preinstalled wheel has no `direct_url.json`; its exact llama.cpp submodule/build source commit cannot be established from installation metadata. Binary hashes and reported build flags identify the tested backend, but reconstructing that binary from source remains unresolved. Do not silently substitute a different wheel of the same Python version.
