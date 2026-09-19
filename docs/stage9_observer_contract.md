# Stage 9 public observer contract

`observe_stage9(transmitted_utf8, public_profile, cover_context, model, token_attributes)` receives no private key, payload, encoder state/trace, seed, label, or authentication outcome. Public size100 bytes is in the profile, not supplied by an evaluator. Its single metered scoring pass reconstructs candidates from the actual text prefix using the existing admission function. Generation trace is output for the evaluator only.

It bounds input bytes/token count; invalid UTF8 and unscorable count receive explicit statuses and downstream unavailable predicates. Canonical bytes require exact detokenization of received tokenization. Membership covers the whole received sequence. Arithmetic accumulation stops internally at the first complete prefix; trailing tokens remain scored and are not discarded from message-boundary acceptance.

Predicates:

1. `valid_utf8`, `canonical_bytes`: received serialization only.
2. `all_candidates_member`: every received token in its conditional16.
3. `stable_target_reached`: at least800 stable bits; pending bits do not count.
4. `first_completion_token`: one-based prefix position, null if incomplete.
5. `ends_at_first_completion`: exact received boundary; null if incomplete.
6. `filler_consistent`: excess released bits equal prefix of1 then zeros; with no excess, vacuously true.
7. `canonical_replay_consistent`: re-encode recovered100 bytes through the first-complete public integer tables and compare every symbol and completion. Independent of local filler verdict, uses no further inference.
8. `kem_canonical`: first32 recovered bytes interpreted little-endian are <2^255−19. Computable on stable bytes even if filler/replay/boundary fails. This necessary honest-output convention is not key validity or authentication.

`format_accepted` requires1–7; `format_and_kem_canonical` additionally8. Failures remain separate. Later predicates are null with `unavailable_reasons` when missing stable bytes or malformed earlier input; aggregate rejection is not evidence each component rejected. An invalid choice before completion blocks extraction; invalid trailing choices still fail full membership. All bytes and decoded envelopes remain unauthenticated public candidates.

`decompose_public_symbols` is an internal pure-integer component consuming only the public scoring pass's reconstructed tables. Offline invocation on retained public scoring tables is explicitly trace-only reanalysis. It is not the wire observer's interface and does not accept an encoder trace or plaintext. Receiver remains the established actual-text `receive_envelope_text`; authentication and authenticated inner-length validation precede payload delivery.

B-stop's `FirstCompletion` only advances decoder state and latches the first target event. It does not call `finish`, replay, KEM, or HPKE. The public observer runs afterward only on delivered messages. Control seeds reside outside this interface. All three model generators/transport define explicit different finite-message distributions; none is asserted to model human traffic.
