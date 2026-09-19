"""Standalone figures from retained Stage9 records; no inference."""
import json,csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage9';FIG=ART/'figures';FIG.mkdir(exist_ok=True)
s=json.loads((ART/'summary.json').read_text());progress=json.loads((ART/'progress.json').read_text());pairs=json.loads((ART/'paired_trajectories.json').read_text());cost=list(csv.DictReader((ART/'costs.csv').open()))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
colors={'R':'#2a5e97','B-fixed':'#9c632c','B-stop':'#3d8a66'}
fig,axes=plt.subplots(2,3,figsize=(12,6.7),sharex=True,sharey=True)
for c,ax in enumerate(axes.flat):
    for row in progress:
        if row['context_index']!=c:continue
        g='R' if row['kind']=='encrypted' else row['family']
        if g=='B-stop':continue # same path as B-fixed up to stopping; show endpoint below
        ax.plot(range(1,len(row['stable_curve'])+1),row['stable_curve'],label=g,color=colors[g],lw=1.3)
    stop=next((r for r in progress if r['case_id']==f'B-stop-c{c}'),None)
    if stop:
        ax.plot(range(1,len(stop['stable_curve'])+1),stop['stable_curve'],color=colors['B-stop'],lw=1,ls='--',label='B-stop (paired path)')
        ax.scatter([stop['emitted_tokens']],[stop['stable_bits_at_end']],color=colors['B-stop'],s=25,zorder=3)
    ax.axhline(800,color='black',lw=.7,ls=':');ax.set_title(f'Context {c}');ax.set_xlim(0,2000);ax.set_ylim(bottom=0)
    if c>=3:ax.set_xlabel('Emitted token position')
    if c%3==0:ax.set_ylabel('Stable arithmetic bits')
axes[0,0].legend(fontsize=8);fig.suptitle('One trajectory per attempt; paired controls share their common prefix')
fig.tight_layout();fig.savefig(FIG/'stable_progress.png');fig.savefig(FIG/'stable_progress.svg');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11,4.3))
for i,g in enumerate(['R','B-fixed','B-stop']):
    c=s['counts'][g]
    for j,k in enumerate(['attempted','delivered','stable_packet_completed']):
        axes[0].bar(i+(j-1)*.22,c[k],.22,color=['#c8c8c8','#7291ad','#387052'][j],label=['Attempted','Delivered','Reached 800 bits'][j] if i==0 else None)
    for j,k in enumerate(['format_accepted','format_and_kem_canonical']):
        d=s['predicate_counts'][g][k];axes[1].bar(i+(j-.5)*.30,d['true'],.30,color=['#527daa','#974d62'][j],label=['Format','Format + KEM'][j] if i==0 else None)
        axes[1].text(i+(j-.5)*.30,d['true']+.07,f"{d['true']}/{d['delivered_scorable_denominator']}",ha='center',fontsize=9)
for ax in axes:
    ax.set_xticks(range(3),['R','B-fixed','B-stop']);ax.set_ylim(0,7);ax.set_ylabel('Messages');ax.legend(fontsize=8)
axes[0].set_title('Attempt and delivery denominators');axes[1].set_title('Public acceptance / delivered scorable count')
fig.tight_layout();fig.savefig(FIG/'completion_format.png');fig.savefig(FIG/'completion_format.svg');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11,4.3))
for p in pairs:
    c=p['context'];xs=[p['fixed_tokens'],p['stop_generated_tokens']];ys=[c-.10,c+.10]
    axes[0].plot(xs,ys,color='#999999');axes[0].scatter(xs,ys,c=[colors['B-fixed'],colors['B-stop']],s=40)
    axes[0].text(xs[1]+15,ys[1],('delivered' if p['stop_delivered'] else 'abort'),fontsize=8)
axes[0].set_yticks(range(6),[f'Context {c}' for c in range(6)]);axes[0].set_xlabel('Tokens: brown fixed / green stopped');axes[0].set_xlim(0,2450);axes[0].set_title('Paired message boundaries; aborts are internal')
for i,g in enumerate(['R','B-fixed','B-stop']):
    rr=[r for r in cost if (r['kind']=='encrypted' if g=='R' else r['family']==g)]
    axes[1].scatter([i]*len(rr),[float(r['job_seconds']) for r in rr],color=colors[g],s=40,alpha=.8)
axes[1].set_xticks(range(3),['R','B-fixed','B-stop']);axes[1].set_ylabel('Startup-inclusive GPU-job seconds');axes[1].set_title('All attempts, including capacity aborts')
fig.tight_layout();fig.savefig(FIG/'boundaries_costs.png');fig.savefig(FIG/'boundaries_costs.svg');plt.close(fig)
print('Wrote three PNG/SVG figures from retained records')
