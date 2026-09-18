# Public protocol v1

This is an experimental transport contract, not a deployment recommendation. `configs/public_profile.json` is the agreed public configuration; `configs/local_runtime.json` contains machine paths and the selected GPU. Paths are not secret and do not contribute to confidentiality.

## Cryptographic record and envelope

Maximum application payload: **128 bytes**, including empty and arbitrary non-text bytes. Padding policy: **none in v1**. The inner record is exactly:

```
random_message_id[16] || unsigned_payload_length[4, big-endian] || payload[length]
```

The length must equal the remaining authenticated record length. No allocation uses this field before validating it against the 128-byte maximum and available bytes. No trailing bytes are allowed. A future padding policy requires a distinct bound profile/version.

Suite: HPKE base mode (0), DHKEM(X25519, HKDF-SHA256) (0x0020), HKDF-SHA256 (0x0001), ChaCha20-Poly1305 (0x0003). The library creates fresh encapsulation randomness for every send. Wire source bytes are `enc[32] || ciphertext || tag[16]`. There is no clear message header or transmitted nonce. Envelope size is payload+68 bytes: 68, 100, 196 bytes for payloads 0, 32, 128. Standard canonical padded RFC 4648 Base64 yields 92, 136, 264 ASCII characters respectively.

The Base64 parser bounds character count before conversion/decoding, permits only the standard alphabet, and compares canonical re-encoding to reject alternate pad bits, extra padding, whitespace, URL-safe variants or omitted padding. Total decoded size must be 68..196 bytes. A syntactically valid envelope is not an authenticated message.

## Binding

Let `J` be ASCII UTF-8 JSON generated with sorted keys, separators `(',', ':')`, `ensure_ascii=True`, and no NaN, from:

```
{"profile": <complete public profile>, "cover_context": <selected exact public string>}
```

Only one of the frozen cover strings may be selected. `info` is the ASCII bytes `ICISSP2027/HPKE/info/v1`, then NUL, then the 4-byte big-endian byte length of `J`, then `J`. AEAD associated data are ASCII `ICISSP2027/HPKE/envelope/v1`, NUL, then SHA-256(J). The binding snapshots immutable bytes. It binds protocol, suite, record format, no-padding policy, payload/token limits, full model/tokenizer/library hashes, inference/token-order settings, source context, complete context set and exact selected cover context. All these fields are public. Recipient public key binding also occurs inside the DHKEM key schedule.

## Text transport

The sender tokenizes canonical Base64 without BOS and without special-token interpretation, extracts its conditional ranks after the agreed source context, and generates the same number of tokens after the cover context. Both contexts consist of one explicit model BOS followed by separately tokenized context bytes. No chat template applies. Ranks use every vocabulary token, descending native logits and ascending token ID on exact ties.

The transmitted object is exactly the detokenized carrier UTF-8 file, without a newline added by the harness. Special-token rendering is enabled; source/carrier tokenization still treats marker strings as ordinary text. Invalid UTF-8 is rejected and diagnostic bytes retained. No strip, whitespace cleanup, Unicode normalization, padding tail or token filter is applied. EOS is an ordinary ranked token and does not terminate encoding. The receiver determines iteration count from the tokenization of the received file, not an out-of-band token count or saved encoder vector.

`receive(transmitted_utf8, private_key, binding, cover_context, codec, replay)` reconstructs a candidate Base64 envelope from received text, checks framing, authenticates using HPKE, validates the authenticated inner record and atomically records its message ID before delivering payload bytes. The receiver has no expected payload/hash, token IDs, ranks or encoder state. Encoder and receiver traces are separate evaluator output. Text retokenization disagreement is an explicit failure; the evaluator can explain it using traces the receiver never receives.

The GPU loader validates the complete model and backend native hashes and pinned runtime package versions. Rank sequences reset both Python token state and native KV state. Every eval uses a single token including context prefill. Model loading, all reconstruction, scoring and observer calls are governed.

## Failure and replay semantics

Framing, serialization, rank/numerical, capacity, authentication, replay, and timeout/resource failures are separate evidence categories. No unauthenticated plaintext is returned, printed, cached as a delivered ID, or supplied to a record consumer. Detailed diagnostics are for this offline study, not a hardened network error protocol.

Replay state is a SQLite table keyed by `(recipient_public_key || binding_digest, authenticated_message_id)`. `BEGIN IMMEDIATE` and a unique primary key provide atomic first delivery across cache instances. Authentication and inner parsing precede insertion. State persists when a file path is used; in-memory state is used only for isolated tests/cases. No expiry or eviction occurs. At 10,000 entries new deliveries fail closed; operational lifecycle and denial-of-service policy are future work. Crash after committing a replay ID but before application receipt provides at-most-once delivery, not guaranteed delivery. Restoring or losing the cache changes replay guarantees.

Base mode does **not** authenticate a sender. Anyone with the public key can send a fresh valid message, including a replacement with a new message ID. Such a message is not an AEAD forgery. Authenticated recipient-key distribution is assumed externally.
