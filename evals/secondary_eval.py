"""One-shot evaluation of the predeclared secondary regression, same scoring."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from backend.app.agent import ollama_models
from backend.app.store import Store
from .benchmark import answer_evaluation, human_review
from .corpus import chunk_map
from .resources import environment

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'evals/datasets/secondary'


class SecondaryCorpus:
    def __init__(self,directory,dataset):
        self.ids={}
        self.stores={}
        self.maps={}
        for case in dataset['cases']:
            key=tuple(case['scoped_documents'])
            if key not in self.stores:
                store=Store(Path(directory)/f'{len(self.stores)}.sqlite3')
                for document in dataset['documents']:
                    if document['name'] in key:
                        self.ids[document['name']]=store.ingest(document['name'],document['text'].encode())['id']
                self.stores[key]=store
                self.maps[key]=chunk_map(store)
        self.store=self.stores[tuple(dataset['cases'][0]['scoped_documents'])]

    def context(self,case):
        key=tuple(case['scoped_documents'])
        return self.stores[key],self.maps[key]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'evals/results/secondary.json')
    parser.add_argument('--model',default='qwen2.5:1.5b')
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Refusing to overwrite the one-shot secondary run. Preserve results; do not tune against this set.')
    content=(DATA/'questions.json').read_bytes()
    expected=json.loads((DATA/'manifest.json').read_text())['sha256']
    assert hashlib.sha256(content).hexdigest()==expected,'Frozen secondary dataset mismatch'
    dataset=json.loads(content)
    report={'dataset_sha256':expected,'dataset_size':len(dataset['cases']),'provenance':dataset['provenance'],
            'environment':environment(),'answers':{},'application_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'backend/app').glob('*.py')}}
    with tempfile.TemporaryDirectory(prefix='research-secondary-') as directory:
        corpus=SecondaryCorpus(directory,dataset)
        for mode in ['extractive','ollama']:
            if mode=='ollama' and args.model not in ollama_models():
                report['unavailable_ollama']='Model unavailable; no values invented.'
                continue
            report['answers'][mode]=answer_evaluation(corpus,dataset['cases'],mode,args.model)
            for row in report['answers'][mode]['raw']:
                row['desired_behavior']=next(c.get('desired_behavior') for c in dataset['cases'] if c['id']==row['id'])
    report['run_id']=report['environment']['recorded_at'].replace(':','')
    args.output.parent.mkdir(exist_ok=True,parents=True)
    report['human_review_file']=human_review(report,args.output.parent/'secondary-human-review.csv')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Saved secondary one-shot results:',args.output)
    if any(e['summary']['errors'] for e in report['answers'].values()):raise SystemExit('Execution errors retained in secondary output.')


if __name__=='__main__':main()
