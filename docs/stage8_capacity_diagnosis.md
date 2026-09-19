# Stage 8 diagnosis of retained Stage 7 trajectories

The historical outcomes remain unchanged. No model inference was used for this diagnosis. `artifacts/stage8/diagnose.py` implements a separate half-open interval calculation using exact rational products and bitwise rescaling; it imports no production entropy coder. Hand-specified uniform and half-mass examples check independent output expectations. All 5,708 historical encoding steps, positive frequency totals (65,536), interval endpoints, stable-bit counts, pending bits and source packet prefixes agree with that calculation.

| Historical case | Stable / required bits | Pending | Selected-symbol information | Effective interval information minus frequency information |
|---|---:|---:|---:|---:|
| Synthetic 100 bytes |800/800|2|803.337510 bits|−0.000010591 bits|
| Synthetic 196 bytes |1229/1568|0|1229.892850 bits|−0.000024186 bits|
| HPKE 32-byte payload |705/800|0|705.476107 bits|−0.000000547 bits|
| HPKE 128-byte payload |1408/1568|2|1410.797568 bits|+0.000000345 bits|

The cumulative effective interval information equals stable bits + pending bits + `32-log2(residual interval width)`, within numerical reporting tolerance at every step. Delayed bit release exists, but pending debt is zero or two at the failed terminal points. Finite interval rounding changes accumulated information by less than 0.000025 bits in these cases. It cannot explain deficits of 339, 95 and 160 stable bits.

For the 32-byte HPKE packet, tokens 769–1,024 release **zero stable bits**. Selected-symbol information totals only **0.115071 bits** and mean integer-table entropy is **0.005118 bits/token** in that block. Its longest no-release run spans tokens633–1196 (564 tokens), with1.582765 selected-information bits and only two pending bits at the end. The 128-byte HPKE packet ends with a141-token no-release run containing0.532789 selected-information bits. These are low-information trajectories, not large amounts of information hidden by underflow bookkeeping.

Per-token CSVs retain stable bits, pending bits, residual widths, effective and nominal selected-symbol information and integer-table entropy. JSON retains fixed128- and256-token blocks and the five longest no-release runs. Integer-table entropy is a conditional expected information rate under that table; selected-symbol information is the realized path. Historical unrounded candidate logits were not retained, so their exact probability-rounding variation cannot be reconstructed from these old tables. Stage8 public scoring measures it where logits are available.

The arithmetic algorithm is retained unchanged. No implementation repair is justified by this audit. The four cases differ in context and input bytes, so their differences are not attributable to HPKE structure. Extending one trajectory can test additional capacity; dividing missing bits by one historical average cannot reliably predict completion through these stalls.
