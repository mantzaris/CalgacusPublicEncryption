#!/usr/bin/env python3
"""Leased public-prefix diagnostic worker. No key, payload or authentication path."""
import copy
import json
import os
from pathlib import Path
import sys
import time
import traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.evaluation.worker_lease import verify_worker_lease
JOB=verify_worker_lease(Path(sys.argv[1]),ROOT/'artifacts/project_budget.jsonl') if __name__=='__main__' else None
from gpu_worker import dump,sha
from llm_stego_public_key.codecs.public_utf8_rank16 import PublicUtf8Rank16Codec,InvariantError
from llm_stego_public_key.codecs.llama_backend import load_model
from llm_stego_public_key.evaluation.budget import TokenMeter
from llm_stego_public_key.evaluation.public_prefix import PublicPrediction,predict_public_prefix,generate_prefix,observe_prefix
from llm_stego_public_key.profile import canonical_json
from llm_stego_public_key.errors import RankError


def main():
    if JOB is None: raise RuntimeError('Controller lease required')
    job=JOB;d=Path(sys.argv[1]).parent
    profile=json.loads((ROOT/'configs/public_utf8_rank16_v1.json').read_text())
    runtime=json.loads((ROOT/'configs/local_runtime.json').read_text());cover=profile['cover_contexts'][job['context_index']]
    meter=TokenMeter(job['token_reservation']);model=None;codec=None;started=time.monotonic()
    r={'schema_version':1,'attempt_id':d.name,'case_id':job['case_id'],'kind':job['kind'],'family':job.get('family'),
       'context_index':job['context_index'],'cover_context':cover,'profile_sha256':sha(canonical_json(profile)),
       'tested_code_commit':job['tested_code_commit'],'split':'development_only_excluded_from_future_heldout',
       'pid':os.getpid(),'gpu_uuid':runtime['gpu_uuid'],'success':False,'authenticated':False,'failure_category':None,'timings':{}}
    try:
        model=load_model(runtime,profile,meter);r['timings']['load_and_verify_seconds']=time.monotonic()-started
        codec=PublicUtf8Rank16Codec(model,model.llm._model.token_get_attr)
        meter.phase='public_prediction' if job['kind']=='prediction' else 'six_token_control'
        t=time.monotonic()
        if job['kind']=='prediction':
            prediction=predict_public_prefix(codec,profile,cover)
            prediction['provenance']={'attempt_id':d.name,'tested_code_commit':job['tested_code_commit'],'pid':os.getpid(),
                                      'gpu_uuid':runtime['gpu_uuid'],'computation':'six independent public zero-symbol selections; computed before opening historical carrier files'}
            dump(d/'public_prediction.json',prediction)
            (d/'snippet.txt').write_bytes(prediction['prefix_utf8'].encode('utf-8'))
            r['prediction']=prediction
            r['historical_reanalysis']=[]
            public=PublicPrediction.from_record(prediction)
            # Historical paths are used only after the public prediction has been persisted.
            for path in job['historical_carrier_paths']:
                wire=(ROOT/path).read_bytes()
                observed=observe_prefix(wire,profile,cover,public,model.tokenize)
                r['historical_reanalysis'].append({'path':path,'transport_sha256':sha(wire),'observer':observed,
                    'interpretation':'historical artifact reanalysis, not a new transmission or recovery'})
            if not all(x['observer']['prefix_match'] for x in r['historical_reanalysis']):
                raise RankError('Historical canonical carrier disagrees with the public zero-prefix prediction')
            r['success']=True
        elif job['kind']=='control':
            cached=(ROOT/job['prediction_path']).read_bytes()
            if sha(cached)!=job['prediction_sha256']: raise RuntimeError('Public prediction cache hash mismatch')
            public=PublicPrediction.from_record(json.loads(cached));public.validate(profile,cover)
            wire=generate_prefix(codec,profile,cover,job['family'],job['sampling_seed'])
            r.update(generated_tokens=len(codec.trace['advanced_ids']),sampling_seed=job['sampling_seed'],snippet_bytes_hex=wire.hex(),
                     prediction_cache_key=public.cache_key,prediction_path=job['prediction_path'],prediction_sha256=job['prediction_sha256'])
            r['observer']=observe_prefix(wire,profile,cover,public,model.tokenize)
            try:
                r['snippet_utf8']=wire.decode('utf-8',errors='strict')
            except UnicodeDecodeError:
                (d/'snippet.invalid.bin').write_bytes(wire)
                r.update(serialization_outcome='invalid_utf8',failure_category='tokenization_serialization_drift')
                if job['family'] in ('B','C'): raise InvariantError('Admissible generator emitted invalid UTF-8')
            else:
                (d/'snippet.txt').write_bytes(wire)
                retokenized=model.tokenize(wire);r['retokenized_ids']=retokenized
                r['text_retokenizes']=retokenized==codec.trace['advanced_ids']
                r['serialization_outcome']='canonical' if r['text_retokenizes'] else 'retokenization_change'
                if job['family'] in ('B','C') and not r['text_retokenizes']:
                    raise InvariantError('Admissible generator violated canonical prefix invariant')
                r['success']=True
        else: raise ValueError('Unknown prefix case kind')
        r['timings']['operation_and_host_observation_seconds']=time.monotonic()-t
        actual=len(model.context_ids[cover])+len(codec.trace['advanced_ids'])
        if actual!=job['expected_evaluated_tokens'] or meter.tokens!=actual:
            raise RuntimeError('Context/prefix token accounting differs from frozen prelaunch bound')
    except Exception as exc:
        r.update(success=False,failure_category=getattr(exc,'category','implementation_failure'),error=str(exc),exception_type=type(exc).__name__)
        traceback.print_exc()
    finally:
        if codec is not None:
            r['trace']=copy.deepcopy(codec.trace)
            if codec.trace.get('advanced_ids'): r['retained_generated_prefix_hex']=model.detokenize(codec.trace['advanced_ids']).hex()
        if model is not None:
            r['public_context_token_ids']=model.context_ids;model.close()
        r.update(charged_tokens=meter.tokens,tokens_by_phase=meter.by_phase,worker_seconds=time.monotonic()-started)
        dump(d/'result.json',r)

if __name__=='__main__':main()
