"""Frozen chunk-boundary regression; same-document overlap vs real conflict."""
import hashlib
import json
import tempfile
from pathlib import Path

from backend.app.agent import ollama_models
from backend.app.store import Store
from .latency_eval import measured_run

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'evals/datasets/boundary'


def main():
    output=ROOT/'evals/results/boundary.json'
    if output.exists():raise SystemExit('Preserve boundary regression execution; refusing overwrite.')
    content=(DATA/'questions.json').read_bytes()
    digest=hashlib.sha256(content).hexdigest()
    assert digest==json.loads((DATA/'manifest.json').read_text())['sha256']
    cases=json.loads(content)['cases']
    report={'dataset_sha256':digest,'application_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'backend/app').glob('*.py')},'raw':[]}
    models=ollama_models()
    with tempfile.TemporaryDirectory(prefix='boundary-regression-') as directory:
        for case in cases:
            store=Store(Path(directory)/(case['id']+'.sqlite3'))
            documents=case.get('documents') or [{'name':case['document'],'text':case['text']}]
            for doc in documents:store.ingest(doc['name'],doc['text'].encode())
            retrieved=store.search(case['question'],k=10)
            partial=any(source['text'].endswith(case.get('expected','').split()[0]) for source in retrieved) if case.get('expected') else None
            if case['category']=='overlap_fragment':assert partial,'Authored case did not actually cross the production chunk boundary'
            for mode in ['extractive','ollama']:
                if mode=='ollama' and 'qwen2.5:1.5b' not in models:continue
                result,error,timings,_=measured_run(store,{'category':'direct','question':case['question']},mode,'qwen2.5:1.5b',{})
                success=not error and (case.get('expected','') in result.get('answer','') and result.get('mode')!='clarification' if case.get('expected') else result.get('mode')=='clarification')
                report['raw'].append({'id':case['id'],'category':case['category'],'mode':mode,'success':success,'partial_fragment_present':partial,'error':error,**timings,'result':result})
    report['summaries']={mode:{category:{'n':len(rows),'successes':sum(row['success'] for row in rows)} for category in sorted({r['category'] for r in report['raw']}) for rows in [[r for r in report['raw'] if r['mode']==mode and r['category']==category]]} for mode in sorted({r['mode'] for r in report['raw']})}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summaries'],indent=2))
    if any(row['error'] or not row['success'] for row in report['raw']):raise SystemExit('Boundary regression failures preserved.')


if __name__=='__main__':main()
