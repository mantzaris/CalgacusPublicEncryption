"""Paper-only checks: rendered content, provenance, anonymity and character budget."""
import hashlib,json,re,subprocess,unicodedata
from pathlib import Path
P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def count(s):return sum(not c.isspace() for c in unicodedata.normalize('NFKC',s))
def text(p):return subprocess.check_output(['pdftotext','-enc','UTF-8',str(p),'-'],text=True)
baseline=json.loads((P/'review/baseline_hashes.json').read_text())
changed=[f for f,h in baseline.items() if not (ROOT/f).exists() or sha(ROOT/f)!=h]
assert not changed,changed
policy=json.loads((P/'review/template_and_policy.json').read_text())
assert all(sha(P/f)==h for f,h in policy['required_files'].items())
pdf=P/'build/main.pdf';s=text(pdf);layout=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
fonts=subprocess.check_output(['pdffonts',str(pdf)],text=True)
for label in ['Author','Creator','Producer','Subject','Keywords']:
 assert re.search(r'^'+label+r':\s*$',info,re.M),label
for identifying in ['mantzaris','CalgacusPublicEncryption','/home/meow','STAGE9_TEST_ONLY','github.com/mantzaris']:
 assert identifying.lower() not in s.lower(),identifying
log=(P/'build/main.log').read_text()
assert not re.search(r'Overfull|undefined references|Citation .* undefined|LaTeX Error',log)
assert '??' not in s
labels=json.loads((P/'generated/figure_labels.json').read_text())
figure_counts={};missing={}
for name,strings in labels.items():
 fs=text(P/'figures'/f'{name}.pdf');compact=lambda t: ''.join(unicodedata.normalize('NFKC',t).split())
 figure_counts[name]={'label_inventory_nonspace_characters':sum(count(t) for t in strings),'pdf_extracted_nonspace_characters':count(fs)}
 # Count any whole label not found contiguously as missing, conservatively.
 missing[name]=[v for v in strings if compact(v) not in compact(s)]
missing_charge=sum(count(v) for vv in missing.values() for v in vv)
visible=count(s);full_figure_charge=sum(v['label_inventory_nonspace_characters'] for v in figure_counts.values())
# Conservative screening ceiling double counts ALL figure labels, plus 2% for
# extraction/ligature/linebreak uncertainty. It is not an official venue counter.
upper=visible+full_figure_charge+int(.02*visible+1)
assert 10000 <= visible and upper < 50000,(visible,upper)
main=(P/'main.tex').read_text();abstract=re.search(r'\\abstract\{(.*?)\}\n',main,re.S).group(1)
abstract_words=len(abstract.split());assert 70<=abstract_words<=200
assert '\u2014' not in main and '\u2013' not in main
pages=int(re.search(r'^Pages:\s*(\d+)',info,re.M).group(1));assert 10<=pages<=12
fig_count=len(re.findall(r'\\begin\{figure\*?\}',main));assert fig_count==4
# Included descriptive and numerical tables use the same official font/captions.
table_count=sum(len(re.findall(r'\\begin\{table\*?\}',f.read_text())) for f in [P/'main.tex',P/'generated/table_profiles.tex',P/'generated/table_recovery.tex',P/'generated/table_predicates.tex'])
assert table_count==3
out={'schema_version':1,'pages':pages,'abstract_words':abstract_words,'pdf_nonwhitespace_nfkc_characters':visible,'layout_extraction_nonwhitespace_nfkc_characters':count(layout),'figure_labels':figure_counts,'possibly_missing_labels':missing,'additional_possible_missing_label_characters':missing_charge,'visible_estimate_with_missing_labels':visible+missing_charge,'conservative_screening_upper_bound':upper,'conservative_headroom_below_50000':50000-upper,'method':'NFKC-normalized non-whitespace Unicode characters from pdftotext of complete PDF. Includes title, abstract, prose, tables, captions, citations, references and extracted vector labels. Unmatched label strings are charged separately. Upper screening bound additionally charges every figure label again, then 2% of extracted content for possible extraction discrepancies. No LaTeX commands counted. Not the official submission-system count.','figure_count':fig_count,'table_count':table_count,'examples':2,'historical_files_unchanged':len(baseline),'ledger_unchanged':True,'ledger_sha256':sha(ROOT/'artifacts/project_budget.jsonl'),'checkpoint_sha256':sha(ROOT/'artifacts/project_budget.checkpoint.json'),'pdf_sha256':sha(pdf),'template_files_unchanged':True,'anonymity_checks':'No author/affiliation/personal-repository/test-key strings in rendered text; author, creator, producer, keywords and subject metadata blank.','build_checks':'No undefined citations/references, overfull boxes or LaTeX errors.','inference_jobs':0,'experimental_cases':0}
(P/'review/draft_checks.json').write_text(json.dumps(out,indent=2)+'\n');(P/'review/pdfinfo.txt').write_text(info);(P/'review/fonts.txt').write_text(fonts)
print(json.dumps({k:out[k] for k in ['pages','abstract_words','pdf_nonwhitespace_nfkc_characters','additional_possible_missing_label_characters','conservative_screening_upper_bound','figure_count','table_count','historical_files_unchanged','ledger_unchanged']},indent=2))
