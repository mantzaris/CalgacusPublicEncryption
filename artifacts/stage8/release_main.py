"""Host-only release decision after completed diagnostics; never starts inference."""
import json,math,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage8'
status=json.loads((ART/'diagnostic_status.json').read_text())
if not status.get('qualification_passed'):raise SystemExit('Qualification did not pass; main release prohibited')
records=[json.loads(l) for l in (ART/'cases.jsonl').read_text().splitlines()]
a=json.loads((ART/'allocation.json').read_text());old=json.loads((ROOT/'artifacts/stage6/summary.json').read_text())
# Full-ceiling three-pass forecast, without assuming future capacity failures
# save time. Scale by the maximum observed per-token long-prefix pass cost.
pass_rates=[]
for r in records:
    tr=json.loads((ROOT/r['trace_path']).read_text())
    for phase,t in tr.items():
        n=len(t.get('advanced_ids',[]));seconds=r['timings'].get(phase+'_seconds')
        if n>=1500 and seconds:pass_rates.append(seconds/n)
if not pass_rates:raise SystemExit('No long-prefix diagnostic measurement for conservative release forecast')
load=max(r['timings']['load_and_verify_seconds'] for r in records)+2
rpass=max(pass_rates)*1984
# Maximum Stage6 F per-cell mean phase costs, used with the margins specified below.
fpass={n:max(x.get('mean_encode_seconds') or 0,x.get('mean_receiver_seconds') or 0,x.get('mean_public_scoring_seconds') or 0) for n in [32,128] for x in old['costs'] if x['method']=='F' and x['kind']=='encrypted' and x['payload_setting_bytes']==n}
forecasts=[]
for repetitions in [2,1]:
    slots=[s for s in a['slots'] if s['stage8_phase']!='diagnostic' and s.get('repetition',0)<repetitions]
    seconds=0;tokens=0
    for slot in slots:
        p=json.loads((ROOT/slot['profile_path']).read_text());n=p['public_size_class']['payload_bytes'];count=1984 if slot['method']=='R' else 2*(68+n)
        passes=3 if slot['kind']=='encrypted' else 2 if slot['kind']=='control' else 1
        cost=rpass if slot['method']=='R' else fpass[n]
        # 10% overall margin; observer pass includes a further10% over codec cost.
        seconds+=(load+cost*(passes+(.1 if passes>1 else 0)))*1.10
        context=len(p['cover_contexts'][slot['context_index']].encode())+1
        tokens+=passes*(count+context)
    full={'seconds':sum(s['reservation'][0] for s in slots),'tokens':sum(s['reservation'][1] for s in slots),'cases':len(slots)}
    forecasts.append({'full_reservations':full,'repetitions':repetitions,'cases':len(slots),'forecast_seconds':seconds,'conservative_evaluated_token_bound':tokens,
                      'fits_stage8':all(full[k]+status['stage8_usage'][k]<=a['additional_limits'][k] for k in full) and seconds+status['stage8_usage']['seconds']<=10800 and tokens+status['stage8_usage']['tokens']<=230000 and len(slots)+len(records)<=88})
chosen=next((x for x in forecasts if x['fits_stage8']),None)
if chosen is None:raise SystemExit('Neither permitted symmetric allocation fits conservative forecast; no main launch')
slots=[s for s in a['slots'] if s['stage8_phase']!='diagnostic' and s.get('repetition',0)<chosen['repetitions']]
r={'schema_version':1,'decision':'proceed_fixed_matrix','repetitions':chosen['repetitions'],'selected_case_ids':[s['case_id'] for s in slots],
 'diagnostic_cases_sha256':hashlib.sha256((ART/'cases.jsonl').read_bytes()).hexdigest(),'diagnostic_source_revision':status['tested_code_commit'],
 'forecast':forecasts,'basis':{'max_observed_long_prefix_seconds_per_token':max(pass_rates),'R_full_1984_pass_seconds':rpass,'load_plus_shutdown_seconds':load,'F_historical_phase_seconds':fpass,
 'margins':'10% overall plus10% extra codec-pass cost for public observer; all R carriers charged in forecast as complete1984 three/two/one-pass jobs, not cheap aborts',
 'limitation':'Not a timing guarantee; unchanged full per-case reservations and deadlines remain authoritative'},
 'reduction_reason':'Two repetitions do not fit conservative startup-inclusive time forecast' if chosen['repetitions']==1 else 'Both repetitions fit forecast',
 'profile_and_inference_change_after_diagnostic':False}
with (ART/'main_release.json').open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(r,indent=2))
