"""Standard host plotting from reconciled records; never loads a model."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage7';OUT=ART/'figures';OUT.mkdir(exist_ok=True)
s=json.loads((ART/'summary.json').read_text());plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})

def save(fig,name):
    fig.tight_layout();fig.savefig(OUT/f'{name}.png',dpi=180);fig.savefig(OUT/f'{name}.pdf');plt.close(fig)

c=s['capacity'];fig,axes=plt.subplots(1,2,figsize=(11,4))
labels=[x['case_id'] for x in c];colors=['#238b45' if x['success'] else '#c0392b' for x in c]
axes[0].bar(range(len(c)),[x['emitted_tokens'] for x in c],color=colors);axes[0].axhline(1536,color='black',linestyle='--',label='Frozen ceiling1536')
axes[0].set(ylabel='Emitted tokens (including sender aborts)',title='Arithmetic finite-packet capacity');axes[0].legend()
axes[1].bar(range(len(c)),[x['stable_bits']/x['target_bits'] for x in c],color=colors);axes[1].axhline(1,color='black',linestyle='--');axes[1].set(ylabel='Stable recovered prefix / required bits',title='Terminal progress; red = failure')
for ax in axes:ax.set_xticks(range(len(c)),labels,rotation=90);ax.grid(axis='y',alpha=.2)
save(fig,'arithmetic_capacity')
if s['main_executed']:
    rr=s['recovery'];fig,axes=plt.subplots(1,2,figsize=(9,4));labels=[f"{r['method']} / {r['payload_bytes']} B" for r in rr]
    axes[0].bar(labels,[r['recovery_fraction'] for r in rr],color=['#4477aa']*2+['#cc6677']*2);axes[0].set(ylabel='Exact recovery / all attempts',ylim=(0,1.1),title='Main transmissions (replays excluded)')
    for i,r in enumerate(rr):axes[0].text(i,r['recovery_fraction']+.02,f"{r['authenticated_exact']}/{r['attempted']}",ha='center')
    axes[1].bar(labels,[r['mean_attempt_useful_bits_per_token'] for r in rr]);axes[1].set(ylabel='Mean useful payload bits/token',title='Failure-inclusive attempt mean')
    save(fig,'recovery_rate')
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    for ax,family in zip(axes,'AB'):
        r=[x for x in s['recognition'] if x['family']==family and x['metric'] in ['mean_nll_bits','format_and_kem_canonical','token_count']]
        xx=list(range(len(r)));ax.bar(xx,[v['auc_higher_is_carrier'] or 0 for v in r]);ax.axhline(.5,color='black',linestyle='--');ax.set_xticks(xx,[v['method']+' '+v['metric'].replace('mean_nll_bits','NLL').replace('format_and_kem_canonical','format+KEM').replace('token_count','tokens') for v in r],rotation=55,ha='right');ax.set(title='Control '+family,ylim=(0,1.07))
        for i,v in enumerate(r):
            if v['auc_higher_is_carrier'] is None:ax.text(i,.03,'NA',ha='center')
    axes[0].set_ylabel('Descriptive AUC; higher is carrier');save(fig,'recognition')
fig,ax=plt.subplots(figsize=(9,4));cc=s['costs'];labels=[f"{x['phase']}\n{x['kind']} {x['method']} {x['family']} {x['payload_bytes']}" for x in cc]
ax.bar(range(len(cc)),[x['mean_job_seconds'] for x in cc]);ax.set_xticks(range(len(cc)),labels,rotation=90);ax.set(ylabel='Mean startup-inclusive GPU-job seconds',title='Cost includes failures and all job phases');save(fig,'resource_cost')
print('Generated compact figures from summary.json; no inference')
