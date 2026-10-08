"""Exercise real Tesseract OCR and retrieval with a temporary database."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.agent import run
from backend.app.store import Store

if not shutil.which('tesseract'):
    raise SystemExit('Install Tesseract first: brew install tesseract')

with tempfile.TemporaryDirectory() as directory:
    store = Store(Path(directory) / 'ocr.sqlite3')
    sample = ROOT / 'data/practice-workshop.png'
    document = store.ingest(sample.name, sample.read_bytes())
    results = []
    for question, expected in [
        ('Who is the workshop coordinator?', 'Elena Brooks'),
        ('What is the workshop location?', 'Cedar Room'),
        ('What is the workshop registration fee?', '25 dollars'),
    ]:
        result = run(store, question, document_id=document['id'])
        assert expected in result['answer'], result['answer']
        assert result['citation_check']['valid']
        results.append({'question': question, 'expected': expected, **result})
        print(result['answer'])
    report = {'engine': 'Tesseract local OCR', 'limitations': 'One clean English text image; not a general OCR accuracy benchmark or visual understanding test.', 'results': results}
    (ROOT / 'evals/ocr-check.json').write_text(json.dumps(report, indent=2) + '\n')
