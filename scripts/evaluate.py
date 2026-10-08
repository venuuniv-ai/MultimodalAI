"""Small reproducible retrieval evaluation; not a production benchmark."""
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.store import Store
from backend.app.agent import run


def main():
    cases = json.loads((ROOT / 'evals/questions.json').read_text())
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / 'eval.sqlite3')
        for path in sorted((ROOT / 'data/samples').iterdir()):
            store.ingest(path.name, path.read_bytes())
        for case in cases:
            start = time.perf_counter()
            sources = store.search(case['question'], k=10)
            latency = (time.perf_counter() - start) * 1000
            # Labeled evidence span must occur in the returned chunk, not just its document.
            ranks = [i + 1 for i, source in enumerate(sources) if source['name'] == case['relevant_document'] and case['expected_text'].lower() in source['text'].lower()]
            answer = run(store, case['question'])
            rows.append({**case, 'rank': min(ranks) if ranks else None, 'retrieval_ms': round(latency, 2), 'citation_valid': answer['citation_check']['valid'], 'expected_span_in_answer': case['expected_text'].lower() in answer['answer'].lower()})
    timings = sorted(row['retrieval_ms'] for row in rows)
    report = {'dataset': '8 synthetic demo questions with labeled evidence spans', 'limitations': 'Small demo set; not held-out production data. Citation validity and expected-span presence do not measure semantic faithfulness.', 'machine': platform.platform(), 'questions': len(rows), 'evidence_hit_rate_at_10': sum(row['rank'] is not None for row in rows) / len(rows), 'mrr_at_10': statistics.mean(1 / row['rank'] if row['rank'] else 0 for row in rows), 'citation_valid_rate': statistics.mean(row['citation_valid'] for row in rows), 'expected_span_in_answer_rate': statistics.mean(row['expected_span_in_answer'] for row in rows), 'retrieval_p95_ms': timings[min(len(timings) - 1, int(.95 * len(timings)))], 'results': rows}
    target = ROOT / 'evals/report.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'results'}, indent=2))


if __name__ == '__main__':
    main()
