# Stage 7 measured qualification results

| Case | Raw envelope bytes | Emitted tokens | Stable/required bits | Outcome |
|---|---:|---:|---:|---|
| qual-synthetic-32 | 100 | 1100 | 800/800 | synthetic exact recovery |
| qual-synthetic-128 | 196 | 1536 | 1229/1568 | capacity_exhaustion |
| qual-HPKE-32 | 100 | 1536 | 705/800 | capacity_exhaustion |
| qual-HPKE-128 | 196 | 1536 | 1408/1568 | capacity_exhaustion |

The sole successful case is a synthetic raw-envelope fixture, not an HPKE message. All main-study recovery and recognition metrics are unavailable because qualification blocked execution.

Stage 7 resource use: {"cases": 4, "seconds": 453.3871514170023, "tokens": 6865}. Lifetime: {"cases": 218, "seconds": 7995.272036779985, "tokens": 131859}.

Zero controls and zero fresh-process receiver replays ran. Internal partial emissions from aborted senders are not delivered messages.
