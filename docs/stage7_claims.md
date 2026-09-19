# Stage 7 claim-to-evidence boundaries

The arithmetic adapter is implemented and independently checked on deterministic tables. **The live HPKE qualification gate failed on capacity. The comparative main study was not executed.**

| Statement | Type / status | Evidence | Limit |
|---|---|---|---|
| Arithmetic mapping toward a model distribution is established prior work | Established method | Ziegler et al., D19-1115 §3; source audit | Not our invention; finite packets and restricted support need their own analysis |
| F and R use the same ordered canonical16 candidate function | Inspected implementation, focused contract check | Direct inheritance in `stage7_transport.py`; `test_stage7.py` | No distribution claim follows from support equality |
| The integer core agrees with independent expected mappings | Passed focused validation | Exact Fraction reference, explicit nibble/boundary expectations, changing tables, precision-crossing and terminal rejection checks; 15 focused tests | Small independent cases plus boundary contracts, not a proof or broad suite |
| One 100-byte synthetic envelope traversed actual UTF-8 exactly | Measured | `qual-synthetic-32`, 1100 tokens, 5278 UTF-8 bytes, 800 stable bits; independent cleared-cache inverse | Synthetic raw bytes, not HPKE recovery; inverse in the same worker process |
| A 196-byte synthetic packet exhausted the fixed ceiling | Measured | `qual-synthetic-128`, 1229/1568 stable bits at 1536 tokens | One context/packet, no population capacity estimate |
| Fresh32/128-byte HPKE qualification packets did not complete | Measured | `qual-HPKE-32`:705/800; `qual-HPKE-128`:1408/1568; both1536 tokens | Sender capacity aborts before wire delivery/authentication; not AEAD rejections or demonstrated inverse errors |
| F-versus-R statistical recognition changed | **Unmeasured** | Main gate stopped all32 transmissions and64 controls | No Stage 7 AUC, advantage or detector accuracy claim; historical Stage 6 is not pooled |
| R packet/termination structure remains recognizable | **Hypothesis / implemented predicate, not measured recognition** | Public midpoint/termination checks and canonical-KEM predicate exist | No complete HPKE carriers or control distributions were scored in this run |
| Independent real-message receiver recovery works for R | **Not established on GPU** | Both preselected replay slots unavailable after source aborts | Matching cleared-cache calls do not substitute for a fresh process |
| Stage 7 has a distinct regular-paper contribution | **Not established** | Bounded adverse capacity examples with reproducible failure evidence | General probability/rate tradeoffs are expected; controlled complete-message comparison is missing |

Potential paper contribution, still provisional: a controlled empirical account of how encrypted packet representation, finite termination and actual UTF-8 admissibility jointly affect recovery and public recognition. Stage 7 contributes reusable implementation and a concrete qualification failure to that direction, not the required successful comparison.

No result breaks HPKE, proves concealment, authenticates a sender, establishes edit robustness, or introduces a new encryption primitive. Public format acceptance would remain distinct from authentication. Internal CARTS/RankCloak/ImageCalgacus overlap remains set aside as an execution prerequisite; neither attribution nor novelty caution is removed.
