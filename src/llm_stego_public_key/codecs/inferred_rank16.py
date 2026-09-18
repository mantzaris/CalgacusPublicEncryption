"""Length-inferred public rank transport. Candidate selection is inherited unchanged.

The message boundary is the UTF-8 byte-string boundary, not a secret length.
Even truncation/appending within the bounds reaches HPKE and must authenticate.
"""
from .public_utf8_rank16 import PublicUtf8Rank16Codec, InvariantError, nibbles
from .calgacus import first_difference
from ..cryptography.hpke import MIN_ENVELOPE, MAX_ENVELOPE
from ..errors import CapacityError, FramingError, TransportError
from ..profile import validate_inferred_profile


def inferred_length(token_count):
    if type(token_count) is not int or token_count % 2 or not 2*MIN_ENVELOPE <= token_count <= 2*MAX_ENVELOPE:
        raise FramingError('Inferred frame requires an even token count in 136..392')
    return token_count // 2


class InferredRank16Codec(PublicUtf8Rank16Codec):
    def _start(self, profile, cover, direction):
        validate_inferred_profile(profile)
        if cover not in profile['cover_contexts']:
            raise FramingError('Unknown public context')
        self.trace = {'direction': direction, 'advanced_ids': [], 'symbols': [], 'candidate_steps': []}
        self.model.begin(cover)

    def embed(self, envelope, public_profile, cover_context):
        validate_inferred_profile(public_profile)
        if type(envelope) is not bytes or not MIN_ENVELOPE <= len(envelope) <= MAX_ENVELOPE:
            raise FramingError('Envelope length outside 68..196 bytes')
        symbols = nibbles(envelope)
        if len(symbols) > public_profile['tokens']['max_tokens']:
            raise CapacityError('Carrier token limit exceeded')
        self._start(public_profile, cover_context, 'embed')
        ids = self.trace['advanced_ids']
        for symbol in symbols:
            self._advance(self.candidates(ids)[symbol], symbol)
        raw = self.model.detokenize(ids)
        self.trace['carrier_bytes_hex'] = raw.hex()
        self.trace['retokenized_ids'] = self.model.tokenize(raw)
        self.trace['first_transport_divergence'] = first_difference(ids, self.trace['retokenized_ids'])
        try:
            raw.decode('utf-8', errors='strict')
        except UnicodeError as exc:
            raise InvariantError('Inferred carrier is not strict UTF-8') from exc
        if self.trace['first_transport_divergence'] is not None:
            raise InvariantError('Inferred carrier violates canonical prefix invariant')
        if len(raw) > public_profile['tokens']['max_transport_bytes']:
            raise CapacityError('Transport byte limit exceeded')
        return raw

    def extract(self, transmitted_utf8, public_profile, cover_context):
        validate_inferred_profile(public_profile)
        if type(transmitted_utf8) is not bytes or len(transmitted_utf8) > public_profile['tokens']['max_transport_bytes']:
            raise FramingError('Invalid or oversized transport bytes')
        try:
            transmitted_utf8.decode('utf-8', errors='strict')
        except UnicodeError as exc:
            raise TransportError('Received carrier is not strict UTF-8') from exc
        ids = self.model.tokenize(transmitted_utf8)
        length = inferred_length(len(ids))  # Validate before allocating recovered envelope.
        if self.model.detokenize(ids) != transmitted_utf8:
            raise FramingError('Carrier bytes are not canonical under the tokenizer')
        self._start(public_profile, cover_context, 'extract')
        self.trace.update(received_ids=ids, inferred_envelope_bytes=length)
        result = bytearray(length)
        prefix = self.trace['advanced_ids']
        high = None
        for position, token in enumerate(ids):
            eligible = self.candidates(prefix)
            if token not in eligible:
                self.trace['invalid_choice'] = {'position': position, 'token': token, 'eligible_ids': eligible}
                raise FramingError('Received token outside public rank16 alphabet')
            symbol = eligible.index(token)
            self._advance(token, symbol)
            if high is None:
                high = symbol
            else:
                result[position//2] = (high << 4) | symbol
                high = None
        return bytes(result)
