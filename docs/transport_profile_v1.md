# public_utf8_rank16_v1: bounded public rank-based transport comparator

This is an explicitly different transport profile, not unmodified Calgacus, a new public-key encryption primitive, a provably secure stegosystem or an established novel contribution. The baseline codec and `configs/public_profile.json` remain unchanged. The profile is registered by exact canonical-JSON SHA-256 in `profile.py`; arbitrary profile variants are rejected. All policy below is bound by HPKE through the existing `Binding.from_profile` information and associated-data mechanism for fresh encrypted cases.

## Frame and public selection

The input is the complete raw HPKE encapsulation plus ciphertext/tag, **68..196 bytes**. Frame it as `envelope_length_u32be || envelope`. No magic, padding, normalization, Base64 carrier, EOS terminator or out-of-band length is used. Each byte becomes its most-significant nibble then least-significant nibble, each in 0..15. The existing Base64 serializer/deserializer is only an internal bridge to the unchanged HPKE wrapper.

Begin with the existing separately tokenized public cover context, including its context BOS, and clear both Python/native caches. At each carrier position:

1. Read native float32 logits under the cover context and previously emitted token IDs. Reuse the existing full descending-logit / ascending-token-ID tie order.
2. Examine at most the first **128** ranked IDs. Exclude llama.cpp attributes UNKNOWN, UNUSED, CONTROL or USER_DEFINED (mask **27**) and empty singleton emitted bytes. Normal/byte vocabulary entries, including ordinary whitespace, remain eligible subject to the full-prefix check.
3. Detokenize the **entire proposed carrier prefix** using the existing exact-byte detokenizer. Admit only strict UTF-8 whose exact, no-BOS/no-special-interpretation tokenization is the proposed ID sequence. No stripping, replacement decoding, concatenation approximation or normalization is allowed.
4. Take the first **16** admitted IDs in that rank order, stopping the scan when 16 are found. Nibble `n` selects ID `eligible[n]`. Fewer than 16 is a capacity/admissibility failure; do not enlarge the pool, change radix, substitute a candidate policy or retry.

Candidate checks do not evaluate speculative tokens. Only the selected/received token is advanced through the existing metered GPU model. The final selected token is evaluated too and charged. Attribute and singleton-byte caches contain only public vocabulary metadata; prefix admissibility is always recomputed from full bytes. Candidate traces record the capped support, scanned count, rejection counts and ordered-list digest; they are diagnostics outside the decoder interface. Capped support 16 means at least 16 found, not exactly 16 eligible in the whole top-128 pool.

## Receiver, bounds and termination

`PublicUtf8Rank16Codec` implements `PublicEnvelopeCodec.embed/extract`. A decoder accepts transmitted bytes, public profile and cover context; its public model/token metadata are its only other inputs. It never accepts encoder IDs/ranks, saved caches, original envelopes, evaluator lengths or expected hashes.

Before inference, require strict UTF-8, at most **65,536 bytes**, at most **512 received tokens**, and byte-exact detokenization of the received canonical token sequence. Require at least eight tokens for the header. Reset the model under the cover context. At every received token, recompute the same eligible list from the preceding prefix and derive the nibble from the token's position; reject tokens outside this list.

Accumulate only the four fixed header bytes initially. After eight valid header symbols, interpret the unsigned big-endian length and require 68..196. Require the actual received token count to equal `2 * (4 + length)` before allocating the bounded envelope buffer. Reject a partial header, truncated body, trailing symbols, out-of-range header and invalid token choice. There is exactly one even-length, unpadded representation per selected token sequence. The decoded envelope is delivered to unchanged HPKE authentication/record parsing through canonical serialization; plaintext is delivered only after successful authentication and replay handling.

The existing context limit stays **2,048 tokens**, with 512 carrier tokens and 65,536 transport bytes unchanged. The largest supported frame is 200 bytes / **400 carrier tokens**. A 32-byte payload has a 100-byte envelope and requires **208 carrier tokens**; 128 bytes gives a 196-byte envelope / **400 tokens**. Analytical net payload rates are respectively **256/208 = 1.230769...** and **1024/400 = 2.56 bits/token**; the frame carries four bits/token including header and HPKE overhead. Measured text bytes, evaluated tokens and wall time are separate quantities.

## Conditional correctness and limitations

Inductively, every admitted carrier prefix is a canonical tokenization of its own emitted UTF-8. Thus tokenizing the final transmitted bytes recovers the emitted IDs. Given identical public context, model/tokenizer, cache handling and conditional candidate ordering, the decoder starts with the same prefix, obtains the same first 16 eligible IDs, and recovers each nibble. Length validation then recovers the exact framed envelope. This assumes reproducible conditional ordering across the frozen numerical backend, including cutoff ordering. Stable tie handling alone cannot guarantee cross-backend numerical agreement. Fresh-process replays test selected executions, not all environments.

The constrained emission policy changes the carrier distribution, fluency and capacity relative to full-vocabulary Calgacus or ordinary generation. Candidate exhaustion may occur even when individual prefixes are canonical. Structured header symbols and public constrained support may be recognizable. This invariant is an exact-transport argument, not concealment, cryptographic-security, edit-robustness or novelty evidence. HPKE base mode does not authenticate senders; other public senders can create valid fresh ciphertexts.

## Reuse and qualification

ImageCalgacus `2bec65dbe5509623f6658d8a231ec93f6d579b4e`: inspected `text_backend.py` full-prefix consistency and attribute mask, and `fixed_rank.py` nibble mapping. Adapted these small MIT helpers with full-prefix detokenization, zero-based symbols, top-128/first-16 ordering and bounded public framing. Its probability filter, top-256 policy, static filter and expected-length decoder are not imported. RankCloak `ce853d42d6ba64065cb63c6bdfc0d825c62734cd`: inspected `model_io.py` and `rankcloak/revision_runner.py`; reuse the already-attributed exact tokenization, cache clearing and stable rank ordering in this repository. Actual inspected file hashes and local tree states are recorded in the Stage 3 environment artifact. See `THIRD_PARTY_NOTICES.md` and retained MIT licenses. No broad literature/novelty audit was performed.

The two historical envelopes are codec fixtures only. They remain encrypted under their historical profile and are not authenticated by the new profile. New carriers do not repair the old carriers. Fresh transmissions use new random recipient keys and fresh HPKE randomness under the entire new profile. Public observers receive only codec, UTF-8, profile and context; they inspect framing and envelope bounds, never private keys or tag authentication.

The frozen ten-case order and payloads are in `artifacts/stage3_transport/allocation.json`: two fixtures, A32/0, A128/1, B32/2, B128/0, then two 128-byte fresh-process replays, then two matched ordinary controls. Payload byte `j` is `(193 + 31*u + 11*j + n) mod 256`. Control PCG64 seeds are 2026092001 and 2026092002, full-vocabulary temperature-one sampling, fixed token count, no EOS stop. Ordinary generation and constrained comparator emission define different distributions. All cases are development-only and excluded from future held-out evaluation.

Full reservations: fixtures 140 s/900 tokens each; 32-byte fresh cases 120 s/750 tokens; 128-byte fresh cases 160 s/1,300 tokens; replays 80 s/450 tokens; controls 100 s/900 tokens. Both the additional 1,200 s/8,000 evaluated-token/10-case ceilings and existing 7,200 s/25,000-token/72-case ceilings are enforced on the same ledger. Stop before a full reservation cannot fit. Abandoned attempts keep conservative charges. Fixture or non-control failure stops this qualification, including invariant and capacity failures. Control format rejection is expected; any accounting, lease, timeout, provenance, numerical or implementation failure stops all GPU work. There are no retries, profile searches or substitutions.

Focused verification command (existing environment, only the new codec file):

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_public_utf8_rank16.py -v
.venv/bin/python scripts/run_stage3.py --allocation-check
```

Historical CPU test results are reused but not attributed to this new codec. No full CPU suite, lint/formatting sweep, benchmark or backend rebuild is part of this allocation.
