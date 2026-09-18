#!/usr/bin/env python3
"""Stage 3 leased worker. All model work runs through the unchanged local GPU loader."""
import copy
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_stego_public_key.evaluation.worker_lease import verify_worker_lease
JOB = verify_worker_lease(Path(sys.argv[1]), ROOT/'artifacts/project_budget.jsonl') if __name__=='__main__' else None

import numpy as np
from gpu_worker import dump, sha
from llm_stego_public_key.codecs.public_utf8_rank16 import PublicUtf8Rank16Codec
from llm_stego_public_key.codecs.llama_backend import load_model
from llm_stego_public_key.cryptography.hpke import ReplayCache, deserialize, seal, public_key
from llm_stego_public_key.errors import RankError, TransportError
from llm_stego_public_key.evaluation.budget import TokenMeter
from llm_stego_public_key.evaluation.rank16_observer import observe_rank16
from llm_stego_public_key.profile import Binding, canonical_json
from llm_stego_public_key.transport.envelope_receiver import receive_envelope_text


def main():
    if JOB is None: raise RuntimeError('Controller lease required')
    job=JOB;directory=Path(sys.argv[1]).parent
    profile=json.loads((ROOT/'configs/public_utf8_rank16_v1.json').read_text())
    runtime=json.loads((ROOT/'configs/local_runtime.json').read_text())
    cover=profile['cover_contexts'][job['context_index']]
    meter=TokenMeter(job['token_reservation']); started=time.monotonic();model=None
    record={'schema_version':1,'attempt_id':directory.name,'case_id':job['case_id'],'kind':job['kind'],
            'tested_code_commit':job['tested_code_commit'],'profile_sha256':sha(canonical_json(profile)),
            'profile_id':profile['profile_id'],'pid':os.getpid(),'gpu_uuid':runtime['gpu_uuid'],
            'split':'development_only_excluded_from_future_heldout','success':False,'authenticated':False,
            'failure_category':None,'timings':{},'cover_context':cover,'traces':{}}
    def new_codec(): return PublicUtf8Rank16Codec(model,model.llm._model.token_get_attr)
    def phase(name, fn):
        c=new_codec();meter.phase=name;t=time.monotonic()
        try: return fn(c)
        finally:
            record['timings'][name+'_seconds']=time.monotonic()-t
            record['traces'][name]=copy.deepcopy(c.trace)
            if name=='encode' and c.trace.get('advanced_ids'):
                record['traces'][name]['partial_prefix_bytes_hex']=model.detokenize(c.trace['advanced_ids']).hex()
    def save_carrier(wire):
        (directory/'carrier.txt').write_bytes(wire)
        record.update(transport_utf8=wire.decode('utf-8'),transport_sha256=sha(wire),transport_bytes=len(wire),
                      carrier_tokens=len(model.tokenize(wire)))
    try:
        model=load_model(runtime,profile,meter)
        record['timings']['load_and_verify_seconds']=time.monotonic()-started
        if job['kind'] in ('fixture','encrypted'):
            if job['kind']=='fixture':
                envelope=bytes.fromhex(job['envelope_hex'])
                record.update(fixture_source_attempt_id=job['fixture_source_attempt_id'],hpke_new_profile_binding=False)
            else:
                payload=bytes.fromhex(job['payload_hex']);sk=bytes.fromhex(job['TEST_ONLY_private_key_hex'])
                serialized=seal(payload,public_key(sk),Binding.from_profile(profile,cover))
                envelope=deserialize(serialized)
                record.update(payload_bytes=len(payload),payload_sha256=sha(payload),key_id=job['key_id'],
                              receiver_public_key_hex=public_key(sk).hex(),serialized_base64=serialized,
                              hpke_new_profile_binding=True)
            record.update(envelope_bytes=len(envelope),envelope_sha256=sha(envelope),
                          analytical_carrier_tokens=2*(4+len(envelope)))
            wire=phase('encode',lambda c:c.embed(envelope,profile,cover));save_carrier(wire)
            record['text_retokenizes']=record['traces']['encode']['first_transport_divergence'] is None
            if job['kind']=='fixture':
                recovered=phase('fixture_decoder',lambda c:c.extract((directory/'carrier.txt').read_bytes(),profile,cover))
                record['recovered_envelope_sha256']=sha(recovered)
                record['envelope_exact_recovery']=recovered==envelope
                if recovered!=envelope: raise RankError('Fixture public envelope mismatch')
            else:
                recovered=phase('receiver',lambda c:receive_envelope_text((directory/'carrier.txt').read_bytes(),sk,profile,cover,c,ReplayCache()))
                record.update(authenticated=True,recovered_sha256=sha(recovered),exact_recovery=recovered==payload)
                if recovered!=payload: raise RankError('Authenticated but incorrect plaintext')
                record['observer']=phase('public_extraction',lambda c:observe_rank16(c,(directory/'carrier.txt').read_bytes(),profile,cover))
                if not record['observer']['format_valid'] or record['observer']['envelope_sha256']!=sha(envelope):
                    raise RankError('Public extraction differs from the encoded envelope')
                record['net_payload_bits_per_token']=8*len(payload)/record['carrier_tokens']
            record['success']=True
        elif job['kind']=='replay':
            wire=(ROOT/job['carrier_path']).read_bytes();record['transport_sha256']=sha(wire)
            sk=bytes.fromhex(job['TEST_ONLY_private_key_hex'])
            recovered=phase('fresh_receiver',lambda c:receive_envelope_text(wire,sk,profile,cover,c,ReplayCache()))
            record.update(success=True,authenticated=True,recovered_sha256=sha(recovered),recovered_bytes=len(recovered))
        elif job['kind']=='control':
            meter.phase='ordinary_control';t=time.monotonic();model.begin(cover)
            rng=np.random.Generator(np.random.PCG64(job['sampling_seed']));ids=[]
            record['control_ids']=ids
            for _ in range(job['target_tokens']):
                values=model.logits().astype(np.float64);probabilities=np.exp(values-values.max());probabilities/=probabilities.sum()
                token=int(rng.choice(len(probabilities),p=probabilities));model.advance(token);ids.append(token)
            wire=model.detokenize(ids);record['timings']['ordinary_control_seconds']=time.monotonic()-t
            record['carrier_bytes_hex']=wire.hex()
            try: wire.decode('utf-8',errors='strict')
            except UnicodeDecodeError as exc: raise TransportError('Ordinary control is not UTF-8') from exc
            save_carrier(wire);record['generated_tokens']=len(ids);record['sampling_seed']=job['sampling_seed']
            record['text_retokenizes']=model.tokenize(wire)==ids
            record['observer']=phase('public_extraction',lambda c:observe_rank16(c,wire,profile,cover))
            record['success']=True
        else: raise ValueError('Unknown fixed-allocation case kind')
    except Exception as exc:
        record.update(success=False,failure_category=getattr(exc,'category','implementation_failure'),
                      error=str(exc),exception_type=type(exc).__name__)
        traceback.print_exc()
    finally:
        if model is not None:
            record['public_context_token_ids']=model.context_ids
            model.close()
        record.update(charged_tokens=meter.tokens,tokens_by_phase=meter.by_phase,worker_seconds=time.monotonic()-started)
        dump(directory/'result.json',record)

if __name__=='__main__': main()
