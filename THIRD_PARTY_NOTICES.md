# Third-party notices

`vendor/calgacus/` is an unmodified reference snapshot of noranta4/calgacus at the commit in `manifests/upstream_sources.json`. Its MIT license is retained. `codecs/calgacus.py` adapts the conditional rank method; adaptations are enumerated in `docs/source_audit.md`.

CUDA preloading, full native cache reset and stable token-ID tie handling follow MIT-licensed RankCloak, commit ce853d42d6ba64065cb63c6bdfc0d825c62734cd. Its license is in `vendor/RANKCLOAK_LICENSE`. No related manuscript or prior experiment dataset is redistributed as new work.

HPKE uses MIT-licensed pyhpke 0.6.5 and PyCA cryptography 46.0.7. Published known-answer test data are attributed to RFC 9180 Appendix A.2.1 and the CFRG HPKE vector repository; provenance and hashes are recorded. Model weights/tokenizer are external, governed by their original terms (Meta Llama 3 / the QuantFactory distribution), not this project's MIT license. No model weights are committed.
