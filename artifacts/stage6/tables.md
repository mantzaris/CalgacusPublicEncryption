# Retained Stage 6 results

## Attempt-level recovery and useful rate

| Method | Payload bytes | Exact / attempted | Mean useful bits/token over attempts | Mean successful bits/token |
|---|---:|---:|---:|---:|
| L | 32 | 8/8 | 1.2308 | 1.2308 |
| L | 128 | 8/8 | 2.5600 | 2.5600 |
| F | 32 | 8/8 | 1.2800 | 1.2800 |
| F | 128 | 8/8 | 2.6122 | 2.6122 |
| Calgacus | 32 | 2/4 | 1.3011 | 2.6023 |
| Calgacus | 128 | 2/4 | 2.7177 | 5.4355 |

## Recognition (matched, scorable delivered pairs)

| Method | Control | Score | Pairs | AUC | Cluster interval |
|---|---|---|---:|---:|---|
| L | A | prefix_match | 16 | 0.9688 | [0.875, 1.0] |
| L | A | format_accepted | 16 | 1.0000 | [1.0, 1.0] |
| L | A | format_and_kem_canonical | 16 | 1.0000 | [1.0, 1.0] |
| L | A | mean_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| L | A | encrypted_body_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| L | A | token_count | 16 | 0.5000 | [0.5, 0.5] |
| L | B | prefix_match | 16 | 0.9688 | [0.875, 1.0] |
| L | B | format_accepted | 16 | 1.0000 | [1.0, 1.0] |
| L | B | format_and_kem_canonical | 16 | 1.0000 | [1.0, 1.0] |
| L | B | mean_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| L | B | encrypted_body_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| L | B | token_count | 16 | 0.5000 | [0.5, 0.5] |
| L | C | prefix_match | 16 | 1.0000 | [1.0, 1.0] |
| L | C | format_accepted | 16 | 1.0000 | [1.0, 1.0] |
| L | C | format_and_kem_canonical | 16 | 1.0000 | [1.0, 1.0] |
| L | C | mean_nll_bits | 16 | 0.4219 | [0.15625, 0.71484375] |
| L | C | encrypted_body_nll_bits | 16 | 0.4414 | [0.15615234375, 0.765625] |
| L | C | token_count | 16 | 0.5000 | [0.5, 0.5] |
| F | A | prefix_match | 16 | 0.5000 | [0.5, 0.5] |
| F | A | format_accepted | 16 | 1.0000 | [1.0, 1.0] |
| F | A | format_and_kem_canonical | 16 | 1.0000 | [1.0, 1.0] |
| F | A | mean_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| F | A | encrypted_body_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| F | A | token_count | 16 | 0.5156 | [0.5, 0.5625] |
| F | B | prefix_match | 16 | 0.5000 | [0.5, 0.5] |
| F | B | format_accepted | 16 | 0.5000 | [0.5, 0.5] |
| F | B | format_and_kem_canonical | 16 | 0.5000 | [0.5, 0.5] |
| F | B | mean_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| F | B | encrypted_body_nll_bits | 16 | 1.0000 | [1.0, 1.0] |
| F | B | token_count | 16 | 0.5000 | [0.5, 0.5] |
| F | C | prefix_match | 16 | 0.5000 | [0.5, 0.5] |
| F | C | format_accepted | 16 | 0.5000 | [0.5, 0.5] |
| F | C | format_and_kem_canonical | 16 | 0.7188 | [0.59375, 0.84375] |
| F | C | mean_nll_bits | 16 | 0.3672 | [0.16796875, 0.5234375] |
| F | C | encrypted_body_nll_bits | 16 | 0.4102 | [0.1794921875, 0.609375] |
| F | C | token_count | 16 | 0.5000 | [0.5, 0.5] |

Intervals resample four context blocks and two repetitions within blocks; collapsed intervals are not population guarantees. Hidden aborts are reported separately.

## Resources and failures

Stage 6 usage: {"seconds": 5809.186128039983, "tokens": 101145, "cases": 150}. Lifetime: {"seconds": 7541.8848853629825, "tokens": 124994, "cases": 214}.

- qualification / L / - / None: 4 cases, 62.410 seconds, 69 tokens.
- qualification / F / - / 0: 1 cases, 29.334 seconds, 441 tokens.
- qualification / F / - / 128: 1 cases, 60.802 seconds, 1215 tokens.
- main_fixed / L / - / 32: 8 cases, 300.963 seconds, 5262 tokens.
- main_fixed / F / - / 32: 8 cases, 292.321 seconds, 5070 tokens.
- main_fixed / F / - / 128: 8 cases, 485.962 seconds, 9678 tokens.
- main_fixed / L / - / 128: 8 cases, 494.464 seconds, 9870 tokens.
- main_fixed / L / A / 32: 8 cases, 223.594 seconds, 3508 tokens.
- main_fixed / L / B / 32: 8 cases, 243.345 seconds, 3508 tokens.
- main_fixed / L / C / 32: 8 cases, 242.267 seconds, 3508 tokens.
- main_fixed / F / A / 32: 8 cases, 218.710 seconds, 3380 tokens.
- main_fixed / F / B / 32: 8 cases, 235.804 seconds, 3380 tokens.
- main_fixed / F / C / 32: 8 cases, 237.477 seconds, 3380 tokens.
- main_fixed / F / A / 128: 8 cases, 321.214 seconds, 6450 tokens.
- main_fixed / F / B / 128: 8 cases, 368.603 seconds, 6452 tokens.
- main_fixed / F / C / 128: 8 cases, 365.850 seconds, 6452 tokens.
- main_fixed / L / A / 128: 8 cases, 324.863 seconds, 6580 tokens.
- main_fixed / L / B / 128: 8 cases, 374.020 seconds, 6580 tokens.
- main_fixed / L / C / 128: 8 cases, 373.361 seconds, 6580 tokens.
- baseline / Calgacus / - / 32: 4 cases, 137.078 seconds, 2563 tokens.
- baseline / Calgacus / - / 128: 4 cases, 205.356 seconds, 4731 tokens.
- fresh_receiver / L / - / None: 4 cases, 105.635 seconds, 1260 tokens.
- fresh_receiver / F / - / None: 4 cases, 105.754 seconds, 1228 tokens.

Failures: {"retokenization_drift": 4, "tokenization_serialization_drift": 4}.
