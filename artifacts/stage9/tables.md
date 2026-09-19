# Stage9 derived tables

## Attempt and delivery denominators

| Group | Attempted | 800-bit complete | Delivered/scorable | Exact authenticated | Capacity aborts |
| --- | --- | --- | --- | --- | --- |
| B-fixed | 6 | 0 | 6/6 | 0 | 0 |
| B-stop | 6 | 3 | 3/3 | 0 | 3 |
| R | 6 | 4 | 4/4 | 4 | 2 |

B-fixed complete means800 stable bits, distinct from successfully emitting its assigned length. B-stop/R capacity aborts have no delivered-message observer. Controls are never privately authenticated.

## Per-context prospective outcomes

| Context | R outcome/tokens | B-fixed length | Fixed first800 | B-stop emitted | Stop first800 | Fixed format | Stop format | Stop filler | Stop replay | Stop KEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | exact/862 | 862 | NA | 1984 | NA | fail | NA | NA | NA | NA |
| 1 | exact/752 | 752 | NA | 1186 | 1186 | fail | fail | fail | fail | pass |
| 2 | capacity_exhaustion | 1984 | NA | 1984 | NA | fail | NA | NA | NA | NA |
| 3 | exact/905 | 905 | NA | 1052 | 1052 | fail | fail | pass | fail | fail |
| 4 | capacity_exhaustion | 1984 | NA | 1984 | NA | fail | NA | NA | NA | NA |
| 5 | exact/832 | 832 | NA | 1044 | 1044 | fail | fail | fail | fail | fail |

## Separate public predicates

| Group | Predicate | True | False | Unavailable | Scorable denominator |
| --- | --- | --- | --- | --- | --- |
| B-fixed | all_candidates_member | 6 | 0 | 0 | 6 |
| B-fixed | canonical_bytes | 6 | 0 | 0 | 6 |
| B-fixed | canonical_replay_consistent | 0 | 0 | 6 | 6 |
| B-fixed | ends_at_first_completion | 0 | 0 | 6 | 6 |
| B-fixed | filler_consistent | 0 | 0 | 6 | 6 |
| B-fixed | format_accepted | 0 | 6 | 0 | 6 |
| B-fixed | format_and_kem_canonical | 0 | 6 | 0 | 6 |
| B-fixed | kem_canonical | 0 | 0 | 6 | 6 |
| B-fixed | stable_target_reached | 0 | 6 | 0 | 6 |
| B-fixed | valid_utf8 | 6 | 0 | 0 | 6 |
| B-stop | all_candidates_member | 3 | 0 | 0 | 3 |
| B-stop | canonical_bytes | 3 | 0 | 0 | 3 |
| B-stop | canonical_replay_consistent | 0 | 3 | 0 | 3 |
| B-stop | ends_at_first_completion | 3 | 0 | 0 | 3 |
| B-stop | filler_consistent | 1 | 2 | 0 | 3 |
| B-stop | format_accepted | 0 | 3 | 0 | 3 |
| B-stop | format_and_kem_canonical | 0 | 3 | 0 | 3 |
| B-stop | kem_canonical | 1 | 2 | 0 | 3 |
| B-stop | stable_target_reached | 3 | 0 | 0 | 3 |
| B-stop | valid_utf8 | 3 | 0 | 0 | 3 |
| R | all_candidates_member | 4 | 0 | 0 | 4 |
| R | canonical_bytes | 4 | 0 | 0 | 4 |
| R | canonical_replay_consistent | 4 | 0 | 0 | 4 |
| R | ends_at_first_completion | 4 | 0 | 0 | 4 |
| R | filler_consistent | 4 | 0 | 0 | 4 |
| R | format_accepted | 4 | 0 | 0 | 4 |
| R | format_and_kem_canonical | 4 | 0 | 0 | 4 |
| R | kem_canonical | 4 | 0 | 0 | 4 |
| R | stable_target_reached | 4 | 0 | 0 | 4 |
| R | valid_utf8 | 4 | 0 | 0 | 4 |

## Complete-message raw scores

| Case | Tokens | UTF8 bytes | NLL bits/token | Mean log2 rank | Admissible NLL bits/token |
| --- | --- | --- | --- | --- | --- |
| R-c0 | 862 | 3909 | 0.9701 | 0.3417 | 0.9306 |
| B-fixed-c0 | 862 | 2457 | 0.2938 | 0.0998 | 0.2746 |
| R-c1 | 752 | 3297 | 1.1131 | 0.3859 | 1.0656 |
| B-fixed-c1 | 752 | 3175 | 0.6337 | 0.2092 | 0.5997 |
| B-stop-c1 | 1186 | 5297 | 0.7027 | 0.2293 | 0.6771 |
| B-fixed-c2 | 1984 | 9863 | 0.3469 | 0.1241 | 0.3318 |
| R-c3 | 905 | 4489 | 0.9052 | 0.3124 | 0.8854 |
| B-fixed-c3 | 905 | 4128 | 0.8259 | 0.2847 | 0.8136 |
| B-stop-c3 | 1052 | 4819 | 0.7730 | 0.2681 | 0.7623 |
| B-fixed-c4 | 1984 | 8294 | 0.3230 | 0.1196 | 0.3119 |
| R-c5 | 832 | 3748 | 0.9943 | 0.3335 | 0.9674 |
| B-fixed-c5 | 832 | 4187 | 0.8762 | 0.3078 | 0.8572 |
| B-stop-c5 | 1044 | 5272 | 0.7962 | 0.2815 | 0.7802 |

These are canonical-token path scores, not UTF8-string probabilities. No absent/aborted message is assigned a score. Higher-is-R orientations remain fixed.

## Inclusive resource costs

| Group | Attempted | Mean job seconds | Mean encode/generate seconds | Mean observer seconds | Observer passes | Evaluated tokens |
| --- | --- | --- | --- | --- | --- | --- |
| R | 6 | 141.5975 | 73.7369 | 39.6502 | 4 | 14147 |
| B-fixed | 6 | 157.4314 | 70.5459 | 71.5143 | 6 | 14746 |
| B-stop | 6 | 137.8852 | 93.9481 | 56.5812 | 3 | 12597 |

Job and generation means include failures; observer mean is conditional on an actual pass. Startup, receiver and shutdown are included in full jobs.
