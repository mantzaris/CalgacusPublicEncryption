## Fresh attempt-level recovery

| Method | Payload bytes | Exact / attempted | Capacity failures | Successful tokens | Success bits/token | Attempt mean bits/token | Mean job seconds |
|---|---|---|---|---|---|---|---|
| F | 32 | 4/4 | 0 | 200–200 | 1.2800 | 1.2800 | 37.0737 |
| F | 128 | 4/4 | 0 | 392–392 | 2.6122 | 2.6122 | 60.6844 |
| R | 32 | 2/4 | 2 | 563–1783 | 0.2991 | 0.1496 | 185.4250 |
| R | 128 | 0/4 | 4 | NA | NA | 0.0000 | 151.0288 |

## Nested checkpoints (not independent observations)

| Phase | Group | Recovery meaning | 512 | 1024 | 1536 | 1984 |
|---|---|---|---|---|---|---|
| diagnostic | diagnostic-qual-synthetic-32 | raw synthetic envelope | 0/1 | 0/1 | 1/1 | 1/1 |
| diagnostic | diagnostic-qual-HPKE-32 | authenticated payload | 0/1 | 0/1 | 0/1 | 1/1 |
| diagnostic | diagnostic-qual-synthetic-128 | raw synthetic envelope | 0/1 | 0/1 | 0/1 | 0/1 |
| diagnostic | diagnostic-qual-HPKE-128 | authenticated payload | 0/1 | 0/1 | 0/1 | 0/1 |
| main_fixed | F/32 | authenticated payload | 4/4 | 4/4 | 4/4 | 4/4 |
| main_fixed | F/128 | authenticated payload | 4/4 | 4/4 | 4/4 | 4/4 |
| main_fixed | R/32 | authenticated payload | 0/4 | 1/4 | 1/4 | 2/4 |
| main_fixed | R/128 | authenticated payload | 0/4 | 0/4 | 0/4 | 0/4 |

## Matched delivered/scorable recognition against B

| Method | Score (higher is carrier) | Pairs | Carrier mean | Control mean | AUC | Cluster interval |
|---|---|---|---|---|---|---|
| F | mean_nll_bits | 8 | 5.8166 | 1.0993 | 1.0000 | [1.0, 1.0] |
| F | mean_log2_rank | 8 | 2.7438 | 0.4050 | 1.0000 | [1.0, 1.0] |
| F | mean_admissible_nll_bits | 8 | 5.3154 | 1.0537 | 1.0000 | [1.0, 1.0] |
| F | format_accepted | 8 | 1.0000 | 1.0000 | 0.5000 | [0.5, 0.5] |
| F | format_and_kem_canonical | 8 | 1.0000 | 1.0000 | 0.5000 | [0.5, 0.5] |
| F | token_count | 8 | 296.0000 | 296.0000 | 0.5000 | [0.5, 0.5] |
| F | utf8_bytes | 8 | 1322.7500 | 1399.7500 | 0.4531 | [0.234375, 0.765625] |
| R | mean_nll_bits | 2 | 0.9821 | 0.7083 | 0.5000 | [0.0, 1.0] |
| R | mean_log2_rank | 2 | 0.3440 | 0.2506 | 0.5000 | [0.0, 1.0] |
| R | mean_admissible_nll_bits | 2 | 0.9369 | 0.6792 | 0.5000 | [0.0, 1.0] |
| R | format_accepted | 2 | 1.0000 | 0.0000 | 1.0000 | [1.0, 1.0] |
| R | format_and_kem_canonical | 2 | 1.0000 | 0.0000 | 1.0000 | [1.0, 1.0] |
| R | token_count | 2 | 1173.0000 | 1173.0000 | 0.5000 | [0.5, 0.5] |
| R | utf8_bytes | 2 | 4574.0000 | 5535.5000 | 0.5000 | [0.0, 1.0] |

## All attempted controls and encrypted settings

| Method | Role | Attempted | Delivered | Scorable | Format accepted | Format + KEM | Candidate membership all |
|---|---|---|---|---|---|---|---|
| F | encrypted | 8 | 8 | 8 | 8 | 8 | 8 |
| F | control | 8 | 8 | 8 | 8 | 8 | 8 |
| R | encrypted | 8 | 2 | 2 | 2 | 2 | 2 |
| R | control | 8 | 8 | 8 | 0 | 0 | 8 |

## Probability approximation diagnostics

| Method | Role | Messages | Mean message TV | Maximum step TV | Mean integer entropy | Mean unrounded entropy |
|---|---|---|---|---|---|---|
| F | encrypted | 8 | 0.0001 | 0.0002 | 2.8478 | 2.8472 |
| F | control | 8 | 0.0002 | 0.0002 | 1.0606 | 1.0584 |
| R | encrypted | 2 | 0.0002 | 0.0002 | 0.9337 | 0.9313 |
| R | control | 8 | 0.0002 | 0.0002 | 0.4370 | 0.4340 |

These are descriptive conditional-table differences, not independent token samples or a bound proving sequence-distribution equivalence.
