"""Public six-zero prediction, prefix-only observer and fixed diagnostic generators.

Admissibility is delegated directly to the unchanged rank16 codec. No private key,
expected payload, ciphertext, encoder trace or evaluator label is an API input.
"""
from dataclasses import dataclass
import hashlib
import math
import numpy as np
from ..codecs.public_utf8_rank16 import PublicUtf8Rank16Codec, InvariantError
from ..errors import RankError
from ..profile import canonical_json, validate_rank16_profile

PREFIX_TOKENS = 6
OBSERVER_ID = 'public_zero6_v1'


def cache_key(profile, cover):
    return hashlib.sha256(canonical_json({'observer_id': OBSERVER_ID,
        'profile_sha256': hashlib.sha256(canonical_json(profile)).hexdigest(),
        'cover_context': cover})).hexdigest()


@dataclass(frozen=True)
class PublicPrediction:
    profile_sha256: str
    cover_context: str
    token_ids: tuple[int, ...]
    cache_key: str

    @classmethod
    def from_record(cls, record):
        return cls(record['profile_sha256'], record['cover_context'], tuple(record['token_ids']), record['cache_key'])

    def validate(self, profile, cover):
        validate_rank16_profile(profile)
        if (cover not in profile['cover_contexts'] or self.cover_context != cover
            or self.profile_sha256 != hashlib.sha256(canonical_json(profile)).hexdigest()
            or self.cache_key != cache_key(profile, cover)
            or len(self.token_ids) != PREFIX_TOKENS
            or any(type(t) is not int or t < 0 for t in self.token_ids)):
            raise ValueError('Public prediction/configuration mismatch')


def observe_prefix(transmitted_utf8, public_profile, cover_context, prediction, tokenize):
    """Tokenize actual text and compare only its first six IDs; no full-length rule.

    Invalid bytes and fewer than six tokens are nonmatches with explicit statuses.
    Bad public cache/configuration or tokenizer failures raise, rather than silently
    producing a classification. A match is not ciphertext or tag validation.
    """
    prediction.validate(public_profile, cover_context)
    if type(transmitted_utf8) is not bytes:
        return {'prefix_match': False, 'status': 'invalid_input'}
    try:
        transmitted_utf8.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        return {'prefix_match': False, 'status': 'invalid_utf8'}
    prefix = tuple(tokenize(transmitted_utf8)[:PREFIX_TOKENS])
    if len(prefix) < PREFIX_TOKENS:
        return {'prefix_match': False, 'status': 'insufficient_tokens', 'observed_prefix_ids': list(prefix)}
    match = prefix == prediction.token_ids
    return {'prefix_match': match, 'status': 'match' if match else 'valid_nonmatch',
            'observed_prefix_ids': list(prefix)}


def probabilities(values):
    """Temperature-one float64 softmax and stable log probabilities."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise RankError('Nonfinite/invalid diagnostic logits')
    shifted = values - values.max()
    weights = np.exp(shifted)
    total = weights.sum()
    return weights / total, shifted - math.log(float(total))


def choose_token(values, eligible, family, rng):
    if family == 'A':
        p, _ = probabilities(values)
        return int(rng.choice(len(p), p=p)), None
    if len(eligible) != 16:
        raise ValueError('Admissible generators require the unchanged 16-token alphabet')
    if family == 'B':
        p, _ = probabilities(np.asarray(values)[eligible])
        index = int(rng.choice(16, p=p))
    elif family == 'C':
        index = int(rng.integers(16))
    else:
        raise ValueError('Unknown frozen generator')
    return int(eligible[index]), index


def predict_public_prefix(codec, public_profile, cover_context):
    """Six symbol-zero steps computed solely from the public configuration."""
    codec._start(public_profile, cover_context, 'public_prediction')
    prefix = codec.trace['advanced_ids']; scores = []
    for position in range(PREFIX_TOKENS):
        eligible = codec.candidates(prefix)
        logits = codec.model.logits().astype(np.float64)
        p_a, log_a = probabilities(logits)
        p_b, log_b = probabilities(logits[eligible])
        token = eligible[0]
        scores.append({'position': position, 'token_id': token, 'admissible_ids': eligible,
                       'admissible_logits': logits[eligible].tolist(),
                       'A_probability_latent_token': float(p_a[token]), 'A_log_probability': float(log_a[token]),
                       'B_probability_admissible_zero': float(p_b[0]), 'B_log_probability': float(log_b[0])})
        codec._advance(token, 0)
    raw = codec.model.detokenize(prefix)
    try: raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc: raise InvariantError('Public prediction is not UTF-8') from exc
    if codec.model.tokenize(raw) != prefix:
        raise InvariantError('Public prediction prefix is not canonical')
    log_a = math.fsum(s['A_log_probability'] for s in scores)
    log_b = math.fsum(s['B_log_probability'] for s in scores)
    return {'schema_version': 1, 'observer_id': OBSERVER_ID,
            'profile_sha256': hashlib.sha256(canonical_json(public_profile)).hexdigest(),
            'cover_context': cover_context, 'cache_key': cache_key(public_profile, cover_context),
            'token_ids': list(prefix), 'prefix_utf8': raw.decode('utf-8'), 'scores': scores,
            'A_log_probability_latent_sequence': log_a, 'A_probability_latent_sequence': math.exp(log_a),
            'B_log_probability_prefix_match': log_b, 'B_probability_prefix_match': math.exp(log_b),
            'C_log_probability_prefix_match': -6 * math.log(16), 'C_probability_prefix_match': 16.0**-6,
            'provenance_rule': 'public candidate selection, symbol zero six times; no saved carriers or encoder data used'}


def generate_prefix(codec, public_profile, cover_context, family, seed):
    """Exactly six attempted emissions; no resampling, header, encryption or tail."""
    if family not in ('A', 'B', 'C'): raise ValueError('Unknown frozen generator')
    codec._start(public_profile, cover_context, 'control_' + family)
    prefix = codec.trace['advanced_ids']; rng = np.random.Generator(np.random.PCG64(seed))
    for _ in range(PREFIX_TOKENS):
        eligible = codec.candidates(prefix) if family in ('B', 'C') else []
        token, index = choose_token(codec.model.logits(), eligible, family, rng)
        codec._advance(token, index)
    return codec.model.detokenize(prefix)
