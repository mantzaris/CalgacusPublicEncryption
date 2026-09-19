"""Focused checks of new stopping/decomposition contracts; no model inference."""
import inspect,json,sys
from pathlib import Path
import numpy as np
import pytest
from llm_stego_public_key.evaluation.stopping_rule import FirstCompletion,decompose_public_symbols
from llm_stego_public_key.codecs.arithmetic_core import PacketDecoder
from llm_stego_public_key.evaluation.stage9_observer import observe_stage9
ROOT=Path(__file__).resolve().parents[1]

def test_independent_uniform_and_changing_table_bits(monkeypatch):
    monkeypatch.setattr(PacketDecoder,'finish',lambda s:(_ for _ in ()).throw(AssertionError('Stopping must not finish')))
    stop=FirstCompletion(1)
    assert not stop.step(0,[1]*16) # 0000
    assert not stop.step(3,[1]*4)  # 11
    assert stop.step(2,[1]*4)      # 10 -> 0x0e
    assert stop.first_completion==3 and stop.decoder.state.bits==[0,0,0,0,1,1,1,0]
    assert stop.step(1,[1,1]) and stop.first_completion==3 # first event stays latched

def test_pending_underflow_is_not_stable_completion():
    stop=FirstCompletion(1);assert not stop.step(1,[1,2,1])
    assert stop.decoder.state.pending==1 and stop.decoder.state.bits==[]
    assert not stop.step(0,[1,1]);assert stop.decoder.state.bits==[0,1]
    for _ in range(5):assert not stop.step(0,[1,1])
    assert stop.step(0,[1,1]) and stop.first_completion==8

def test_completion_overshoot_does_not_imply_finish():
    out=decompose_public_symbols([0],[[1,511]],1)
    # Interval [0,1/512) releases nine zero bits. Required byte is0;
    # its deterministic midpoint begins 00000000 1, outside that interval.
    assert out['stable_bits']==9 and out['stable_target_reached'] and out['ends_at_first_completion']
    assert not out['filler_consistent'] and not out['canonical_replay_consistent']
    assert not out['format_accepted']

def test_incomplete_trailing_and_capacity_denominators():
    out=decompose_public_symbols([0],[[1]*16],1)
    assert out['stable_target_reached'] is False and out['filler_consistent'] is None
    out=decompose_public_symbols([0,1,2],[[1]*16]*3,1)
    assert out['first_completion_token']==2 and not out['ends_at_first_completion']
    assert out['filler_consistent'] and out['canonical_replay_consistent']
    assert decompose_public_symbols([0,1],[[1]*16]*2,1)['format_accepted']
    stop=FirstCompletion(1)
    for _ in range(64):assert not stop.step(1,[1,65535])
    assert stop.first_completion is None

def test_public_interface_and_sampling_distribution():
    assert list(inspect.signature(observe_stage9).parameters)==['transmitted_utf8','public_profile','cover_context','model','token_attributes']
    from llm_stego_public_key.evaluation.public_prefix import choose_token
    class Capture:
        def choice(self,n,p):
            assert n==16
            expected=np.exp(np.arange(16)-15);expected/=expected.sum()
            assert np.allclose(p,expected,rtol=1e-14);return 3
    assert choose_token(np.arange(16,dtype=float),list(range(16)),'B',Capture())==(3,3)
    p=json.loads((ROOT/'configs/stage9/R32.json').read_text())
    out=observe_stage9(b'\xff',p,p['cover_contexts'][0],None,None)
    assert out['valid_utf8'] is False and out['filler_consistent'] is None
    old=json.loads((ROOT/'configs/stage8/R32.json').read_text());q=dict(p,profile_id=old['profile_id'],cover_contexts=old['cover_contexts']);assert q==old

def test_complete_allocation_and_subset_limits(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'));from run_stage9 import allocation_check
    a=json.loads((ROOT/'artifacts/stage9/allocation.json').read_text());assert allocation_check(a)==dict(seconds=8400,tokens=96000,cases=22)
    from llm_stego_public_key.evaluation.budget import BudgetLedger
    from llm_stego_public_key.errors import BudgetError
    auth=json.loads((ROOT/'configs/stage9/authorization.json').read_text());anchor=auth['previous_checkpoint'];p=tmp_path/'budget.jsonl'
    p.write_bytes((ROOT/'artifacts/project_budget.jsonl').read_bytes()[:anchor['bytes']]);p.with_suffix('.checkpoint.json').write_text(json.dumps(anchor))
    b=BudgetLedger(p,authorization=auth)
    for request in [(8641,64,1),(45,120001,1),(45,64,33)]:
        with pytest.raises(BudgetError):b.reserve(*request,allocation_id=auth['allocation_id'])
    aid=b.reserve(45,128,allocation_id=auth['allocation_id']);b.close()
    b=BudgetLedger(p,authorization=auth);assert b.usage()['tokens']==auth['baseline_usage']['tokens']+128;b.close()
