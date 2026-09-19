"""Compact tables from reconciled Stage9 output only."""
import csv,json,statistics
from pathlib import Path
ART=Path(__file__).resolve().parent
s=json.loads((ART/'summary.json').read_text());cases=[json.loads(x) for x in (ART/'cases.jsonl').read_text().splitlines()];by={r['case_id']:r for r in cases}
def flag(x):return 'NA' if x is None else 'pass' if x else 'fail'
def p(r,k):return r.get('observer',{}).get(k)
def fmt(x):return 'NA' if x is None else f'{x:.4f}' if isinstance(x,float) else str(x)
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(fmt,row))+' |\n' for row in rows)
text='# Stage9 derived tables\n\n## Attempt and delivery denominators\n\n'
text+=table(['Group','Attempted','800-bit complete','Delivered/scorable','Exact authenticated','Capacity aborts'],[[g,c['attempted'],c['stable_packet_completed'],f"{c['delivered']}/{c['scorable']}",c['authenticated_exact'],c['capacity_aborts']] for g,c in s['counts'].items()])
text+='\nB-fixed complete means800 stable bits, distinct from successfully emitting its assigned length. B-stop/R capacity aborts have no delivered-message observer. Controls are never privately authenticated.\n\n## Per-context prospective outcomes\n\n'
rr=[]
for c in range(6):
    r=by.get(f'R-c{c}',{});f=by.get(f'B-fixed-c{c}',{});b=by.get(f'B-stop-c{c}',{})
    rr.append([c,f"exact/{r['carrier_tokens']}" if r.get('authenticated_message_recovery') else r.get('failure_category','unattempted'),f.get('carrier_tokens'),p(f,'first_completion_token'),b.get('generated_tokens'),b.get('generation_completion',{}).get('first_completion_token'),p(f,'format_accepted'),p(b,'format_accepted'),p(b,'filler_consistent'),p(b,'canonical_replay_consistent'),p(b,'kem_canonical')])
text+=table(['Context','R outcome/tokens','B-fixed length','Fixed first800','B-stop emitted','Stop first800','Fixed format','Stop format','Stop filler','Stop replay','Stop KEM'],[[*row[:6],*[flag(x) for x in row[6:]]] for row in rr])
text+='\n## Separate public predicates\n\n'
rr=[]
for g,pp in s['predicate_counts'].items():
    for k,d in pp.items():rr.append([g,k,d['true'],d['false'],d['unavailable'],d['delivered_scorable_denominator']])
text+=table(['Group','Predicate','True','False','Unavailable','Scorable denominator'],rr)
text+='\n## Complete-message raw scores\n\n'
rr=[]
for r in cases:
    if r['stage9_phase']=='prospective' and r.get('observer',{}).get('scorable'):
        rr.append([r['case_id'],r['carrier_tokens'],r['transport_bytes'],p(r,'mean_nll_bits'),p(r,'mean_log2_rank'),p(r,'mean_admissible_nll_bits')])
text+=table(['Case','Tokens','UTF8 bytes','NLL bits/token','Mean log2 rank','Admissible NLL bits/token'],rr)
text+='\nThese are canonical-token path scores, not UTF8-string probabilities. No absent/aborted message is assigned a score. Higher-is-R orientations remain fixed.\n\n## Inclusive resource costs\n\n'
rr=[]
for g in ['R','B-fixed','B-stop']:
    rs=[r for r in cases if r['stage9_phase']=='prospective' and ('R' if r['kind']=='encrypted' else r['family'])==g]
    if not rs:continue
    obs=[r['timings']['public_scoring_seconds'] for r in rs if 'public_scoring_seconds' in r['timings']]
    gen=[r['timings'].get('encode_seconds',r['timings'].get('control_generation_seconds')) for r in rs]
    rr.append([g,len(rs),statistics.mean(r['job_elapsed_seconds'] for r in rs),statistics.mean(gen),statistics.mean(obs) if obs else None,len(obs),sum(r['charged_tokens'] for r in rs)])
text+=table(['Group','Attempted','Mean job seconds','Mean encode/generate seconds','Mean observer seconds','Observer passes','Evaluated tokens'],rr)
text+='\nJob and generation means include failures; observer mean is conditional on an actual pass. Startup, receiver and shutdown are included in full jobs.\n'
(ART/'tables.md').write_text(text)
print(text)
