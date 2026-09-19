"""Public first-stable-bit stopping and independent format predicates.

No change to the Stage 7 arithmetic core. A completion event is not finish().
"""
import hashlib
from ..codecs.arithmetic_core import PacketDecoder, PacketEncoder
from ..errors import FramingError
from .full_text_observer import kem_representation


class FirstCompletion:
    def __init__(self, envelope_bytes):
        self.decoder = PacketDecoder(envelope_bytes)
        self.position = 0
        self.first_completion = None

    def step(self, symbol, frequencies):
        self.position += 1
        if self.first_completion is None:
            self.decoder.step(symbol, frequencies)
            if self.decoder.done:
                self.first_completion = self.position
        return self.first_completion is not None

    def snapshot(self):
        return dict(self.decoder.state.snapshot(), first_completion_token=self.first_completion)


def decompose_public_symbols(symbols, tables, envelope_bytes, *, canonical=True):
    """Pure host component fed ONLY by the public observer's own scoring pass.

Historical callers are labelled trace-only reanalysis, never live reception.
Every finish predicate concerns the first-complete prefix; end-at-first is
separate. KEM inspects stable bytes even when canonical finish fails.
"""
    names=['stable_target_reached','ends_at_first_completion','filler_consistent','canonical_replay_consistent','kem_canonical']
    out={k:None for k in names};out.update(first_completion_token=None,stable_bits=None,
        all_candidates_member=all(s is not None for s in symbols),unavailable_reasons={},format_accepted=False,format_and_kem_canonical=False)
    if len(symbols)!=len(tables):raise ValueError('Public table/symbol count mismatch')
    if not canonical:
        out['unavailable_reasons']={k:'Noncanonical or invalid text' for k in names};return out
    state=FirstCompletion(envelope_bytes)
    for pos,(symbol,table) in enumerate(zip(symbols,tables),1):
        if symbol is None or table is None:
            out['unavailable_reasons']={k:'Invalid admissible symbol before completion' for k in names}
            out['first_invalid_symbol']=pos;return out
        if state.step(symbol,table):break
    out.update(stable_target_reached=state.first_completion is not None,first_completion_token=state.first_completion,
               stable_bits=len(state.decoder.state.bits),arithmetic_terminal=state.decoder.state.snapshot())
    if state.first_completion is None:
        out['unavailable_reasons']={k:'Required stable bits not reached' for k in names[1:]};return out
    out['ends_at_first_completion']=state.first_completion==len(symbols)
    n=8*envelope_bytes;bits=state.decoder.state.bits
    tail=bits[n:];out['stable_overshoot_bits']=len(tail)
    out['filler_consistent']=tail==([1]+[0]*max(0,len(tail)-1))[:len(tail)]
    data=bytes(sum(bits[i+j]<<(7-j) for j in range(8)) for i in range(0,n,8))
    out.update(envelope_bytes=len(data),envelope_sha256=hashlib.sha256(data).hexdigest(),kem_canonical=kem_representation(data))
    replay=PacketEncoder(data);out['canonical_replay_consistent']=True
    for pos,(symbol,table) in enumerate(zip(state.decoder.symbols,state.decoder.tables),1):
        try:predicted=replay.step(table)
        except FramingError as exc:
            out.update(canonical_replay_consistent=False,canonical_replay_error=str(exc),first_replay_divergence=pos);break
        if predicted!=symbol:
            out.update(canonical_replay_consistent=False,first_replay_divergence=pos);break
    if out['canonical_replay_consistent'] and not replay.done:
        out.update(canonical_replay_consistent=False,canonical_replay_error='Replay did not complete')
    out['format_accepted']=all(out[k] is True for k in ['all_candidates_member','stable_target_reached','ends_at_first_completion','filler_consistent','canonical_replay_consistent'])
    out['format_and_kem_canonical']=out['format_accepted'] and out['kem_canonical']
    return out
