"""Stage 8 public scoring pass extended with separate Stage 9 predicates.

Reuses the unchanged canonical candidate method, probabilities and arithmetic.
The interface accepts no evaluator labels, seeds, keys or encoder traces.
"""
import hashlib
import math
import numpy as np
from ..codecs.stage7_transport import Arithmetic16Codec
from ..codecs.arithmetic_core import frequencies
from .stopping_rule import decompose_public_symbols
from ..profile import validate_stage7_profile,canonical_json
from ..errors import FramingError,CapacityError
from .public_prefix import probabilities
from .full_text_observer import mean,kem_representation


def observe_stage9(transmitted_utf8,public_profile,cover_context,model,token_attributes):
    validate_stage7_profile(public_profile,'R')
    if cover_context not in public_profile['cover_contexts']:raise ValueError('Invalid public inputs')
    out={'schema_version':1,'observer_id':'stage9_decomposed_public_v1','authenticated':False,'scorable':False,
         'format_accepted':False,'format_and_kem_canonical':False,'kem_canonical':None,
         'profile_sha256':hashlib.sha256(canonical_json(public_profile)).hexdigest(),
         'body_region_scores':None,'body_region_reason':'No fixed token exclusion applied; complete-message scores are primary for both methods'}
    out.update(valid_utf8=None,canonical_bytes=None,all_candidates_member=None,stable_target_reached=None,first_completion_token=None,ends_at_first_completion=None,filler_consistent=None,canonical_replay_consistent=None,unavailable_reasons={'downstream':'Received text not yet scored'})
    if type(transmitted_utf8)!=bytes:return dict(out,status='invalid_input')
    out['utf8_bytes']=len(transmitted_utf8)
    try:transmitted_utf8.decode('utf-8',errors='strict')
    except UnicodeError:return dict(out,status='invalid_utf8',valid_utf8=False)
    out['valid_utf8']=True
    if len(transmitted_utf8)>public_profile['tokens']['max_transport_bytes']:return dict(out,status='oversized_bytes')
    ids=model.tokenize(transmitted_utf8);out.update(token_count=len(ids),canonical_bytes=model.detokenize(ids)==transmitted_utf8)
    # Bound the actual received message before any model evaluation.
    if not 1<=len(ids)<=public_profile['tokens']['max_tokens']:return dict(out,status='unscorable_token_count')
    c=Arithmetic16Codec(model,token_attributes);c._start(public_profile,cover_context,'public_scoring')
    ranks=[];nll=[];symbols=[];weighted_nll=[];tables=[];unavailable=[];rounding=[]
    for pos,token in enumerate(ids):
        values=model.logits();_,logs=probabilities(values)
        ranks.append(int(np.count_nonzero(values>values[token])+np.count_nonzero(values[:token]==values[token])+1))
        nll.append(float(-logs[token]/math.log(2)))
        try:eligible=c.candidates(c.trace['advanced_ids'])
        except CapacityError:eligible=[];unavailable.append(pos)
        symbol=eligible.index(token) if token in eligible else None
        symbols.append(symbol)
        if eligible:
            local_probs,local_logs=probabilities(values[eligible]);tables.append(frequencies(values[eligible]))
            q=np.asarray(tables[-1],dtype=float)/65536
            rounding.append({'total_variation':float(np.abs(q-local_probs).sum()/2),
                'integer_entropy_bits':float(-np.sum(q*np.log2(q))),
                'unrounded_entropy_bits':float(-np.sum(local_probs*local_logs)/math.log(2))})
            weighted_nll.append(float(-local_logs[symbol]/math.log(2)) if symbol is not None else None)
        else:tables.append(None);weighted_nll.append(None)
        c._advance(token,symbol)
    out.update(status='scored',scorable=True,all_candidates_member=all(s is not None for s in symbols),
        member_fraction=sum(s is not None for s in symbols)/len(symbols),mean_nll_bits=mean(nll),
        mean_log2_rank=mean([math.log2(x) for x in ranks]),
        mean_admissible_nll_bits=mean(weighted_nll) if all(x is not None for x in weighted_nll) else None,
        candidate_unavailable_positions=unavailable,
        probability_rounding_mean_tv=mean([x['total_variation'] for x in rounding]),
        probability_rounding_max_tv=max((x['total_variation'] for x in rounding),default=None),
        trace={'received_ids':ids,'symbols':symbols,'ranks':ranks,'nll_bits':nll,'admissible_nll_bits':weighted_nll,
               'candidate_steps':c.trace['candidate_steps'],'frequency_tables':tables,'probability_rounding':rounding})
    out.update(decompose_public_symbols(symbols,tables,public_profile['public_size_class']['envelope_bytes'],canonical=out['canonical_bytes']))
    return out
