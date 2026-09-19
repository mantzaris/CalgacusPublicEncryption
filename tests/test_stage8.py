"""Only changed profile, binding, accounting and prefix-comparison contracts."""
import hashlib,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
from llm_stego_public_key.profile import Binding,validate_supported_profile
from llm_stego_public_key.cryptography.hpke import seal,open_message,generate_key_pair,ReplayCache
from llm_stego_public_key.errors import AuthenticationError,BudgetError,FramingError

def test_profiles_change_only_declared_fields():
    for method in ['F','R']:
      for n in [32,128]:
        old=json.loads((ROOT/f'configs/stage7/{method}{n}.json').read_text());new=json.loads((ROOT/f'configs/stage8/{method}{n}.json').read_text());validate_supported_profile(new)
        new['profile_id']=old['profile_id']
        if method=='R':assert new['tokens']['max_tokens']==new['framing']['maximum_carrier_tokens']==1984;new['tokens']['max_tokens']=1536;new['framing']['maximum_carrier_tokens']=1536
        assert old==new
    baseline=json.loads((ROOT/'artifacts/stage8/starting_state.json').read_text())['tracked_files']
    for p in ['src/llm_stego_public_key/codecs/arithmetic_core.py','src/llm_stego_public_key/codecs/stage7_transport.py','src/llm_stego_public_key/codecs/public_utf8_rank16.py','src/llm_stego_public_key/evaluation/public_prefix.py']:
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==baseline[p]

def test_profile_binding_preserves_original_authentication():
    old=json.loads((ROOT/'configs/stage7/R32.json').read_text());new=json.loads((ROOT/'configs/stage8/R32.json').read_text());c=old['cover_contexts'][2]
    sk,pk=generate_key_pair();source=seal(bytes(range(32)),pk,Binding.from_profile(old,c));cache=ReplayCache()
    try:
        with pytest.raises(AuthenticationError):open_message(source,sk,Binding.from_profile(new,c),cache)
        assert open_message(source,sk,Binding.from_profile(old,c),cache)==bytes(range(32))
    finally:cache.close()

def test_new_receiver_count_and_context_bounds():
    from test_stage6 import Toy
    from llm_stego_public_key.codecs.stage7_transport import Arithmetic16Codec
    p=json.loads((ROOT/'configs/stage8/R32.json').read_text());c=Arithmetic16Codec(Toy(),lambda t:4)
    with pytest.raises(FramingError):c.extract(b'A'*1985,p,p['cover_contexts'][0])
    check=json.loads((ROOT/'artifacts/stage8/context_window_check.json').read_text())
    assert [r['actual_context_tokens'] for r in check['contexts']]==[12,12,10,11]
    assert all(r['total_positions']<=2048 for r in check['contexts'])

def test_suballocation_same_lifetime_crash_and_limits(tmp_path):
    from llm_stego_public_key.evaluation.budget import BudgetLedger
    auth=json.loads((ROOT/'configs/stage8/authorization.json').read_text());old=auth['previous_checkpoint'];p=tmp_path/'ledger.jsonl'
    p.write_bytes((ROOT/'artifacts/project_budget.jsonl').read_bytes()[:old['bytes']]);p.with_suffix('.checkpoint.json').write_text(json.dumps(old))
    b=BudgetLedger(p,authorization=auth);assert b.limits==old['limits']
    with pytest.raises(BudgetError):BudgetLedger(p,authorization=auth)
    for request in [(10801,64,1),(45,230001,1),(45,64,89)]:
        with pytest.raises(BudgetError):b.reserve(*request,allocation_id=auth['allocation_id'])
    aid=b.reserve(45,128,allocation_id=auth['allocation_id']);b.close()
    b=BudgetLedger(p,authorization=auth);assert b.usage()['tokens']==auth['baseline_usage']['tokens']+128
    b.settle(aid,10,16);b.close();assert json.loads(p.with_suffix('.checkpoint.json').read_text())['limits']==old['limits']

def test_prefix_checker_detects_each_contract(monkeypatch,tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'));import run_stage8
    monkeypatch.setattr(run_stage8,'ROOT',tmp_path)
    item={'advanced_ids':[7],'candidate_steps':[{'ordered_ids_sha256':'abc'}],'arithmetic_steps':[{'frequencies':[4096]*16,'stable_bits':4,'low':0,'high_inclusive':2**32-1,'pending_underflow':0}]}
    (tmp_path/'old.json').write_text(json.dumps({'encode':item}));(tmp_path/'new.json').write_text(json.dumps({'encode':item}))
    old={'attempt_id':'old','trace_path':'old.json'};new={'attempt_id':'new','trace_path':'new.json','case_id':'test'}
    assert run_stage8.prefix_check(new,old)['prefix_agreement']
    for field in ['advanced_ids','candidate_steps','arithmetic_steps']:
        bad=json.loads(json.dumps(item))
        if field=='advanced_ids':bad[field][0]=8
        elif field=='candidate_steps':bad[field][0]['ordered_ids_sha256']='bad'
        else:bad[field][0]['stable_bits']=3
        (tmp_path/'new.json').write_text(json.dumps({'encode':bad}));assert not run_stage8.prefix_check(new,old)['prefix_agreement']
