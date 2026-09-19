"""Compact host-only evidence tables; run after final reconciliation."""
import json,collections,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage8'
s=json.loads((ART/'summary.json').read_text())
records=[json.loads(l) for l in (ART/'cases.jsonl').read_text().splitlines()]
def fmt(x):
 if x is None:return 'NA'
 if isinstance(x,float):return f'{x:.4f}'
 return str(x)
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'---|'*len(headers)]+['| '+' | '.join(fmt(x) for x in row)+' |' for row in rows])
out=[]
out.append('## Fresh attempt-level recovery\n\n'+table(['Method','Payload bytes','Exact / attempted','Capacity failures','Successful tokens','Success bits/token','Attempt mean bits/token','Mean job seconds'],[[r['method'],r['payload_bytes'],f"{r['authenticated_exact']}/{r['attempted']}",r['capacity_failures'],f"{r['carrier_token_min']}–{r['carrier_token_max']}" if r['carrier_token_min'] else 'NA',r['mean_success_payload_bits_per_token'],r['mean_attempt_useful_bits_per_token'],next(x['mean_job_seconds'] for x in s['costs'] if x['phase']=='main_fixed' and x['kind']=='encrypted' and x['method']==r['method'] and x['payload_bytes']==r['payload_bytes'])] for r in s['recovery']]))
check=[]
for phase in ['diagnostic','main_fixed']:
 for method in (['R'] if phase=='diagnostic' else ['F','R']):
  for size in [32,128]:
   subsets=[(x['case_id'],[x]) for x in []]
   rr=[x for x in s['checkpoints'] if x['phase']==phase and x['method']==method and x['payload_class_bytes']==size]
   groups=collections.defaultdict(list)
   for x in rr:groups[x['case_id'] if phase=='diagnostic' else f'{method}/{size}'].append(x)
   for name,xx in groups.items():
    hpke=xx[0]['is_hpke'];field='authenticated_by_budget' if hpke else 'complete_envelope_by_budget'
    check.append([phase,name,'authenticated payload' if hpke else 'raw synthetic envelope']+[f"{sum(x[field] for x in xx if x['budget']==b)}/{sum(x['budget']==b for x in xx)}" for b in [512,1024,1536,1984]])
out.append('## Nested checkpoints (not independent observations)\n\n'+table(['Phase','Group','Recovery meaning','512','1024','1536','1984'],check))
keep=['mean_nll_bits','mean_admissible_nll_bits','mean_log2_rank','format_accepted','format_and_kem_canonical','token_count','utf8_bytes']
out.append('## Matched delivered/scorable recognition against B\n\n'+table(['Method','Score (higher is carrier)','Pairs','Carrier mean','Control mean','AUC','Cluster interval'],[[r['method'],r['metric'],r['matched_scorable_pairs'],r['encrypted_mean'],r['control_mean'],r['auc_higher_is_carrier'],r['cluster_interval']] for r in s['recognition'] if r['metric'] in keep]))
out.append('## All attempted controls and encrypted settings\n\n'+table(['Method','Role','Attempted','Delivered','Scorable','Format accepted','Format + KEM','Candidate membership all'],[[r[k] for k in ['method','role','attempted','delivered','scorable','format_accepted','format_and_kem_canonical','all_candidates_member']] for r in s['recognition_counts']]))
rounding=[]
for method in ['F','R']:
 for kind in ['encrypted','control']:
  rr=[r for r in records if r['method']==method and r['kind']==kind and r.get('observer',{}).get('scorable')]
  if not rr:continue
  steps=[x for r in rr for x in json.loads((ROOT/r['trace_path']).read_text())['public_scoring']['probability_rounding']]
  rounding.append({'method':method,'kind':kind,'messages':len(rr),'steps':len(steps),'mean_message_tv':statistics.mean(r['observer']['probability_rounding_mean_tv'] for r in rr),'max_step_tv':max(x['total_variation'] for x in steps),'mean_message_integer_entropy':statistics.mean(statistics.mean(x['integer_entropy_bits'] for x in json.loads((ROOT/r['trace_path']).read_text())['public_scoring']['probability_rounding']) for r in rr),'mean_message_unrounded_entropy':statistics.mean(statistics.mean(x['unrounded_entropy_bits'] for x in json.loads((ROOT/r['trace_path']).read_text())['public_scoring']['probability_rounding']) for r in rr)})
(ART/'rounding_summary.json').write_text(json.dumps(rounding,indent=2)+'\n')
out.append('## Probability approximation diagnostics\n\n'+table(['Method','Role','Messages','Mean message TV','Maximum step TV','Mean integer entropy','Mean unrounded entropy'],[[x[k] for k in ['method','kind','messages','mean_message_tv','max_step_tv','mean_message_integer_entropy','mean_message_unrounded_entropy']] for x in rounding])+'\n\nThese are descriptive conditional-table differences, not independent token samples or a bound proving sequence-distribution equivalence.')
(ART/'tables.md').write_text('\n\n'.join(out)+'\n')
print('Tables and rounding summaries derived from retained records; no inference')
