"""Regenerate manuscript assets from immutable saved records. NO model calls.

Run with the existing matplotlib environment. All writes stay in this paper.
The manifest records every read file, figure, table and illustrative selection.
"""
import base64
import csv
import hashlib
import json
import math
import statistics as st
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_stego_public_key.evaluation.stopping_rule import decompose_public_symbols

INPUTS = {}
def read(path):
    p = ROOT / path
    raw = p.read_bytes()
    INPUTS[str(p.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    return raw
def obj(path): return json.loads(read(path))
def rows(stage):
    return [json.loads(x) for x in read(f'artifacts/stage{stage}/cases.jsonl').splitlines()]
def dump(path, value):
    (PAPER / path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
def write_csv(path, rr):
    with (PAPER / path).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rr[0])); w.writeheader(); w.writerows(rr)
def mean(v): return st.mean(v) if v else None
def auc(pos, neg):
    return sum((x > y) + .5*(x == y) for x in pos for y in neg) / (len(pos)*len(neg))
def size(r): return r.get('payload_setting_bytes', r.get('payload_bytes'))
def trace(r): return obj(r['trace_path'])


PROFILE_TABLE = '\\begin{table*}[t]\n\\caption{Evaluated transport profiles. All encrypted rows use the same established HPKE role, protecting the inner record rather than hiding the existence of communication. The profile, context and indicated size policy are public and authenticated through the binding. A/B/C are unencrypted diagnostic generators, not competing encryption schemes.}\n\\label{tab:profiles}\n\\centering\\small\n\\begin{tabular}{p{.80in}p{1.35in}p{1.65in}p{1.67in}}\n\\hline\nMethod & Public size information & Mapping/support & Framing and end condition\\\\\n\\hline\nAdapted Calgacus & Bounded Base64 envelope & Full-vocabulary conditional rank transfer & Source-token count; actual text is retokenized\\\\\nLength rank (L) & Four-byte outer envelope length & Two nibbles/byte on canonical 16 & Header then envelope; 208/400 tokens\\\\\nInferred rank (F) & Envelope length from token count; later fixed class & Same canonical 16, high nibble first & No outer header; 200/392 tokens\\\\\nArithmetic (R) & Pre-agreed 100/196-byte envelope class & Integer probability intervals on the same 16 & First stable packet; midpoint/replay; 1536 then 1984 ceiling\\\\\nControls & Assigned length or agreed packet target & A: full vocabulary; B: weighted 16; C: uniform 16 & Fixed length; B-stop instead ends at first stable packet\\\\\n\\hline\n\\end{tabular}\n\\end{table*}'
(PAPER/'generated/table_profiles.tex').write_text(PROFILE_TABLE+'\n')
for stage in (8,9):
    profile=obj(f'configs/stage{stage}/R32.json')
    assert profile['tokens']['max_tokens']==1984
    assert profile['public_size_class']['envelope_bytes']==100
    assert len(profile['cover_contexts'])==(4 if stage==8 else 6)

data = {s: rows(s) for s in (6, 7, 8, 9)}
for s, rr in data.items():
    for r in rr:
        if r.get('wire_delivered') and (ROOT/r['evidence_dir']/'carrier.txt').exists():
            raw = read(r['evidence_dir']+'/carrier.txt')
            assert hashlib.sha256(raw).hexdigest() == r['transport_sha256']
        if r.get('exact_recovery') and r.get('payload_sha256'):
            assert r['payload_sha256'] == r['recovered_sha256']
        if r.get('serialized_base64'):
            assert hashlib.sha256(base64.b64decode(r['serialized_base64'], validate=True)).hexdigest() == r['envelope_sha256']
        o = r.get('observer', {})
        if o.get('scorable'):
            t = trace(r)['public_scoring']
            assert len(t['nll_bits']) == o['token_count']
            assert math.isclose(mean(t['nll_bits']), o['mean_nll_bits'], abs_tol=1e-10)
            if s == 9:
                p = decompose_public_symbols(t['symbols'], t['frequency_tables'], 100)
                for k in ['stable_target_reached','first_completion_token','ends_at_first_completion',
                          'filler_consistent','canonical_replay_consistent','kem_canonical','format_accepted']:
                    assert p[k] == o[k], (r['case_id'], k)

main = {s: [r for r in data[s] if r['kind']=='encrypted' and
            r.get(f'stage{s}_phase') in ('main_fixed','baseline','prospective')] for s in (6,8,9)}
recovery = []
for s in (6,8,9):
    for method in ('Calgacus','L','F','R'):
        for n in (32,128):
            rr = [r for r in main[s] if r['method']==method and size(r)==n]
            if not rr: continue
            good = [r for r in rr if r['exact_recovery']]
            by_id = {r['attempt_id']:r for r in rr}
            replays = [r for r in data[s] if r['kind']=='replay' and r.get('source_attempt_id') in by_id]
            recovery.append(dict(stage=s, method=method, payload_bytes=n, attempted=len(rr), recovered=len(good),
                independent_replays=len(replays), exact_replays=sum(r['exact_recovery'] for r in replays),
                delivered_token_min=min((r['carrier_tokens'] for r in good), default=None),
                delivered_token_max=max((r['carrier_tokens'] for r in good), default=None),
                success_bits_per_token=mean([8*n/r['carrier_tokens'] for r in good]),
                attempt_mean_bits_per_token=sum(8*n/r['carrier_tokens'] for r in good)/len(rr),
                bytes_per_inclusive_second=n*len(good)/sum(r['job_elapsed_seconds'] for r in rr),
                mean_job_seconds=mean([r['job_elapsed_seconds'] for r in rr]),
                encode_seconds=mean([r['timings']['encode_seconds'] for r in rr]),
                receive_seconds=mean([r['timings']['receiver_seconds'] for r in rr if 'receiver_seconds' in r['timings']]),
                score_seconds=mean([r['timings']['public_scoring_seconds'] for r in rr if 'public_scoring_seconds' in r['timings']]),
                evaluated_tokens=sum(r['charged_tokens'] for r in rr),
                failures=dict(Counter(r['failure_category'] for r in rr if not r['exact_recovery'])),
                attempt_ids=[r['attempt_id'] for r in rr], gpu_revisions=sorted(set(r['tested_code_commit'] for r in rr))))
dump('generated/recovery.json', recovery)
write_csv('generated/recovery.csv', [{k:v for k,v in r.items() if k not in ('failures','attempt_ids','gpu_revisions')} for r in recovery])

# Table 2: successful length range does not hide failed attempts; rate assigns zero to failure.
table = [r'\begin{table*}[t]', r'\caption{Recovery and cost by separate study cohort and payload size. Recovery includes every encrypted attempt. Replay counts are exact/attempted independent receiver jobs, not additional transmissions. Tokens describe successful carriers only. $U_s$ averages useful payload bits per token among successes; $U_a$ assigns zero to failed attempts. Seconds average complete encrypted jobs, including startup, reception and public scoring when reached. Calgacus denotes the audited adaptation. No failed arithmetic partial output is counted as transmitted text.}', r'\label{tab:recovery}', r'\centering\small', r'\begin{tabular}{llrrrrrrrr}',r'\hline',r'Study & Method & Bytes & Recovery & Replays & Tokens & $U_s$ & $U_a$ & Seconds & Bytes/s\\',r'\hline']
for r in recovery:
    tok = '--' if r['delivered_token_min'] is None else str(r['delivered_token_min']) if r['delivered_token_min']==r['delivered_token_max'] else f"{r['delivered_token_min']}--{r['delivered_token_max']}"
    us = '--' if r['success_bits_per_token'] is None else f"{r['success_bits_per_token']:.3f}"
    rep = '--' if not r['independent_replays'] else f"{r['exact_replays']}/{r['independent_replays']}"
    table.append(f"S{r['stage']} & {r['method']} & {r['payload_bytes']} & {r['recovered']}/{r['attempted']} & {rep} & {tok} & {us} & {r['attempt_mean_bits_per_token']:.3f} & {r['mean_job_seconds']:.1f} & {r['bytes_per_inclusive_second']:.3f} \\")
    table[-1] += '\\'  # TeX row terminator, two literal backslashes
table += [r'\hline',r'\end{tabular}',r'\end{table*}']
(PAPER/'generated/table_recovery.tex').write_text('\n'.join(table)+'\n')

prospective = [r for r in data[9] if r['stage9_phase']=='prospective']
groups = {g:[r for r in prospective if ('R' if r['kind']=='encrypted' else r['family'])==g] for g in ('R','B-fixed','B-stop')}
predicate_keys=['valid_utf8','canonical_bytes','all_candidates_member','stable_target_reached','ends_at_first_completion','filler_consistent','canonical_replay_consistent','kem_canonical','format_accepted']
pred = {}
for g,rr in groups.items():
    oo=[r['observer'] for r in rr if r.get('observer',{}).get('scorable')]
    pred[g]={'attempted':len(rr),'delivered':sum(r.get('wire_delivered',False) for r in rr),'scorable':len(oo),'capacity_aborts':sum(r.get('failure_category')=='capacity_exhaustion' for r in rr),
             'checks':{k:{'pass':sum(o.get(k) is True for o in oo),'fail':sum(o.get(k) is False for o in oo),'na':sum(o.get(k) is None for o in oo)} for k in predicate_keys}}
assert [sum(r['exact_recovery'] for r in groups['R']),pred['B-fixed']['delivered'],pred['B-stop']['delivered']]==[4,6,3]
assert pred['B-stop']['checks']['canonical_replay_consistent']=={'pass':0,'fail':3,'na':0}
dump('generated/predicates.json',pred)
table=[r'\begin{table}[t]',r'\caption{Prospective stopping study (S9). Each check cell is pass/fail/unavailable among scorable delivered texts. Aborted attempts are listed separately and receive no wire verdict. Full format includes completion, exact end, filler and replay, but never authentication.}',r'\label{tab:predicates}',r'\centering\small',r'\begin{lrcases}' ]
# Normal tabular keeps the conference table font at 9 pt.
table[-1]=r'\begin{tabular}{lrrr}'
table += [r'\hline',r'Outcome & R & B-fixed & B-stop\\',r'\hline']
for key,label in [('attempted','Attempts'),('delivered','Delivered'),('scorable','Scorable'),('capacity_aborts','Capacity aborts')]:
    table.append(label+' & '+' & '.join(str(pred[g][key]) for g in groups)+r'\\')
table.append(r'\hline')
labels=['Valid UTF-8','Canonical bytes','Support membership','Packet target','Exact first end','Local filler','Canonical replay','KEM representation','Full format']
for k,label in zip(predicate_keys,labels):
    table.append(label+' & '+' & '.join('/'.join(str(pred[g]['checks'][k][x]) for x in ('pass','fail','na')) for g in groups)+r'\\')
table += [r'\hline',r'\end{tabular}',r'\end{table}']
(PAPER/'generated/table_predicates.tex').write_text('\n'.join(table)+'\n')

# Public scores are recomputed from the saved observer pass, never from encoder diagnostics.
scores=[]
for s in (6,8,9):
    for r in data[s]:
        if r.get(f'stage{s}_phase') not in ('main_fixed','prospective'):continue
        o=r.get('observer',{})
        if not o.get('scorable'):continue
        scores.append(dict(stage=s,case_id=r['case_id'],attempt_id=r['attempt_id'],kind=r['kind'],method=r['method'],family=r.get('family'),context=r['context_index'],pair=r.get('pair_id'),payload=size(r),nll=o['mean_nll_bits'],body_nll=o.get('encrypted_body_nll_bits'),token_count=o['token_count'],byte_count=o['utf8_bytes'],format=o['format_accepted'],kem=o.get('kem_canonical')))
write_csv('generated/scores.csv',scores)
comparisons=[]
for s,m,fam,metric in [(6,'F',f,'body_nll') for f in ('A','B','C')]+[(6,'F',f,'nll') for f in ('A','B','C')]+[(8,'R','B','nll'),(9,'R','B-fixed','nll')]:
    pos=[r for r in scores if r['stage']==s and r['kind']=='encrypted' and r['method']==m]
    neg=[r for r in scores if r['stage']==s and r['family']==fam and r['method']==m and r['pair'] in {p['pair'] for p in pos}]
    assert len(pos)==len(neg)
    comparisons.append(dict(stage=s,method=m,family=fam,score=metric,pairs=len(pos),auc=auc([r[metric] for r in pos],[r[metric] for r in neg]),orientation='higher is carrier',positive_ids=[r['attempt_id'] for r in pos],negative_ids=[r['attempt_id'] for r in neg]))
assert comparisons[-2]['auc']==.5 and comparisons[-1]['auc']==1
dump('generated/auc.json',comparisons)

# Selected teaching cases: first predetermined replay source, and sole stopped
# control whose local filler passes while full canonical replay fails.
examples=[]
for case,end,rationale in [('R-c0','Texas.','Earliest predeclared replay source, not selected for fluency.'),('B-stop-c3','passed on.','Only completed stopped control with a passing local filler but failing replay; exposes the distinction.')]:
    r=next(r for r in data[9] if r['case_id']==case)
    raw=read(r['evidence_dir']+'/carrier.txt');txt=raw.decode('utf-8');excerpt=txt[:txt.index(end)+len(end)]
    fn='example_success.txt' if case=='R-c0' else 'example_control.txt'
    (PAPER/'generated'/fn).write_bytes(excerpt.encode('utf-8'))
    examples.append(dict(case=case,attempt_id=r['attempt_id'],carrier_path=r['evidence_dir']+'/carrier.txt',source_sha256=r['transport_sha256'],excerpt_utf8=excerpt,excerpt_byte_start=0,excerpt_byte_end=len(excerpt.encode()),rationale=rationale,full_tokens=r['carrier_tokens'],full_bytes=r['transport_bytes'],gpu_revision=r['tested_code_commit'],observer=r['observer']))
dump('generated/examples.json',examples)

# All paired controls are dependent observations. Verify their common prefix.
pairs=[]
for c in range(6):
    a=next(r for r in groups['B-fixed'] if r['context_index']==c);b=next(r for r in groups['B-stop'] if r['context_index']==c)
    ta=trace(a)['control_generation'];tb=trace(b)['control_generation'];n=min(len(ta['advanced_ids']),len(tb['advanced_ids']))
    for k in ('advanced_ids','candidate_steps','arithmetic_steps'): assert ta[k][:n]==tb[k][:n]
    pairs.append(dict(context=c,common=n,fixed_tokens=len(ta['advanced_ids']),stop_tokens=len(tb['advanced_ids']),stop_delivered=b['wire_delivered']))
dump('generated/paired_controls.json',pairs)

# Figures use vector PDF with embedded fonts and no personal PDF metadata.
plt.rcParams.update({'font.family':'serif','font.serif':['Liberation Serif'],'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
COL=['#0072B2','#D55E00','#009E73','#CC79A7','#555555','#E69F00']
FIG_LABELS={}
def save(fig,name):
    fig.canvas.draw()
    FIG_LABELS[name]=[x.get_text() for x in fig.findobj(matplotlib.text.Text) if x.get_visible() and x.get_text()]
    fig.savefig(PAPER/'figures'/f'{name}.pdf',metadata={'Creator':'Scientific plotting script','Author':'','CreationDate':None,'ModDate':None})
    fig.savefig(PAPER/'figures'/f'{name}.svg',metadata={'Creator':'Scientific plotting script','Date':None})
    plt.close(fig)

fig,ax=plt.subplots(figsize=(6.22,2.30));ax.set_xlim(0,10);ax.set_ylim(0,4);ax.axis('off')
def box(x,y,w,h,text,color):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.04,rounding_size=0.07',facecolor=color,edgecolor='#444444',lw=.8));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=9)
def arrow(a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':1.0,'color':'#444444'})
box(.10,2.5,1.65,.78,'Binary payload\n+ inner record','#eeeeee');box(2.10,2.5,1.75,.78,'HPKE encryption\nrecipient public key','#DCEAF3');box(4.23,2.5,1.70,.78,'Public LLM codec\nencrypted envelope','#DCEAF3');box(6.33,2.5,1.5,.78,'Actual UTF-8\nmessage boundary','#ffffff')
arrow((1.8,2.9),(2.05,2.9));arrow((3.9,2.9),(4.18,2.9));arrow((5.98,2.9),(6.28,2.9))
box(8.25,2.35,1.6,1.05,'Retokenize\npublic extraction\n(no encoder state)','#DCEAF3');arrow((7.88,2.9),(8.20,2.9))
box(5.0,.20,2.50,1.2,'PUBLIC OBSERVER\nscores, stopping, filler,\ncanonical replay, KEM\nNo authentication','#FFF0DA')
box(7.95,.20,1.90,1.2,'PRIVATE RECEIVER\nHPKE open with sk\nlength check\npayload or rejection','#DCEFE6')
arrow((8.70,2.3),(6.2,1.45));arrow((9.2,2.3),(8.9,1.45));ax.text(.1,1.55,'Public at all endpoints: model, tokenizer, context,\nprofile, size class when used, and recipient public key.',fontsize=9,va='center');ax.text(.1,.50,'Only the receiver has the private key.\nPublic format acceptance is not authenticated recovery.',fontsize=9,va='center');fig.subplots_adjust(left=.01,right=.995,top=.99,bottom=.01);save(fig,'figure1_protocol')

fig,axs=plt.subplots(1,3,figsize=(6.22,2.75))
d=next(r for r in data[8] if r['case_id']=='diagnostic-qual-HPKE-32');curve=[x['stable_bits'] for x in trace(d)['encode']['arithmetic_steps']]
axs[0].plot(range(1,1537),curve[:1536],color='#555555',lw=1.2,label='Original prefix')
axs[0].plot(range(1536,len(curve)+1),curve[1535:],color=COL[0],lw=1.3,label='Ceiling extension')
axs[0].scatter([1942],[800],marker='o',color=COL[0],s=20);axs[0].axhline(800,color='black',ls=':',lw=.8);axs[0].set_title('(a) Historical packet\n32-byte payload');axs[0].set_ylim(0,900);axs[0].legend(loc='lower right',fontsize=8)
for ax,n,title in zip(axs[1:],[32,128],['(b) Fresh S8, 32 bytes','(c) Fresh S8, 128 bytes']):
    rr=[r for r in main[8] if r['method']=='R' and size(r)==n]
    for r in rr:
        cur=[x['stable_bits'] for x in trace(r)['encode']['arithmetic_steps']];c=r['context_index'];ax.plot(range(1,len(cur)+1),cur,color=COL[c],ls=['-','--','-.',':'][c],lw=1,label=f'c{c}');ax.scatter([len(cur)],[cur[-1]],marker='o' if r['exact_recovery'] else 'x',s=20,color=COL[c])
    ax.axhline(8*(n+68),color='black',ls=':',lw=.8);ax.set_ylim(0,900 if n==32 else 1750);ax.set_title(title);ax.legend(loc='lower right',fontsize=8,ncol=2,columnspacing=.5,handlelength=1.4)
for ax in axs:
    ax.set_xlim(0,2050);ax.set_xticks([0,1024,1984]);ax.set_xlabel('Emitted tokens');ax.grid(alpha=.15)
axs[0].set_ylabel('Stable decoded bits');fig.tight_layout(pad=.5,w_pad=.7);save(fig,'figure2_capacity')

fig,axs=plt.subplots(1,2,figsize=(6.22,2.85),gridspec_kw={'width_ratios':[1.15,1]})
for p in pairs:
    c=p['context'];axs[0].plot([p['fixed_tokens'],p['stop_tokens']],[c,c],color='#999999',lw=1)
    axs[0].scatter([p['fixed_tokens']],[c-.1],color=COL[0],marker='s',s=28)
    axs[0].scatter([p['stop_tokens']],[c+.1],color=COL[1],marker='o' if p['stop_delivered'] else 'x',s=32)
axs[0].set_yticks(range(6),[f'c{c}' for c in range(6)]);axs[0].invert_yaxis();axs[0].set_xlim(550,2050);axs[0].set_xticks([752,1186,1984]);axs[0].set_xlabel('Tokens on the same sampled trajectory');axs[0].set_title('(a) Fixed and first-complete boundaries');axs[0].grid(axis='x',alpha=.2)
axs[0].scatter([],[],color=COL[0],marker='s',label='Fixed, incomplete');axs[0].scatter([],[],color=COL[1],marker='o',label='Stopped, delivered');axs[0].scatter([],[],color=COL[1],marker='x',label='Stopped, abort');axs[0].legend(loc='upper center',bbox_to_anchor=(.5,-.22),ncol=1,frameon=False,fontsize=8)
ax=axs[1];ax.set_xlim(-.5,2.5);ax.set_ylim(5.5,-.5);ax.set_xticks([0,1,2],['First end','Local filler','Replay']);ax.set_yticks(range(6),[f'c{c}' for c in range(6)]);ax.set_title('(b) B-stop public predicates');ax.tick_params(length=0)
for r in groups['B-stop']:
    c=r['context_index']
    for j,k in enumerate(['ends_at_first_completion','filler_consistent','canonical_replay_consistent']):
        v=r.get('observer',{}).get(k);label='Abort' if not r['wire_delivered'] else 'Pass' if v else 'Fail';color='#eeeeee' if label=='Abort' else '#DCEFE6' if v else '#F9E2D8';ax.add_patch(plt.Rectangle((j-.44,c-.4),.88,.8,facecolor=color,edgecolor='#aaaaaa',lw=.4));ax.text(j,c,label,ha='center',va='center',fontsize=9)
for sp in ax.spines.values():sp.set_visible(False)
fig.subplots_adjust(left=.06,right=.995,top=.88,bottom=.34,wspace=.34);save(fig,'figure3_stopping')

fig,axs=plt.subplots(2,2,figsize=(6.22,4.3))
ax=axs[0,0]; cats=[('encrypted',None,'F'),('control','A','A'),('control','B','B-fixed'),('control','C','C-uniform')]
for j,(kind,fam,label) in enumerate(cats):
    rr=[r for r in scores if r['stage']==6 and r['method']=='F' and r['kind']==kind and r['family']==fam]
    ax.scatter([j+(i-(len(rr)-1)/2)*.025 for i in range(len(rr))],[r['nll'] for r in rr],s=16,marker=['o','^','s','D'][j],color=COL[j],alpha=.85)
ax.set_xticks(range(4),[x[2] for x in cats]);ax.set_title('(a) S6, F and three generators\n16 delivered texts per group');ax.set_ylabel('Canonical-token surprisal (bits/token)');ax.grid(axis='y',alpha=.15)
for ax,s,fam,title in [(axs[0,1],8,'B','(b) S8, R / B-fixed: 2 pairs\nHigher-is-R AUC = 0.5'),(axs[1,0],9,'B-fixed','(c) S9, R / B-fixed: 4 pairs\nHigher-is-R AUC = 1.0'),(axs[1,1],9,'B-stop','(d) S9, R / B-stop: 3 pairs\nUnequal lengths; no AUC')]:
    pp=[r for r in scores if r['stage']==s and r['method']=='R' and r['kind']=='encrypted']
    for a in pp:
        b=next((r for r in scores if r['stage']==s and r['method']=='R' and r['family']==fam and r['pair']==a['pair']),None)
        if b is None:continue
        c=a['context'];off=(c-2.5)*.022;ax.plot([0+off,1+off],[a['nll'],b['nll']],color=COL[c],lw=.8,alpha=.8);ax.scatter([0+off,1+off],[a['nll'],b['nll']],color=COL[c],marker=['o','s','^','D','v','P'][c],s=25,label=f'c{c}')
    ax.set_xlim(-.3,1.3);ax.set_xticks([0,1],['R','B-fixed' if fam=='B' else fam]);ax.set_ylim(.2,1.6);ax.set_title(title);ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8,ncol=2,frameon=False,loc='upper right',handlelength=1,columnspacing=.7)
axs[1,0].set_ylabel('Canonical-token surprisal (bits/token)');fig.tight_layout(pad=.6,h_pad=1.3,w_pad=1.1);save(fig,'figure4_scores')
dump('generated/figure_labels.json',FIG_LABELS)

# Preserve already computed dependent-sample uncertainty, with exact provenance.
for s in (6,8,9):
    obj(f'artifacts/stage{s}/summary.json')
    obj(f'artifacts/stage{s}/recognition.json')
obj('artifacts/stage8/historical_diagnosis.json');obj('artifacts/stage9/historical_reanalysis.json')
verification={'source_evidence_revision':'87cc8c8394a1e1b370825cf565bb0e132da14954','model_inference_calls':0,'experimental_cases':0,'checks':['all retained carrier byte hashes','payload/recovered hash agreement','serialized envelope hashes','public surprisal means from token scoring tables','all Stage 9 delivered public predicates from public tables','six paired control common prefixes','raw AUC recomputation','all-attempt recovery and inclusive costs'], 'stage9_counts':pred,'auc':comparisons,'examples':examples,'inputs_sha256':INPUTS,'gpu_revisions':{str(s):sorted(set(r['tested_code_commit'] for r in data[s])) for s in data}}
dump('review/asset_verification.json',verification)
print('PASS: regenerated four vector figures, two data tables, two exact excerpts, raw metrics and evidence hashes. No inference.')
print('Recovery:',[(r['stage'],r['method'],r['payload_bytes'],r['recovered'],r['attempted']) for r in recovery])
print('AUC:',[(r['stage'],r['family'],r['score'],r['auc']) for r in comparisons])
