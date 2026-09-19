"""Host-only publication-exportable plots from retained trajectories and counts."""
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage8';OUT=ART/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
    fig.tight_layout();fig.savefig(OUT/f'{name}.png',dpi=180);fig.savefig(OUT/f'{name}.pdf');plt.close(fig)
def read_csv(p):return list(csv.DictReader(p.open()))
h=json.loads((ART/'historical_diagnosis.json').read_text());fig,axes=plt.subplots(2,2,figsize=(10,7))
for ax,case in zip(axes.flat,h['cases']):
    rows=read_csv(ART/('historical_progress_'+case['case_id']+'.csv'));xx=[int(r['position']) for r in rows]
    ax.plot(xx,[int(r['stable_bits']) for r in rows],label='Stable bits',color='#2166ac')
    accum=[];total=0
    for r in rows:total+=float(r['selected_information_bits']);accum.append(total)
    ax.plot(xx,accum,label='Selected-symbol information',color='#b2182b',linestyle='--')
    ax.axhline(case['required_bits'],color='black',alpha=.5,linestyle=':',label='Required packet bits')
    ax.set(title=case['case_id'],xlabel='Emitted token position',ylabel='Bits');ax.grid(alpha=.2)
axes[0,0].legend(fontsize=8);save(fig,'historical_stable_bits')
if not (ART/'summary.json').exists():print('Historical figure only; current GPU trajectory not interpreted as final');raise SystemExit
s=json.loads((ART/'summary.json').read_text());cap=s['capacity'];fig,axes=plt.subplots(2,2,figsize=(10,7))
for ax,case in zip(axes.flat,[x for x in cap if x['phase']=='diagnostic']):
    p=ART/('progress_'+case['case_id']+'.csv');rows=read_csv(p)
    ax.plot([int(r['position']) for r in rows],[int(r['stable_bits']) for r in rows],label='Single extended trajectory')
    for budget in [512,1024,1536,1984]:ax.axvline(budget,color='grey',alpha=.3,linestyle=':')
    ax.axhline(case['target_bits'],color='black',linestyle='--');ax.set(xlim=(0,2010),title=case['case_id'].replace('diagnostic-qual-',''),xlabel='Emitted tokens',ylabel='Stable packet bits')
save(fig,'extended_diagnostic_progress')
cp=s['checkpoints'];fresh=[x for x in cp if x['phase']=='main_fixed'];diag=[x for x in cp if x['phase']=='diagnostic' and x['is_hpke']]
fig,axes=plt.subplots(1,2,figsize=(10,4))
for method,size in [('F',32),('F',128),('R',32),('R',128)]:
    rr=[x for x in fresh if x['method']==method and x['payload_class_bytes']==size]
    if not rr:continue
    values=[];rate=[]
    for b in [512,1024,1536,1984]:
        block=[x for x in rr if x['budget']==b];values.append(sum(x['authenticated_by_budget'] for x in block)/len(block));rate.append(sum(x['successful_payload_bits_per_token'] for x in block)/len(block))
    axes[0].plot([512,1024,1536,1984],values,marker='o',label=f'{method} / {size} bytes');axes[1].plot([512,1024,1536,1984],rate,marker='o',label=f'{method} / {size} bytes')
if not fresh:
    for x in diag:
        axes[0].scatter(x['budget'],int(x['authenticated_by_budget']),label=x['case_id'] if x['budget']==512 else None)
    axes[1].text(.5,.5,'Fresh comparison not executed',ha='center',transform=axes[1].transAxes)
axes[0].set(ylabel='Authenticated recovery / attempted packets',ylim=(-.05,1.05));axes[1].set(ylabel='Mean useful payload bits/token; abort=0')
for ax in axes:ax.set(xlabel='Carrier-token budget',xticks=[512,1024,1536,1984]);ax.grid(alpha=.2)
axes[0].legend(fontsize=8);save(fig,'completion_checkpoints')
if s['main_executed']:
    fig,axes=plt.subplots(2,2,figsize=(10,7))
    cases={x['case_id']:x for x in s['capacity'] if x['phase']=='main_fixed'}
    for context,ax in enumerate(axes.flat):
        for size,style in [(32,'-'),(128,'--')]:
            case_id=f'R-c{context}-n{size}-r0'
            if case_id not in cases:continue
            rows=read_csv(ART/('progress_'+case_id+'.csv'))
            ax.plot([int(x['position']) for x in rows],[int(x['stable_bits']) for x in rows],linestyle=style,label=f'{size}-byte payload')
        for target in [800,1568]:ax.axhline(target,color='grey',linestyle=':',alpha=.6)
        for budget in [512,1024,1536,1984]:ax.axvline(budget,color='grey',linestyle=':',alpha=.2)
        ax.set(title=f'Context{context}: separate fresh packets',xlabel='Carrier-token position',ylabel='Stable envelope bits',xlim=(0,2010))
    axes[0,0].legend(fontsize=8);save(fig,'fresh_stable_bits')
    fig,axes=plt.subplots(1,2,figsize=(10,4));r=s['recovery'];labels=[f"{v['method']} / {v['payload_bytes']} B" for v in r]
    axes[0].bar(labels,[x['recovery_fraction'] for x in r]);axes[0].set(ylabel='Exact / attempted fresh packets',ylim=(0,1.1))
    for i,x in enumerate(r):axes[0].text(i,x['recovery_fraction']+.025,f"{x['authenticated_exact']}/{x['attempted']}",ha='center')
    cc=[x for x in s['costs'] if x['phase']=='main_fixed' and x['kind']=='encrypted'];axes[1].bar([f"{x['method']} / {x['payload_bytes']} B" for x in cc],[x['mean_job_seconds'] for x in cc]);axes[1].set(ylabel='Mean complete GPU-job seconds (aborts included)')
    save(fig,'recovery_cost')
    fig,ax=plt.subplots(figsize=(8,4));rr=[x for x in s['recognition'] if x['metric'] in ['mean_nll_bits','format_and_kem_canonical','token_count']]
    ax.bar(range(len(rr)),[x['auc_higher_is_carrier'] or 0 for x in rr]);ax.axhline(.5,color='black',linestyle='--')
    ax.set_xticks(range(len(rr)),[x['method']+' '+x['metric'].replace('mean_nll_bits','surprisal').replace('format_and_kem_canonical','format+KEM').replace('token_count','tokens') for x in rr],rotation=30,ha='right')
    ax.set(ylabel='Descriptive AUC; higher is carrier',ylim=(0,1.07),title='B controls: length- and delivery-conditioned comparison')
    for i,x in enumerate(rr):
        if x['auc_higher_is_carrier'] is None:ax.text(i,.03,'NA',ha='center')
        else:ax.text(i,x['auc_higher_is_carrier']+.025,f"n={x['matched_scorable_pairs']}",ha='center',fontsize=8)
    save(fig,'conditional_recognition')
print('Figures generated from retained evidence; no inference')
