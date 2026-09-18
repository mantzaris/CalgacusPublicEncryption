"""Frozen Stage 6 public diagnostics, starting from received bytes only.

No private key, payload, encoder trace, intended length, family label or receiver
outcome is an input. One cover-scoring pass feeds all rank/support/likelihood
statistics. Calgacus needs an additional public source reconstruction pass.
"""
import hashlib
import math
import numpy as np
from ..codecs.public_utf8_rank16 import PublicUtf8Rank16Codec
from ..codecs.calgacus import CalgacusCodec
from ..codecs.inferred_rank16 import inferred_length
from ..cryptography.hpke import deserialize
from ..errors import CapacityError, FramingError, TransportError
from ..profile import validate_supported_profile, validate_rank16_profile, canonical_json
from .public_prefix import PublicPrediction, observe_prefix, probabilities


def parse_public_symbols(symbols, variant):
    if variant == 'F':
        inferred_length(len(symbols))
    elif variant == 'L':
        if len(symbols) % 2 or not 144 <= len(symbols) <= 400:
            raise FramingError('Length-framed token count outside bounds')
    else:
        raise ValueError('Unknown rank frame')
    if any(type(s) is not int or not 0 <= s < 16 for s in symbols):
        raise FramingError('Received token outside public rank16 alphabet')
    raw = bytes((a << 4) | b for a,b in zip(symbols[::2],symbols[1::2]))
    if variant == 'L':
        size = int.from_bytes(raw[:4], 'big')
        if not 68 <= size <= 196 or len(raw) != size+4:
            raise FramingError('Invalid declared envelope length or trailing/truncated frame')
        return raw[4:]
    return raw


def kem_representation(envelope):
    """Necessary canonical X25519 output representation, NOT key/tag validation.

    RFC 7748 section 5 encodeUCoordinate reduces modulo 2**255-19;
    RFC 9180 sections 4.1/7.1.1 place this serialized ephemeral key first.
    Noncanonical inputs can still be accepted by X25519 decoders; this tests
    the output representation of the frozen sender, not recipient acceptance.
    """
    if len(envelope) < 32:
        return False
    return int.from_bytes(envelope[:32], 'little') < 2**255-19


def mean(values):
    return float(math.fsum(values)/len(values)) if values else None


def observe_complete(transmitted_utf8, public_profile, cover_context, recipient_public_key,
                     public_prediction, admission_profile, model, token_attributes):
    validate_supported_profile(public_profile)
    validate_rank16_profile(admission_profile)
    if cover_context not in public_profile['cover_contexts'] or type(recipient_public_key) is not bytes or len(recipient_public_key) != 32:
        raise ValueError('Invalid agreed public observer inputs')
    pred = PublicPrediction.from_record(public_prediction)
    pred.validate(admission_profile, cover_context)
    if any(public_profile[k] != admission_profile[k] for k in ['model','backend','inference','cover_contexts']):
        raise ValueError('Observer model/context identity mismatch')
    result = {'schema_version':1, 'observer_id':'stage6_public_complete_v1', 'authenticated':False,
              'profile_sha256':hashlib.sha256(canonical_json(public_profile)).hexdigest(),
              'format_accepted':False,'format_and_kem_canonical':False,'kem_canonical':None,
              'scorable':False,'prediction_cache_key':pred.cache_key}
    if type(transmitted_utf8) is not bytes:
        return dict(result,status='invalid_input')
    result['utf8_bytes'] = len(transmitted_utf8)
    try:
        transmitted_utf8.decode('utf-8', errors='strict')
    except UnicodeError:
        return dict(result,status='invalid_utf8')
    if len(transmitted_utf8) > public_profile['tokens']['max_transport_bytes']:
        return dict(result,status='oversized_bytes')
    ids = model.tokenize(transmitted_utf8)
    result['token_count'] = len(ids)
    result['canonical_bytes'] = model.detokenize(ids) == transmitted_utf8
    result['prefix'] = observe_prefix(transmitted_utf8, admission_profile, cover_context, pred, model.tokenize)
    if not 1 <= len(ids) <= public_profile['tokens']['max_tokens']:
        return dict(result,status='unscorable_token_count')
    codec = PublicUtf8Rank16Codec(model,token_attributes)
    codec._start(admission_profile,cover_context,'public_complete_score')
    ranks=[];symbols=[];nll=[];candidate_unavailable=[]
    prefix=codec.trace['advanced_ids']
    for position,token in enumerate(ids):
        values=model.logits()
        _,logs=probabilities(values)
        rank=int(np.count_nonzero(values>values[token])+np.count_nonzero(values[:token]==values[token])+1)
        ranks.append(rank);nll.append(float(-logs[token]/math.log(2)))
        try:
            eligible=codec.candidates(prefix)
        except CapacityError:
            eligible=[];candidate_unavailable.append(position)
        symbol=eligible.index(token) if token in eligible else None
        symbols.append(symbol);codec._advance(token,symbol)
    variant = 'F' if public_profile['codec']=='public_utf8_rank16_inferred_v1' else ('L' if public_profile['codec']=='public_utf8_rank16_v1' else 'Calgacus')
    body_start = {'L':72,'F':64}.get(variant)
    log_ranks=[math.log2(v) for v in ranks]
    result.update(status='scored',scorable=True,all_candidates_member=all(s is not None for s in symbols),
        member_fraction=sum(s is not None for s in symbols)/len(symbols),
        mean_nll_bits=mean(nll),mean_log2_rank=mean(log_ranks),
        after_eight_nll_bits=mean(nll[8:]),after_eight_log2_rank=mean(log_ranks[8:]),
        encrypted_body_nll_bits=mean(nll[body_start:]) if body_start is not None else None,
        encrypted_body_log2_rank=mean(log_ranks[body_start:]) if body_start is not None else None,
        candidate_unavailable_positions=candidate_unavailable,
        trace={'received_ids':ids,'symbols':symbols,'ranks':ranks,'nll_bits':nll,
               'candidate_steps':codec.trace['candidate_steps']})
    try:
        if not result['canonical_bytes']:
            raise FramingError('Received bytes are not canonical tokenizer output')
        if variant == 'Calgacus':
            # The ranks were computed here from public wire text, not supplied by encoder.
            source_codec=CalgacusCodec(model,public_profile['source_context'])
            model.meter.phase='public_source_reconstruction'
            source_ids=source_codec.from_ranks(ranks,public_profile['source_context'])
            raw=model.detokenize(source_ids)
            try: text=raw.decode('utf-8',errors='strict')
            except UnicodeError as exc: raise TransportError('Public source reconstruction is invalid UTF-8') from exc
            envelope=deserialize(text)
        else:
            envelope=parse_public_symbols(symbols,variant)
        result.update(format_accepted=True,envelope_bytes=len(envelope),
                      envelope_sha256=hashlib.sha256(envelope).hexdigest(),
                      kem_canonical=kem_representation(envelope),
                      format_and_kem_canonical=kem_representation(envelope))
    except (FramingError,TransportError,CapacityError) as exc:
        result.update(format_error=str(exc),format_failure_category=exc.category)
    return result
