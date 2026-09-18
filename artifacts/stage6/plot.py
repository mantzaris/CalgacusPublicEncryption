#!/usr/bin/env python3
"""Render retained Stage 6 results on the host; no inference imports."""
import json
from pathlib import Path
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'artifacts/stage6'
OUT=ART/'figures';OUT.mkdir(exist_ok=True)
s=json.loads((ART/'summary.json').read_text())
rows=[json.loads(line) for line in (ART/'cases.jsonl').read_text().splitlines()]
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight','figure.dpi':140})
colors={'L':'#245d91','F':'#008879','Calgacus':'#9a7152'}
def save(fig,name):
    fig.savefig(OUT/(name+'.png'));fig.savefig(OUT/(name+'.pdf'));plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(10,3.8))
for j,m in enumerate(['L','F','Calgacus']):
    rr=[r for r in s['recovery'] if r['method']==m]
    x=np.arange(2)+(j-1)*.24
    fractions=[r['recovery_fraction'] or 0 for r in rr]
    bars=axs[0].bar(x,fractions,.23,color=colors[m],label=m)
    for bar,r in zip(bars,rr):axs[0].text(bar.get_x()+bar.get_width()/2,bar.get_height()+.035,f"{r['authenticated_exact']}/{r['attempted']}",ha='center',fontsize=8)
    axs[1].bar(x,[r['mean_attempt_useful_bits_per_transmitted_token'] or 0 for r in rr],.23,color=colors[m],label=m)
for ax in axs:ax.set_xticks([0,1],['32 bytes','128 bytes']);ax.set_xlabel('Application payload');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
axs[0].set_ylim(0,1.2);axs[0].set_ylabel('Exact recovery / attempted transmission');axs[0].set_yticks([0,.25,.5,.75,1]);axs[0].legend(loc='lower left')
axs[1].set_ylabel('Mean useful payload bits / received token\n(failed attempts assigned zero)');axs[1].legend()
fig.suptitle('Actual UTF-8 transport: main L/F comparison and adapted Calgacus baseline')
fig.text(.5,-.025,'Replays and qualifications excluded; all failed transmissions retained. Four contexts, eight main keys.',ha='center',fontsize=8)
fig.tight_layout();save(fig,'recovery_useful_rate')

metrics=[('prefix_match','Old six-token prefix'),('format_accepted','Public frame accepted'),('format_and_kem_canonical','Frame + canonical KEM'),('member_fraction','Candidate membership'),('mean_nll_bits','Complete-token surprisal'),('after_eight_nll_bits','Surprisal after 8 tokens'),('encrypted_body_nll_bits','Body-token surprisal'),('encrypted_body_log2_rank','Body mean log2 rank'),('token_count','Received token length'),('utf8_bytes','UTF-8 byte length')]
cells=[(m,f) for f in 'ABC' for m in ['L','F']]
array=[];labels=[]
for metric,label in metrics:
    line=[];text=[]
    for m,f in cells:
        r=next(x for x in s['recognition_auc'] if x['method']==m and x['family']==f and x['metric']==metric)
        v=r['auc_higher_is_stego'];line.append(np.nan if v is None else v);text.append('NA' if v is None else f'{v:.3f}\n(n={r["matched_scorable_pairs"]})')
    array.append(line);labels.append(text)
fig,ax=plt.subplots(figsize=(9,6.2));im=ax.imshow(array,vmin=0,vmax=1,cmap='coolwarm',aspect='auto')
ax.set_xticks(range(6),[f'{f}: {m}' for m,f in cells]);ax.set_yticks(range(len(metrics)),[label for metric,label in metrics])
for i,row in enumerate(labels):
    for j,label in enumerate(row):ax.text(j,i,label,ha='center',va='center',fontsize=7,color='black')
ax.set_title('Descriptive AUC; fixed higher-is-stego orientation')
fig.colorbar(im,ax=ax,label='AUC (0.5 = tied/chance ranking)',shrink=.75)
fig.text(.5,.005,'A: full vocabulary; B: probability-weighted admissible; C: uniform admissible.\nMatched scorable deliveries only; no authentication-based selection. Cluster intervals in recognition.csv.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));save(fig,'recognition_auc')

fig,axs=plt.subplots(1,2,figsize=(10.5,4.7))
labels=[];loads=[];enc=[];recv=[];obs=[];over=[]
for method in ['L','F','Calgacus']:
    for size in [32,128]:
        rr=[r for r in rows if r['kind']=='encrypted' and r['stage6_phase']!='qualification' and r['method']==method and r.get('payload_bytes')==size]
        if not rr:continue
        labels.append(f'{method}\n{size} B')
        means=[statistics.mean(r['timings'].get(key,0) for r in rr) for key in ['load_and_verify_seconds','encode_seconds','receiver_seconds','public_scoring_seconds']]
        total=statistics.mean(r['job_elapsed_seconds'] for r in rr)
        loads.append(means[0]);enc.append(means[1]);recv.append(means[2]);obs.append(means[3]);over.append(max(0,total-sum(means)))
x=np.arange(len(labels));bottom=np.zeros(len(x))
for label,values,color in [('Load/verify',loads,'#aaaaaa'),('Encode',enc,'#245d91'),('Receive',recv,'#008879'),('Public scoring',obs,'#b575b8'),('Startup/shutdown/other',over,'#ddba78')]:
    axs[0].bar(x,values,bottom=bottom,label=label,color=color);bottom+=values
axs[0].set_xticks(x,labels);axs[0].set_ylabel('Mean charged GPU-job seconds / attempt');axs[0].legend(fontsize=7,loc='upper left',bbox_to_anchor=(0,-.18),ncol=3);axs[0].set_title('Measured costs, including unsuccessful attempts')
groups=[('L','encrypted'),('F','encrypted'),('Calgacus','encrypted'),('A','control'),('B','control'),('C','control')]
names=['Canonical delivered','Delivered with tokenization drift','Invalid UTF-8 / no delivery','Other failure / no delivery']
values=[[] for _ in names]
for label,kind in groups:
    rr=[r for r in rows if r['kind']==kind and r['stage6_phase']!='qualification' and (r['method']==label if kind=='encrypted' else r.get('family')==label)]
    vals=[sum(r['wire_delivered'] and r.get('serialization_status')=='canonical' for r in rr),sum(r['wire_delivered'] and r.get('serialization_status')=='retokenization_drift' for r in rr),sum(not r['wire_delivered'] and r.get('serialization_status')=='invalid_utf8' for r in rr),sum(not r['wire_delivered'] and r.get('serialization_status')!='invalid_utf8' for r in rr)]
    for col,v in zip(values,vals):col.append(v)
bottom=np.zeros(len(groups))
for label,vs,color in zip(names,values,['#008879','#dfae42','#b54b47','#897ca1']):
    axs[1].bar(range(len(groups)),vs,bottom=bottom,label=label,color=color);bottom+=vs
axs[1].set_xticks(range(len(groups)),[m for m,k in groups]);axs[1].set_ylabel('Attempted transmissions / control generations');axs[1].legend(fontsize=7);axs[1].set_title('Serialization outcomes; no failures replaced')
fig.tight_layout(rect=(0,.08,1,1));save(fig,'costs_failures')

fig,axs=plt.subplots(1,2,figsize=(11,4),sharey=True)
allocation=json.loads((ART/'allocation.json').read_text());slots={x['case_id']:x for x in allocation['slots']}
for ax,size in zip(axs,[32,128]):
    data=[];labels=[];contexts=[]
    for method in ['L','F']:
        for family in ['encrypted','A','B','C']:
            rr=[r for r in rows if r['stage6_phase']=='main_fixed' and r['method']==method and (r.get('payload_bytes',slots[r['case_id']].get('payload_setting_bytes'))==size) and (r['kind']=='encrypted' if family=='encrypted' else r['kind']=='control' and r['family']==family) and r.get('observer',{}).get('encrypted_body_nll_bits') is not None]
            data.append([r['observer']['encrypted_body_nll_bits'] for r in rr]);contexts.append([r['context_index'] for r in rr]);labels.append(f'{method}\n{family}')
    ax.boxplot(data,positions=range(len(data)),widths=.6,showfliers=False)
    for i,(vs,cs) in enumerate(zip(data,contexts)):
        for j,(v,c) in enumerate(zip(vs,cs)):ax.scatter(i+(j-(len(vs)-1)/2)*.04,v,s=20,color=['#245d91','#008879','#bd7229','#984984'][c],zorder=3)
    ax.set_xticks(range(len(labels)),labels,fontsize=8);ax.set_title(f'{size}-byte payload setting');ax.grid(axis='y',alpha=.15)
axs[0].set_ylabel('Canonical-token surprisal after frame + encapsulation\n(bits per token; not UTF-8 string probability)')
fig.suptitle('Complete-message residual score: encrypted-body region')
fig.text(.5,-.025,'Points are messages, colored by public context; no token-level independence assumption.\nControls use the same positional exclusion and contain no encrypted packet; all 128 main outputs were scorable.',ha='center',fontsize=8)
fig.tight_layout();save(fig,'body_score_distributions')
print('Rendered 4 figures in PNG and PDF from retained records; no inference.')
