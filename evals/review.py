"""Readable offline human review with blank judgments and local CSV export."""
import argparse
import hashlib
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def generate(paths,output):
    rows=[]
    for path in paths:
        report=json.loads(path.read_text())
        phase=path.parent.name if path.name=='latest.json' else path.stem
        for mode,evaluation in report['answers'].items():
            for row in evaluation['raw']:
                rows.append({'phase':phase,'mode':mode,**row})
    cards=[]
    esc=html.escape
    fields=[('correctness','Correctness'),('groundedness','Groundedness'),('citation_support','Citation support'),('abstention_correct','Refusal/clarification appropriate')]
    for row in rows:
        key=f'{row["phase"]}:{row["mode"]}:{row["id"]}'
        source_html=''.join(f'<details><summary>[S{i}] {esc(s["name"])} — page/row {s["page"]}</summary><h4>Focused evidence</h4><pre>{esc(s.get("evidence_text",s["text"]))}</pre><h4>Full retrieved chunk</h4><pre>{esc(s["text"])}</pre></details>' for i,s in enumerate(row['sources'],1))
        controls=''.join(f'<label>{label}<select data-field="{name}"><option value=""></option><option>yes</option><option>no</option><option>uncertain</option><option>not applicable</option></select></label>' for name,label in fields)
        controls+='<label>Substantive claim count<input type="number" min="0" data-field="claim_count"></label><label>Unsupported claim count<input type="number" min="0" data-field="unsupported_claim_count"></label><label>Reviewer<input data-field="reviewer"></label><label>Notes<textarea data-field="notes"></textarea></label>'
        cards.append(f'<article data-key="{esc(key)}" data-phase="{esc(row["phase"])}" data-mode="{esc(row["mode"])}" data-category="{esc(row["category"])}"><h2>{esc(key)} · {esc(row["category"])}</h2><h3>{esc(row["question"])}</h3><p><b>Expected literal values:</b> {esc(json.dumps(row["expected_answers"]))}</p><p><b>Actual mode:</b> {esc(str(row["actual_mode"]))}</p><pre>{esc(row["answer"])}</pre>{source_html}<div class="judgments">{controls}</div></article>')
    data=json.dumps([{key:row.get(key) for key in ['phase','mode','id','category','question','expected_answers','answer','sources','actual_mode']} for row in rows]).replace('<','\\u003c')
    fingerprint=hashlib.sha256(data.encode()).hexdigest()[:16]
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence review</title>
<style>body{font:15px system-ui;margin:2rem auto;max-width:1050px;padding:0 1rem;color:#172d30;background:#f5f8f7}header{position:sticky;top:0;background:#f5f8f7;padding:1rem 0;border-bottom:1px solid #ccd}article{background:white;padding:1.4rem;border:1px solid #ccd;border-radius:8px;margin:1.3rem 0}pre{white-space:pre-wrap;word-break:break-word;font:14px system-ui;line-height:1.5;background:#f1f5f4;padding:1rem}details{margin:.8rem 0}.judgments{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem}label{display:flex;flex-direction:column;gap:.4rem}input,select,textarea,button{font:inherit;padding:.5rem}textarea{min-height:5rem}header select{max-width:170px}h2{font-size:16px}h3{font-size:19px}[hidden]{display:none}@media(max-width:600px){.judgments{grid-template-columns:1fr}}</style>
<header><h1>Independent evidence review</h1><p>No subjective judgments are prefilled. Read original/focused evidence; a matching answer string or valid ID does not prove correctness. Notes stay in this browser; export CSV to retain/share your judgments. File-origin storage may be unavailable—export before closing.</p><select id="phase"><option value="">All runs</option></select> <select id="mode"><option value="">All modes</option></select> <select id="category"><option value="">All categories</option></select> <button id="export">Export human review CSV</button><p id="count"></p></header>'''+''.join(cards)+'''<script>
const rows=ROW_DATA,storageKey='evidence-review-FINGERPRINT';let saved={};try{saved=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch{}
const cards=[...document.querySelectorAll('article')];for(const card of cards){for(const field of card.querySelectorAll('[data-field]')){field.value=(saved[card.dataset.key]||{})[field.dataset.field]||'';field.addEventListener('input',()=>{saved[card.dataset.key]??={};saved[card.dataset.key][field.dataset.field]=field.value;try{localStorage.setItem(storageKey,JSON.stringify(saved))}catch{}})}}
for(const dimension of ['phase','mode','category']){const select=document.getElementById(dimension);for(const value of [...new Set(rows.map(r=>r[dimension]))].sort()){const option=document.createElement('option');option.value=value;option.textContent=value;select.append(option)}select.addEventListener('change',filter)}
function filter(){let visible=0;for(const card of cards){card.hidden=['phase','mode','category'].some(d=>document.getElementById(d).value&&document.getElementById(d).value!==card.dataset[d]);if(!card.hidden)visible++}document.getElementById('count').textContent=visible+' of '+cards.length+' response records'}filter();
document.getElementById('export').onclick=()=>{const fields=['phase','mode','id','category','question','expected_answers','answer','sources','actual_mode','correctness','groundedness','citation_support','abstention_correct','claim_count','unsupported_claim_count','reviewer','notes'];const quote=v=>'"'+String(typeof v==='object'?JSON.stringify(v):v??'').replaceAll('"','""')+'"';const lines=[fields.map(quote).join(',')];for(const row of rows){const entry={...row,...saved[row.phase+':'+row.mode+':'+row.id]};lines.push(fields.map(f=>quote(entry[f]??'')).join(','))}const url=URL.createObjectURL(new Blob([lines.join('\\r\\n')],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='independent-evidence-review.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
</script></html>'''.replace('ROW_DATA',data).replace('FINGERPRINT',fingerprint)
    output.write_text(page)
    print(f'Generated {output}: {len(rows)} records, all human judgments blank.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'evals/results/review.html')
    parser.add_argument('--input',type=Path,nargs='+',default=[ROOT/'evals/results/before-architecture/latest.json',ROOT/'evals/results/after-architecture/latest.json',ROOT/'evals/results/secondary-final.json'])
    args=parser.parse_args()
    generate(args.input,args.output)


if __name__=='__main__':main()
