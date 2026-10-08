"""Frozen corpus loader; UUIDs mapped to stable document/page/chunk labels."""
import hashlib
import json
import shutil
import sqlite3
import time
from pathlib import Path

from backend.app.store import Store, extract
from .metrics import distribution, word_error_rate

DATA=Path(__file__).resolve().parent/'datasets/heldout'


def load_dataset():
    dataset=json.loads((DATA/'questions.json').read_text())
    manifest=json.loads((DATA/'manifest.json').read_text())
    actual=hashlib.sha256((DATA/'questions.json').read_bytes()).hexdigest()
    if actual!=manifest['dataset_sha256']:
        raise ValueError('Frozen dataset hash mismatch; regenerate manifest explicitly only for a NEW benchmark version.')
    for doc in dataset['documents']:
        if hashlib.sha256((DATA/'corpus'/doc['name']).read_bytes()).hexdigest()!=doc['sha256']:
            raise ValueError('Corpus hash mismatch: '+doc['name'])
    return dataset,manifest


def chunk_map(store):
    with store.connect() as db:
        rows=db.execute('SELECT c.id,d.name,c.page,c.text FROM chunks c JOIN documents d ON d.id=c.document_id ORDER BY c.rowid').fetchall()
    counts={}
    mapping={}
    for uuid,name,page,text in rows:
        counts[(name,page)]=counts.get((name,page),0)+1
        mapping[uuid]={'key':f'{name}:page{page}:chunk{counts[(name,page)]}','document':name,'page':page,'text':text}
    return mapping


def normalize(text):
    return ' '.join(text.lower().split())


def label_chunks(case,mapping):
    qrels={}
    missing=[]
    for index,label in enumerate(case['evidence']):
        found=[]
        for chunk in mapping.values():
            if chunk['document']==label['document'] and normalize(label['span']) in normalize(chunk['text']):
                found.append(chunk['key'])
                qrels.setdefault(chunk['key'],set()).add(index)
        if not found:
            missing.append(label)
    return {key:min(2,len(units)) for key,units in qrels.items()},missing


class Corpus:
    def __init__(self,directory,dataset,ingestion_repeats=3):
        self.directory=Path(directory)
        self.dataset=dataset
        self.store=Store(self.directory/'base.sqlite3')
        self.ids={}
        self.ingestion=[]
        self.extraction=[]
        self.errors=[]
        self.ocr=[]
        for doc in dataset['documents']:
            if doc['name'].startswith('attack-'):
                continue
            content=(DATA/'corpus'/doc['name']).read_bytes()
            for repeat in range(ingestion_repeats):
                target=self.store if repeat==0 else Store(self.directory/f'ingest-{doc["name"]}-{repeat}.sqlite3')
                start=time.perf_counter()
                try:
                    result=target.ingest(doc['name'],content)
                    self.ingestion.append(dict(document=doc['name'],modality=doc['modality'],repeat=repeat,latency_ms=(time.perf_counter()-start)*1000))
                    if repeat==0:self.ids[doc['name']]=result['id']
                except Exception as exc:
                    self.errors.append(dict(document=doc['name'],phase='ingestion',repeat=repeat,error=f'{type(exc).__name__}: {exc}'))
            for repeat in range(ingestion_repeats):
                start=time.perf_counter()
                try:
                    pages,_=extract(doc['name'],content)
                    self.extraction.append(dict(document=doc['name'],modality=doc['modality'],repeat=repeat,latency_ms=(time.perf_counter()-start)*1000))
                    if doc['modality']=='ocr' and repeat==0:
                        transcript=(DATA/(Path(doc['name']).stem+'-transcription.txt')).read_text()
                        text='\n'.join(text for _,text in pages)
                        self.ocr.append(dict(document=doc['name'],reference=transcript,extracted=text,**word_error_rate(transcript,text)))
                except Exception as exc:
                    self.errors.append(dict(document=doc['name'],phase='extraction',error=f'{type(exc).__name__}: {exc}'))
        self.mapping=chunk_map(self.store)
        self.scoped={}
        for case in dataset['cases']:
            if 'scoped_documents' not in case:
                continue
            target=Store(self.directory/(case['id']+'.sqlite3'))
            with self.store.connect() as source,target.connect() as destination:
                source.backup(destination)
            with target.connect() as db:
                placeholders=','.join('?' for _ in case['scoped_documents'])
                db.execute(f'DELETE FROM chunks WHERE document_id IN (SELECT id FROM documents WHERE name NOT IN ({placeholders}))',case['scoped_documents'])
                db.execute(f'DELETE FROM documents WHERE name NOT IN ({placeholders})',case['scoped_documents'])
            attack=DATA/'corpus'/case['attack_document']
            target.ingest(attack.name,attack.read_bytes())
            self.scoped[case['id']]=target
        self.scope_maps={key:chunk_map(store) for key,store in self.scoped.items()}

    def context(self,case):
        return self.scoped.get(case['id'],self.store),self.scope_maps.get(case['id'],self.mapping)

    def report(self):
        return dict(base_documents=self.store.documents(),base_document_count=len(self.ids),base_chunk_count=len(self.mapping),
                    base_corpus_bytes=sum(doc['bytes'] for doc in self.dataset['documents'] if not doc['name'].startswith('attack-')),
                    sqlite_bytes=self.store.path.stat().st_size,persisted_retrieval_index_bytes=0,
                    index_note='No persisted TF-IDF/BM25 index. SQLite stores chunks and parsed CSV. Vectorizer and BM25 bags are rebuilt per query; transient index RAM is part of process RSS, not separately attributable.',
                    adversarial_contexts={key:{'documents':len(store.documents()),'chunks':len(self.scope_maps[key])} for key,store in self.scoped.items()},
                    ingestion_raw=self.ingestion,extraction_raw=self.extraction,errors=self.errors,ocr=self.ocr,
                    ingestion_by_modality={m:distribution(r['latency_ms'] for r in self.ingestion if r['modality']==m) for m in ['text','pdf','csv','ocr']},
                    extraction_by_modality={m:distribution(r['latency_ms'] for r in self.extraction if r['modality']==m) for m in ['text','pdf','csv','ocr']})
