"""Independent half-open interval reconstruction from retained tables only.

Does not import the production arithmetic coder, tokenizer or model.
"""
import base64,csv,hashlib,json,math,subprocess
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/stage8'

def reference(symbols,tables):
    # Independent half-open integer convention and bitwise rescaling.
    a,b=0,2**32;deferred=0;output=[];steps=[];total_information=0
    for pos,(symbol,f) in enumerate(zip(symbols,tables),1):
        assert len(f)==16 and all(type(x)==int and x>0 for x in f) and sum(f)==65536
        span=b-a;lower=sum(f[:symbol]);upper=lower+f[symbol]
        left=a+int(Fraction(span*lower,65536));right=a+int(Fraction(span*upper,65536))
        assert a<=left<right<=b
        actual_information=-math.log2((right-left)/span)
        total_information+=actual_information;before=len(output)
        a,b=left,right
        while True:
            # A common most significant bit permits commitment of deferred bits.
            x=a>>31;y=(b-1)>>31
            if x==y:
                output += [x]+[1-x]*deferred;deferred=0
                a=(a & (2**31-1))*2;b=(((b-1)&(2**31-1))*2)+2
            elif a>=2**30 and b<=3*2**30:
                a=2*a-2**31;b=2*b-2**31;deferred+=1
            else:break
        # Exact conservation of accumulated interval information, independent
        # of when underflow debt is released as stable bits.
        residual=32-math.log2(b-a)
        assert math.isclose(total_information,len(output)+deferred+residual,abs_tol=1e-9)
        p=[x/65536 for x in f]
        steps.append({'position':pos,'stable_bits':len(output),'released_bits':len(output)-before,'pending_underflow':deferred,
          'low':a,'high_inclusive':b-1,'residual_width':b-a,'residual_information_bits':residual,
          'selected_frequency':f[symbol],'selected_information_bits':-math.log2(p[symbol]),
          'effective_interval_information_bits':actual_information,'table_entropy_bits':-sum(x*math.log2(x) for x in p)})
    return output,steps

def blocks(steps,size):
    out=[]
    for i in range(0,len(steps),size):
        ss=steps[i:i+size];previous=steps[i-1]['stable_bits'] if i else 0
        out.append({'first_token':i+1,'last_token':i+len(ss),'tokens':len(ss),'stable_bits_released':ss[-1]['stable_bits']-previous,
            'selected_information_bits':sum(x['selected_information_bits'] for x in ss),
            'mean_table_entropy_bits':sum(x['table_entropy_bits'] for x in ss)/len(ss),'pending_at_end':ss[-1]['pending_underflow']})
    return out

def main():
    old=[json.loads(l) for l in (ROOT/'artifacts/stage7/cases.jsonl').read_text().splitlines()];result=[]
    # Small hand-specified independent calculation, including cumulative boundaries.
    bits,st=reference([0,1,15],[[4096]*16]*3);assert bits==[0,0,0,0,0,0,0,1,1,1,1,1]
    f=[32768]+[2048]*14+[4096];assert sum(f)==65536
    bits,st=reference([0],[f]);assert bits==[0] and st[0]['residual_width']==2**32
    for r in old:
        d=ROOT/r['evidence_dir'];trace=json.loads((d/'traces.json').read_text())['encode'];job=json.loads((d/'input.json').read_text())
        data=bytes.fromhex(job['synthetic_envelope_hex']) if r['kind']=='fixture' else base64.b64decode(r['serialized_base64'],validate=True)
        tables=[x['frequencies'] for x in trace['arithmetic_steps']];symbols=trace['symbols']
        bits,steps=reference(symbols,tables)
        expected=[(v>>shift)&1 for v in data for shift in range(7,-1,-1)]+[1]+[0]*64
        assert bits==expected[:len(bits)]
        for observed,reconstructed in zip(trace['arithmetic_steps'],steps):
            assert all(observed[k]==reconstructed[k] for k in ['stable_bits','pending_underflow','low','high_inclusive'])
        runs=[];start=None
        for i,s in enumerate(steps):
            if s['released_bits']==0 and start is None:start=i
            if s['released_bits']!=0 and start is not None:runs.append((start,i));start=None
        if start is not None:runs.append((start,len(steps)))
        runs=sorted(runs,key=lambda x:x[1]-x[0],reverse=True)
        longest=[{'first_token':a+1,'last_token':b,'tokens':b-a,'selected_information_bits':sum(x['selected_information_bits'] for x in steps[a:b]),'pending_start':steps[a-1]['pending_underflow'] if a else 0,'pending_end':steps[b-1]['pending_underflow']} for a,b in runs[:5]]
        info=sum(x['selected_information_bits'] for x in steps);effective=sum(x['effective_interval_information_bits'] for x in steps)
        record={'case_id':r['case_id'],'attempt_id':r['attempt_id'],'historical_source_revision':r['tested_code_commit'],'context':r['cover_context'],
          'kind':r['kind'],'envelope_bytes':len(data),'required_bits':8*len(data),'tokens':len(steps),'terminal':steps[-1],
          'selected_information_sum':info,'effective_interval_information_sum':effective,'finite_rounding_information_difference':effective-info,
          'mean_table_entropy_bits':sum(x['table_entropy_bits'] for x in steps)/len(steps),'prefix_agreement':True,'all_interval_states_agree':True,
          'blocks128':blocks(steps,128),'blocks256':blocks(steps,256),'longest_zero_release_runs':longest,
          'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [d/'input.json',d/'traces.json',d/'outcome.json']}}
        result.append(record)
        with (ART/f"historical_progress_{r['case_id']}.csv").open('w',newline='') as out:
            w=csv.DictWriter(out,fieldnames=list(steps[0]));w.writeheader();w.writerows(steps)
    (ART/'historical_diagnosis.json').write_text(json.dumps({'schema_version':1,'method':'independent half-open interval calculation, rational boundary products, bitwise rescaling; production coder not imported','inference':False,'cases':result},indent=2)+'\n')
    print(json.dumps([{'case_id':r['case_id'],'bits':r['terminal']['stable_bits'],'pending':r['terminal']['pending_underflow'],'information':r['selected_information_sum'],'rounding_difference':r['finite_rounding_information_difference'],'zero_block256':[x for x in r['blocks256'] if x['stable_bits_released']==0],'longest_stall':r['longest_zero_release_runs'][0]} for r in result],indent=2))

if __name__=='__main__':main()
