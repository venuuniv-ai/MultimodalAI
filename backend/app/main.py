from pathlib import Path
from typing import Literal, Optional
import shutil
import json

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import ollama_models, run
from .store import ROOT, Store

app = FastAPI(title='Local Research Desk', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['Content-Type'])
store = Store()


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    mode: Literal['extractive', 'ollama'] = 'extractive'
    model: str = 'qwen2.5:1.5b'
    document_id: Optional[str] = None
    operation: Optional[Literal['count', 'summary']] = None
    column: Optional[str] = None


@app.get('/api/health')
def health():
    return {'status': 'ok', 'documents': len(store.documents()), 'ocr_available': bool(shutil.which('tesseract')), 'models': ollama_models()}


@app.get('/api/documents')
def documents():
    return store.documents()


@app.post('/api/documents')
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, 'Maximum upload size is 10 MB.')
        return store.ingest(file.filename or 'document.txt', content)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(400, str(error))
    finally:
        await file.close()


@app.post('/api/demo')
def demo():
    names = {d['name'] for d in store.documents()}
    loaded = []
    for path in sorted((ROOT / 'data/samples').iterdir()):
        if path.is_file() and path.name not in names:
            loaded.append(store.ingest(path.name, path.read_bytes()))
    return {'loaded': loaded}


@app.delete('/api/documents/{doc_id}')
def delete(doc_id: str):
    if not store.delete(doc_id):
        raise HTTPException(404, 'Document not found.')
    return {'deleted': True}


@app.post('/api/ask')
def ask(request: Question):
    if not request.question.strip():
        raise HTTPException(400, 'Enter a question.')
    try:
        return run(store, **request.model_dump())
    except ValueError as error:
        raise HTTPException(400, str(error))


@app.get('/api/documents/{doc_id}/columns')
def columns(doc_id: str):
    try:
        return store.csv_columns(doc_id)
    except ValueError as error:
        raise HTTPException(400, str(error))


@app.get('/api/evaluations')
def evaluations():
    keys = {'mode', 'model', 'dataset', 'limitations', 'questions', 'answerable_text_questions',
            'unanswerable_questions', 'ambiguous_questions_for_manual_review', 'tool_questions',
            'retrieval_evidence_hit_rate_at_10', 'expected_span_answer_rate', 'unanswerable_abstention_rate',
            'citation_valid_rate_on_answered_factual_questions', 'tool_value_pass_rate', 'errors',
            'latency_p50_ms', 'latency_p95_ms', 'categories'}
    reports = []
    for name in ('baseline-extractive', 'expanded-extractive', 'baseline-ollama', 'expanded-ollama'):
        path = ROOT / 'evals' / (name + '.json')
        if path.exists():
            try:
                report = json.loads(path.read_text())
                reports.append({'id': name, **{key: value for key, value in report.items() if key in keys}})
            except (ValueError, OSError):
                continue
    return reports


DIST = ROOT / 'frontend/dist'
if DIST.exists():
    app.mount('/', StaticFiles(directory=DIST, html=True), name='frontend')
