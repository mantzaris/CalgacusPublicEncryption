"""Paper-only factual reconciliation and exhaustive artifact pointers; no inference."""
import base64,hashlib,json,math,statistics,sys
from pathlib import Path
P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from llm_stego_public_key.evaluation.stopping_rule import decompose_public_symbols

def obj(path):return json.loads((ROOT/path).read_text())
def rows(s):return [json.loads(x) for x in (ROOT/f'artifacts/stage{s}/cases.jsonl').read_text().splitlines()]
def trace(r):return obj(r['trace_path'])
d={s:rows(s) for s in (6,7,8,9)};assets=json.loads((P/'review/asset_verification.json').read_text())
checks={}
controls=[r for r in d[6] if r['kind']=='control'];base=[r for r in d[6] if r.get('stage6_phase')=='baseline']
checks['S6_control_drift']=sum(not r['text_retokenizes'] for r in controls);assert checks['S6_control_drift']==4
checks['S6_baseline_drift']=sum(not r['text_retokenizes'] for r in base);assert checks['S6_baseline_drift']==4
for m in ('L','F'):
 rr=[r for r in d[6] if r['kind']=='encrypted' and r['stage6_phase']=='main_fixed' and r['method']==m]
 checks['S6_'+m+'_public_prefix_matches']=sum(r['observer']['prefix']['prefix_match'] for r in rr)
assert checks['S6_L_public_prefix_matches']==16 and checks['S6_F_public_prefix_matches']==0
for f in ('A','B','C'):
 rr=[r for r in controls if r['method']=='F' and r['family']==f]
 checks['S6_F_'+f]={'format':sum(r['observer']['format_accepted'] for r in rr),'kem':sum(r['observer'].get('kem_canonical') is True for r in rr),'count':len(rr)}
assert [checks['S6_F_'+f]['format'] for f in ('A','B','C')]==[0,16,16]
assert [checks['S6_F_'+f]['kem'] for f in ('B','C')]==[16,9]
checks['S6_F_C_format_kem_auc']=(1+(1-9/16))/2;assert checks['S6_F_C_format_kem_auc']==.71875
old={r['case_id']:r for r in d[7]};diag=[r for r in d[8] if r['kind']=='fixture']
for r in diag:
 o=old[r['case_id'].removeprefix('diagnostic-')];a=trace(o)['encode'];b=trace(r)['encode'];n=len(a['advanced_ids'])
 for k in ('advanced_ids','symbols','candidate_steps','arithmetic_steps'):assert a[k]==b[k][:n],(r['case_id'],k)
checks['historical_unchanged_prefixes']=len(diag);assert len(diag)==4
h=obj('artifacts/stage8/historical_diagnosis.json');checks['historical_steps']=sum(c['tokens'] for c in h['cases']);assert checks['historical_steps']==5708
checks['historical_diagnosis']=[]
for c in h['cases']:
 assert c['all_interval_states_agree'] and c['prefix_agreement']
 assert abs(c['finite_rounding_information_difference'])<.000025
 checks['historical_diagnosis'].append({k:c[k] for k in ['case_id','required_bits','tokens','terminal','selected_information_sum','finite_rounding_information_difference']})
 # Independently recompute information and entropy from retained original tables.
 t=trace(old[c['case_id']])['encode'];info=sum(-math.log2(x['frequencies'][symbol]/sum(x['frequencies'])) for x,symbol in zip(t['arithmetic_steps'],t['symbols']))
 assert math.isclose(info,c['selected_information_sum'],abs_tol=1e-8)
 if c['case_id']=='qual-HPKE-32':
  steps=t['arithmetic_steps'];syms=t['symbols'];block=steps[768:1024]
  stable=steps[1023]['stable_bits']-steps[767]['stable_bits'];selected=sum(-math.log2(x['frequencies'][symbol]/65536) for x,symbol in zip(block,syms[768:1024]));entropy=statistics.mean(-sum((f/65536)*math.log2(f/65536) for f in x['frequencies']) for x in block)
  checks['stall_769_to_1024']={'released':stable,'selected_bits':selected,'mean_entropy':entropy};assert stable==0 and abs(selected-.115071)<.000001 and abs(entropy-.005118)<.000001
checkpoints={}
for n in (32,128):
 rr=[r for r in d[8] if r['kind']=='encrypted' and r['method']=='R' and r['payload_setting_bytes']==n]
 checkpoints[n]={k:sum(r['exact_recovery'] and r.get('carrier_tokens',10000)<=k for r in rr) for k in (512,1024,1536,1984)}
assert list(checkpoints[32].values())==[0,1,1,2] and list(checkpoints[128].values())==[0,0,0,0]
checks['S8_checkpoints']=checkpoints
hist=[]
for r in d[8]:
 if r['kind']=='control' and r['method']=='R':
  t=trace(r)['public_scoring'];n=r['payload_setting_bytes']+68;p=decompose_public_symbols(t['symbols'],t['frequency_tables'],n)
  hist.append({'case_id':r['case_id'],'attempt_id':r['attempt_id'],'public_trace':r['trace_path'],'predicates':p})
assert sum(x['predicates']['stable_target_reached'] for x in hist)==2
checks['S8_control_decomposition']=hist
r9=[r for r in d[9] if r['stage9_phase']=='prospective']
checks['S9_counts']={g:{'attempted':len(rr),'delivered':sum(r['wire_delivered'] for r in rr)} for g in ('R','B-fixed','B-stop') for rr in [[r for r in r9 if ('R' if r['kind']=='encrypted' else r['family'])==g]]}
checks['S9_scores']=[{k:r.get(k) for k in ('case_id','attempt_id','transport_bytes','job_elapsed_seconds','timings','tokens_by_phase')}|{'observer':r.get('observer')} for r in r9]
rounding=[v['total_variation'] for r in r9 if r.get('observer',{}).get('scorable') for v in trace(r)['public_scoring']['probability_rounding']]
checks['S9_rounding_max_tv']=max(rounding);assert abs(max(rounding)-.0002383393023811)<1e-12
checks['S9_replay_times']=[r['job_elapsed_seconds'] for r in d[9] if r['kind']=='replay']
# Explicit mappings keep the anonymous manuscript separate from identifying artifact paths.
used={}
for s,rr in d.items():
 for r in rr:
  if r['kind']=='prediction':continue
  used[f'S{s}/{r["case_id"]}']={'attempt_id':r['attempt_id'],'kind':r['kind'],'phase':r.get(f'stage{s}_phase'),'source_revision':r['tested_code_commit'],'record':f'artifacts/stage{s}/cases.jsonl','trace':r['trace_path'],'carrier':r['evidence_dir']+'/carrier.txt' if (ROOT/r['evidence_dir']/'carrier.txt').exists() else None,'profile_id':r.get('profile_id'),'profile_sha256':r.get('profile_sha256')}
figmap={
 'Figure 1':{'type':'conceptual diagram','sources':['docs/protocol.md','docs/threat_model.md','src/llm_stego_public_key/transport/envelope_receiver.py','src/llm_stego_public_key/evaluation/stage9_observer.py']},
 'Figure 2':{'attempts':[f'S8/{r["case_id"]}' for r in d[8] if r['case_id']=='diagnostic-qual-HPKE-32' or (r['kind']=='encrypted' and r['method']=='R')],'values':'encode.arithmetic_steps[].stable_bits; no interpolation or new inference'},
 'Figure 3':{'attempts':[f'S9/{r["case_id"]}' for r in r9 if r['kind']=='control'],'values':'generated/paired_controls.json; public observer predicates; explicit internal aborts'},
 'Figure 4':{'source':'generated/scores.csv','cohorts':['S6 F and its A/B/C controls','S8 R and B on delivered matched support','S9 R and B-fixed on delivered matched support','S9 R and B-stop on delivered matched support'],'values':'public_scoring.nll_bits per received canonical token, averaged by message; no smooth densities'},
 'Table 1':{'sources':['configs/stage6/L.json','configs/stage6/F.json','configs/stage8/F32.json','configs/stage8/R32.json','configs/stage9/R32.json','docs/source_audit.md','docs/stage7_comparator_audit.md'],'type':'descriptive protocol comparison'},
 'Table 2':{'source':'generated/recovery.json','rule':'Every main encrypted and baseline attempt in S6/S8/S9; independent replays joined by source_attempt_id; qualifications excluded'},
 'Table 3':{'source':'generated/predicates.json','rule':'S9 prospective only; pass/fail/NA counts per scorable delivered text; aborts outside wire denominator'},
 'Example 1 / section 5.3':assets['examples'][0],
 'Example 2 / section 5.5':assets['examples'][1]}
# Some original Stage6 filenames spell out variants, resolve exact registered profiles.
figmap['Table 1']['sources']=[str(p.relative_to(ROOT)) for p in sorted((ROOT/'configs/stage6').glob('*.json'))]+figmap['Table 1']['sources'][2:]
out={'schema_version':1,'evidence_revision':'87cc8c8394a1e1b370825cf565bb0e132da14954','figures_tables_examples':figmap,'attempt_index':used,'regenerated_claim_checks':checks,'point_estimates':'Regenerated from records and retained public scoring tables.','uncertainty':'Saved stage-specific recognition.json/bootstrap intervals retained, not pooled or redefined.','inference_calls':0}
(P/'review/claim_evidence.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print('PASS: reconciled every displayed outcome family, historical prefix, checkpoint, public score and explanatory selection. No inference.')
