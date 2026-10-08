"""Exercise installed Ollama against the practice PDF using a temporary index."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.agent import ollama_models, run
from backend.app.store import Store

if 'qwen2.5:1.5b' not in ollama_models():
    raise SystemExit('Start scripts/start-ollama.sh and install qwen2.5:1.5b first.')

with tempfile.TemporaryDirectory() as directory:
    store = Store(Path(directory) / 'ai.sqlite3')
    document = ROOT / 'data/practice-project-notes.pdf'
    store.ingest(document.name, document.read_bytes())
    results = []
    for question in ['Who is the project manager?', 'What is the monthly cloud budget?', 'What is Maya\'s phone number?']:
        result = run(store, question, mode='ollama', model='qwen2.5:1.5b')
        results.append({'question': question, **result})
        print(json.dumps({'question': question, 'answer': result['answer'], 'mode': result['mode'], 'latency_ms': result['latency_ms'], 'warning': result['warning']}, indent=2), flush=True)
    (ROOT / 'evals/local-ai-check.json').write_text(json.dumps({'model': 'qwen2.5:1.5b', 'limitations': 'Three manually reviewed integration examples, not a quality benchmark.', 'results': results}, indent=2) + '\n')
