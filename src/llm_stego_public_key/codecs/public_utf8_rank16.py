"""Public rank-based transport comparator; not unmodified Calgacus.

Full-prefix consistency and nibble mapping adapt MIT ImageCalgacus helpers;
see THIRD_PARTY_NOTICES.md. No probabilities, secret stego key or normalization.
"""
import hashlib

from .calgacus import first_difference, order_logits
from ..cryptography.hpke import MIN_ENVELOPE, MAX_ENVELOPE
from ..errors import CapacityError, FramingError, Stage1Error, TransportError
from ..profile import validate_rank16_profile


class InvariantError(Stage1Error):
    """An emitted prefix violated the declared transport invariant; stop the run."""


def nibbles(data: bytes):
    # ImageCalgacus fixed_rank adaptation: zero-based symbols, high nibble first.
    return [symbol for byte in data for symbol in (byte >> 4, byte & 15)]


def frame(envelope: bytes):
    if type(envelope) is not bytes or not MIN_ENVELOPE <= len(envelope) <= MAX_ENVELOPE:
        raise FramingError('Envelope length outside 68..196 bytes')
    return len(envelope).to_bytes(4, 'big') + envelope


class PublicUtf8Rank16Codec:
    def __init__(self, model, token_attributes):
        self.model = model
        self.token_attributes = token_attributes
        self.trace = {}
        self._pieces = {}
        self._attributes = {}

    def _start(self, profile, cover, direction):
        validate_rank16_profile(profile)
        if cover not in profile['cover_contexts']:
            raise FramingError('Unknown public context')
        self.trace = {'direction': direction, 'advanced_ids': [], 'symbols': [], 'candidate_steps': []}
        self.model.begin(cover)

    def candidates(self, prefix):
        """One logits read; tokenization checks do not evaluate speculative tokens."""
        eligible = []
        rejected = {'special_control': 0, 'empty': 0, 'invalid_utf8': 0, 'noncanonical': 0}
        examined = 0
        for ranked in order_logits(self.model.logits())[:128]:
            token = int(ranked)
            examined += 1
            if token not in self._attributes:
                self._attributes[token] = int(self.token_attributes(token))
            # llama.cpp UNKNOWN, UNUSED, CONTROL, USER_DEFINED; byte/normal tokens allowed.
            if self._attributes[token] & 27:
                rejected['special_control'] += 1
                continue
            if token not in self._pieces:
                self._pieces[token] = self.model.detokenize([token])
            if not self._pieces[token]:
                rejected['empty'] += 1
                continue
            proposed = prefix + [token]
            # Full detokenization, not concatenation of independently decoded pieces.
            raw = self.model.detokenize(proposed)
            try:
                raw.decode('utf-8', errors='strict')
            except UnicodeDecodeError:
                rejected['invalid_utf8'] += 1
                continue
            if self.model.tokenize(raw) != proposed:
                rejected['noncanonical'] += 1
                continue
            eligible.append(token)
            if len(eligible) == 16:
                break
        self.trace['candidate_steps'].append({
            'position': len(prefix), 'examined': examined, 'eligible_found_capped_at_16': len(eligible),
            'rejected': rejected,
            'ordered_ids_sha256': hashlib.sha256(b''.join(i.to_bytes(4, 'big') for i in eligible)).hexdigest(),
        })
        if len(eligible) < 16:
            self.trace['failure_candidates'] = eligible
            raise CapacityError('Fewer than 16 admissible tokens within first 128 ranked IDs')
        return eligible

    def _advance(self, token, symbol):
        self.model.advance(token)
        self.trace['advanced_ids'].append(token)
        self.trace['symbols'].append(symbol)

    def embed(self, envelope, public_profile, cover_context):
        symbols = nibbles(frame(envelope))
        if len(symbols) > public_profile['tokens']['max_tokens']:
            raise CapacityError('Carrier token limit exceeded')
        self._start(public_profile, cover_context, 'embed')
        ids = self.trace['advanced_ids']
        for symbol in symbols:
            token = self.candidates(ids)[symbol]
            self._advance(token, symbol)
        raw = self.model.detokenize(ids)
        self.trace['carrier_bytes_hex'] = raw.hex()
        self.trace['retokenized_ids'] = self.model.tokenize(raw)
        self.trace['first_transport_divergence'] = first_difference(ids, self.trace['retokenized_ids'])
        try:
            raw.decode('utf-8', errors='strict')
        except UnicodeDecodeError as exc:
            raise InvariantError('Emitted carrier is not strict UTF-8') from exc
        if self.trace['first_transport_divergence'] is not None:
            raise InvariantError('Emitted carrier violates canonical token-prefix invariant')
        if len(raw) > public_profile['tokens']['max_transport_bytes']:
            raise CapacityError('Transport byte limit exceeded')
        return raw

    def extract(self, transmitted_utf8, public_profile, cover_context):
        validate_rank16_profile(public_profile)
        if type(transmitted_utf8) is not bytes or len(transmitted_utf8) > public_profile['tokens']['max_transport_bytes']:
            raise FramingError('Invalid or oversized transport bytes')
        try:
            transmitted_utf8.decode('utf-8', errors='strict')
        except UnicodeDecodeError as exc:
            raise TransportError('Received carrier is not strict UTF-8') from exc
        ids = self.model.tokenize(transmitted_utf8)
        self.trace = {'direction': 'extract', 'received_ids': ids}
        if not 8 <= len(ids) <= public_profile['tokens']['max_tokens']:
            raise FramingError('Incomplete header or carrier token limit exceeded')
        if self.model.detokenize(ids) != transmitted_utf8:
            raise FramingError('Carrier bytes are not canonical under the tokenizer')
        self._start(public_profile, cover_context, 'extract')
        self.trace['received_ids'] = ids
        prefix = self.trace['advanced_ids']
        header = bytearray()  # At most four bytes; no untrusted-length allocation.
        payload = None
        high = None
        length = None
        for position, token in enumerate(ids):
            eligible = self.candidates(prefix)
            if token not in eligible:
                self.trace['invalid_choice'] = {'position': position, 'token': token, 'eligible_ids': eligible}
                raise FramingError('Received token outside public rank16 alphabet')
            symbol = eligible.index(token)
            self._advance(token, symbol)
            if high is None:
                high = symbol
                continue
            value, high = (high << 4) | symbol, None
            if len(header) < 4:
                header.append(value)
                if len(header) == 4:
                    length = int.from_bytes(header, 'big')
                    self.trace['declared_envelope_bytes'] = length
                    if not MIN_ENVELOPE <= length <= MAX_ENVELOPE:
                        raise FramingError('Declared envelope length outside 68..196 bytes')
                    required_tokens = 2 * (4 + length)
                    if len(ids) != required_tokens:
                        raise FramingError('Truncated frame' if len(ids) < required_tokens else 'Trailing carrier tokens')
                    payload = bytearray(length)  # Bound and exact frame size validated first.
            else:
                payload[(position // 2) - 4] = value
        if payload is None or high is not None:
            raise FramingError('Incomplete frame')
        return bytes(payload)
