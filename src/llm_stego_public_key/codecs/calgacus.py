"""Full-vocabulary conditional rank transfer, with explicit text-boundary semantics.

Adapted from Calgacus notebook cell 10; see docs/source_audit.md and vendor license.
Stable total order and full cache reset follow the local RankCloak implementation.
This is NOT the unmodified notebook or a text-normalization repair.
"""

import numpy as np

from ..errors import CapacityError, RankError, TransportError
from .interfaces import RankModel


def order_logits(logits: np.ndarray) -> np.ndarray:
    values = np.asarray(logits)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise RankError("Expected a finite nonempty logits vector")
    return np.lexsort((np.arange(values.size), -values))


def first_difference(expected, actual):
    for i, (a, b) in enumerate(zip(expected, actual)):
        if a != b:
            return {"position": i, "expected": int(a), "actual": int(b)}
    if len(expected) != len(actual):
        return {
            "position": min(len(expected), len(actual)),
            "expected_length": len(expected),
            "actual_length": len(actual),
        }
    return None


class CalgacusCodec:
    def __init__(
        self,
        model: RankModel,
        source_context: str,
        max_tokens: int = 512,
        max_transport_bytes: int = 65536,
    ):
        self.model = model
        self.source_context = source_context
        self.max_tokens = max_tokens
        self.max_transport_bytes = max_transport_bytes
        self.trace = {}

    def ranks(self, ids: list[int], context: str) -> list[int]:
        if len(ids) > self.max_tokens:
            raise CapacityError("Token capacity exceeded")
        self.model.begin(context)
        result = []
        for token in ids:
            order = order_logits(self.model.logits())
            positions = np.flatnonzero(order == token)
            if len(positions) != 1:
                raise RankError("Token outside vocabulary")
            result.append(int(positions[0]) + 1)
            self.model.advance(token)
        return result

    def from_ranks(self, ranks: list[int], context: str) -> list[int]:
        if len(ranks) > self.max_tokens:
            raise CapacityError("Token capacity exceeded")
        self.model.begin(context)
        result = []
        for rank in ranks:
            order = order_logits(self.model.logits())
            if not 1 <= rank <= len(order):
                raise RankError("Rank outside vocabulary")
            token = int(order[rank - 1])
            result.append(token)
            self.model.advance(token)
        return result

    def _text(self, raw: bytes) -> str:
        if len(raw) > self.max_transport_bytes:
            raise CapacityError("Transport byte capacity exceeded")
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise TransportError("Carrier or extracted source is not strict UTF-8") from exc

    def encode(self, source: str, cover_context: str) -> bytes:
        self.trace = {"direction": "encode"}
        raw = source.encode("utf-8", errors="strict")
        self._text(raw)
        ids = self.model.tokenize(raw)
        self.trace["source_ids"] = ids
        ranks = self.ranks(ids, self.source_context)
        self.trace["source_ranks"] = ranks
        cover_ids = self.from_ranks(ranks, cover_context)
        self.trace["carrier_ids"] = cover_ids
        carrier = self.model.detokenize(cover_ids)
        self.trace["carrier_bytes_hex"] = carrier.hex()
        self._text(carrier)
        observed = self.model.tokenize(carrier)
        self.trace["retokenized_ids"] = observed
        self.trace["first_transport_divergence"] = first_difference(cover_ids, observed)
        # Preserve and transmit drifted text. The receiver never receives intended IDs.
        return carrier

    def extract(self, transmitted_utf8: bytes, cover_context: str) -> str:
        self.trace = {"direction": "extract"}
        self._text(transmitted_utf8)
        ids = self.model.tokenize(transmitted_utf8)
        self.trace["received_ids"] = ids
        if self.model.detokenize(ids) != transmitted_utf8:
            raise TransportError("Received text is not byte-exact under tokenizer")
        ranks = self.ranks(ids, cover_context)
        self.trace["received_ranks"] = ranks
        source_ids = self.from_ranks(ranks, self.source_context)
        self.trace["reconstructed_ids"] = source_ids
        return self._text(self.model.detokenize(source_ids))
