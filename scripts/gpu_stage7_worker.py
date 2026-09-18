#!/usr/bin/env python3
"""Leased Stage 7 worker; each call owns a fresh GPU model/cache process."""
import copy
import json
import os
from pathlib import Path
import sys
import time
import traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.evaluation.worker_lease import verify_worker_lease
JOB=verify_worker_lease(Path(sys.argv[1]),ROOT/'artifacts/project_budget.jsonl') if __name__=='__main__' else None
import numpy as np
from gpu_worker import dump,sha
from llm_stego_public_key.codecs.public_utf8_rank16 import PublicUtf8Rank16Codec,InvariantError
from llm_stego_public_key.codecs.stage7_transport import Arithmetic16Codec,FixedClassRank16Codec
from llm_stego_public_key.codecs.calgacus import CalgacusCodec,first_difference
from llm_stego_public_key.codecs.llama_backend import load_model
from llm_stego_public_key.cryptography.hpke import seal,deserialize,public_key,ReplayCache
from llm_stego_public_key.evaluation.budget import TokenMeter
from llm_stego_public_key.evaluation.public_prefix import predict_public_prefix,choose_token
from llm_stego_public_key.evaluation.stage7_observer import observe_stage7
from llm_stego_public_key.transport.envelope_receiver import receive_envelope_text
from llm_stego_public_key.transport.receiver import receive
from llm_stego_public_key.profile import Binding,canonical_json
from llm_stego_public_key.errors import Stage1Error,RankError,TransportError


def candidate_summary(trace):
    steps=trace.get('candidate_steps',[])
    return {'steps':len(steps),'examined_total':sum(x['examined'] for x in steps),
            'examined_max':max((x['examined'] for x in steps),default=None),
            'rejected':{k:sum(x['rejected'][k] for x in steps) for k in ['special_control','empty','invalid_utf8','noncanonical']}}


def main():
    if JOB is None:raise RuntimeError('Controller lease required')
    job=JOB;d=Path(sys.argv[1]).parent
    profile=json.loads((ROOT/job['profile_path']).read_text())
    admission=profile
    runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
    cover=profile['cover_contexts'][job['context_index']]
    meter=TokenMeter(job['token_reservation']);started=time.monotonic();model=None;traces={}
    r={'schema_version':1,'attempt_id':d.name,'case_id':job['case_id'],'kind':job['kind'],
       'stage7_phase':job['stage7_phase'],'method':job['method'],'context_index':job['context_index'],
       'family':job.get('family'),'pair_id':job.get('pair_id'),'payload_setting_bytes':profile['public_size_class']['payload_bytes'],
       'tested_code_commit':job['tested_code_commit'],'profile_sha256':sha(canonical_json(profile)),
       'profile_id':profile['profile_id'],'cover_context':cover,'split':job['split'],
       'pid':os.getpid(),'gpu_uuid':runtime['gpu_uuid'],'success':False,'authenticated':False,
       'exact_recovery':False,'wire_delivered':False,'failure_category':None,'timings':{},'candidate_costs':{}}
    def codec():
        cls=Arithmetic16Codec if job['method']=='R' else FixedClassRank16Codec
        return cls(model,model.llm._model.token_get_attr)
    def phase(name,fn):
        c=codec();meter.phase=name;t=time.monotonic()
        try:return fn(c)
        finally:
            r['timings'][name+'_seconds']=time.monotonic()-t
            traces[name]=copy.deepcopy(c.trace);r['candidate_costs'][name]=candidate_summary(c.trace)
            if name=='encode':
                ids=c.trace.get('advanced_ids',c.trace.get('carrier_ids',[]))
                if ids:(d/'partial_emission.bin').write_bytes(model.detokenize(ids))
    def save_wire(wire,intended_ids):
        r.update(transport_bytes=len(wire),transport_sha256=sha(wire),intended_carrier_tokens=len(intended_ids))
        try:wire.decode('utf-8',errors='strict')
        except UnicodeError:
            (d/'carrier.invalid.bin').write_bytes(wire)
            r.update(serialization_status='invalid_utf8',failure_category='tokenization_serialization_drift')
            if job['method'] in ('R','F') and job.get('family')!='A':raise InvariantError('Canonical emitter produced invalid UTF-8')
            return False
        (d/'carrier.txt').write_bytes(wire)
        received=model.tokenize(wire)
        r.update(wire_delivered=True,carrier_tokens=len(received),text_retokenizes=received==intended_ids,
                 first_transport_divergence=first_difference(intended_ids,received),
                 serialization_status='canonical' if received==intended_ids else 'retokenization_drift')
        if received!=intended_ids and job['method'] in ('R','F') and job.get('family')!='A':
            raise InvariantError('Canonical emitter violated retokenization invariant')
        return True
    def public_score(wire,pk):
        meter.phase='public_scoring';t=time.monotonic()
        try:
            out=observe_stage7(wire,profile,cover,pk,model,model.llm._model.token_get_attr)
            traces['public_scoring']=out.pop('trace',{})
            r['candidate_costs']['public_scoring']=candidate_summary(traces['public_scoring'])
            r['observer']=out
        finally:r['timings']['public_scoring_seconds']=time.monotonic()-t
    try:
        model=load_model(runtime,profile,meter);r['timings']['load_and_verify_seconds']=time.monotonic()-started
        if job['kind']=='encrypted':
            payload=bytes.fromhex(job['payload_hex']);sk=bytes.fromhex(job['TEST_ONLY_private_key_hex']);pk=public_key(sk)
            binding=Binding.from_profile(profile,cover)
            source=seal(payload,pk,binding);envelope=deserialize(source)
            r.update(payload_bytes=len(payload),payload_sha256=sha(payload),key_id=job['key_id'],receiver_public_key_hex=pk.hex(),
                     envelope_bytes=len(envelope),envelope_sha256=sha(envelope),ciphertext_sha256=sha(envelope[32:]),
                     encapsulation_hex=envelope[:32].hex(),serialized_base64=source)
            wire=phase('encode',lambda c:c.encode(source,cover) if job['method']=='Calgacus' else c.embed(envelope,profile,cover))
            ids=traces['encode'].get('advanced_ids',traces['encode'].get('carrier_ids',[]))
            if save_wire(wire,ids):
                try:
                    def receive_wire(c):
                        with_replay=ReplayCache()
                        try:
                            raw=(d/'carrier.txt').read_bytes()
                            return receive(raw,sk,binding,cover,c,with_replay) if job['method']=='Calgacus' else receive_envelope_text(raw,sk,profile,cover,c,with_replay)
                        finally:with_replay.close()
                    recovered=phase('receiver',receive_wire)
                    r.update(authenticated=True,recovered_sha256=sha(recovered),exact_recovery=recovered==payload,success=recovered==payload)
                    if len(recovered)!=profile['public_size_class']['payload_bytes']:raise RankError('Authenticated public size class mismatch')
                    if recovered!=payload:raise RankError('Authenticated but incorrect plaintext')
                except Stage1Error as exc:
                    r.update(receiver_error=str(exc),failure_category=exc.category)
                    if isinstance(exc,RankError):raise
                enc=traces['encode'];dec=traces.get('receiver',{})
                r['first_rank_divergence']=first_difference(enc.get('symbols',enc.get('source_ranks',[])),dec.get('symbols',dec.get('received_ranks',[])))
                if not r['text_retokenizes']:
                    r.update(success=False,failure_category='tokenization_serialization_drift')
                elif not r['success'] and r['first_rank_divergence'] is not None:
                    raise RankError('Unexpected conditional rank divergence')
                public_score((d/'carrier.txt').read_bytes(),pk)
                if r['exact_recovery'] and (not r['observer']['format_accepted'] or r['observer']['envelope_sha256']!=sha(envelope)):
                    raise RankError('Public extraction disagrees with envelope after exact recovery')
                r['successful_payload_bits_per_token']=8*len(payload)/r['carrier_tokens'] if r['exact_recovery'] else None
                r['attempt_useful_bits_per_transmitted_token']=8*len(payload)/r['carrier_tokens'] if r['exact_recovery'] else 0.0
        elif job['kind']=='fixture':
            envelope=bytes.fromhex(job['synthetic_envelope_hex'])
            r.update(envelope_bytes=len(envelope),envelope_sha256=sha(envelope))
            wire=phase('encode',lambda c:c.embed(envelope,profile,cover))
            if save_wire(wire,traces['encode']['advanced_ids']):
                recovered=phase('public_fixture_inverse',lambda c:c.extract((d/'carrier.txt').read_bytes(),profile,cover))
                r.update(exact_envelope_recovery=recovered==envelope,success=recovered==envelope)
                if recovered!=envelope:raise RankError('Wrong synthetic packet inverse')
        elif job['kind']=='control':
            meter.phase='control_generation';t=time.monotonic()
            c=Arithmetic16Codec(model,model.llm._model.token_get_attr);c._start(admission,cover,'control')
            ids=c.trace['advanced_ids'];rng=np.random.Generator(np.random.PCG64(job['sampling_seed']))
            r.update(sampling_seed=job['sampling_seed'],target_tokens=job['target_tokens'])
            try:
                for _ in range(job['target_tokens']):
                    eligible=c.candidates(ids) if job['family'] in ('B','C') else []
                    token,symbol=choose_token(model.logits(),eligible,job['family'],rng);c._advance(token,symbol)
                wire=model.detokenize(ids)
            finally:
                r['timings']['control_generation_seconds']=time.monotonic()-t
                traces['control_generation']=c.trace;r['candidate_costs']['control_generation']=candidate_summary(c.trace)
                if ids:(d/'partial_emission.bin').write_bytes(model.detokenize(ids))
            r['generated_tokens']=len(ids)
            if save_wire(wire,ids):
                public_score((d/'carrier.txt').read_bytes(),bytes.fromhex(job['recipient_public_key_hex']))
                r['success']=True
        elif job['kind']=='replay':
            wire=(ROOT/job['carrier_path']).read_bytes();sk=bytes.fromhex(job['TEST_ONLY_private_key_hex'])
            r.update(transport_sha256=sha(wire),wire_delivered=True,transport_bytes=len(wire),carrier_tokens=len(model.tokenize(wire)))
            def replay_wire(c):
                cache=ReplayCache()
                try:return receive_envelope_text(wire,sk,profile,cover,c,cache)
                finally:cache.close()
            recovered=phase('fresh_receiver',replay_wire)
            r.update(success=True,authenticated=True,recovered_sha256=sha(recovered),recovered_bytes=len(recovered))
        else:raise ValueError('Unknown Stage 7 case kind')
    except Exception as exc:
        r.update(success=False,failure_category=getattr(exc,'category','implementation_failure'),error=str(exc),exception_type=type(exc).__name__)
        # Calgacus's invalid-byte failure occurs inside its unchanged encoder.
        enc=traces.get('encode',{})
        if job['method']=='Calgacus' and enc.get('carrier_bytes_hex') and not r['wire_delivered']:
            raw=bytes.fromhex(enc['carrier_bytes_hex']);(d/'carrier.invalid.bin').write_bytes(raw)
            r.update(transport_bytes=len(raw),transport_sha256=sha(raw),serialization_status='invalid_utf8',intended_carrier_tokens=len(enc.get('carrier_ids',[])))
        traceback.print_exc()
    finally:
        dump(d/'traces.json',traces);r['trace_path']=str((d/'traces.json').relative_to(ROOT))
        if model is not None:r['public_context_token_ids']=model.context_ids;model.close()
        r.update(charged_tokens=meter.tokens,tokens_by_phase=meter.by_phase,worker_seconds=time.monotonic()-started)
        if job['kind']=='encrypted' and not r['exact_recovery']:r['attempt_useful_bits_per_transmitted_token']=0.0
        dump(d/'result.json',r)

if __name__=='__main__':main()
