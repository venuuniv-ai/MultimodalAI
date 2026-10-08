"""Transparent synthetic evaluation; span matching is not semantic grading."""
import argparse
import csv
import json
import math
import platform
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.agent import NO_EVIDENCE, ollama_models, run
from backend.app.store import Store


def rate(values):
    return sum(values) / len(values) if values else None


def summarize(rows):
    factual = [r for r in rows if r['answerable'] and r['category'] != 'tool']
    missing = [r for r in rows if r['category'] == 'unanswerable']
    tools = [r for r in rows if r['category'] == 'tool']
    answered = [r for r in factual if not r['abstained'] and not r['error']]
    timings = sorted(r['latency_ms'] for r in rows if not r['error'])
    return {
        'questions': len(rows), 'answerable_text_questions': len(factual),
        'unanswerable_questions': len(missing), 'tool_questions': len(tools),
        'ambiguous_questions_for_manual_review': sum(r['category'] == 'ambiguous' for r in rows),
        'retrieval_evidence_hit_rate_at_10': rate([r['rank'] is not None for r in factual]),
        'retrieval_mrr_at_10': rate([1 / r['rank'] if r['rank'] else 0 for r in factual]),
        'expected_span_answer_rate': rate([r['expected_span_present'] for r in factual]),
        'unanswerable_abstention_rate': rate([r['abstained'] and not r['error'] for r in missing]),
        'citation_valid_rate_on_answered_factual_questions': rate([r['citation_valid'] for r in answered]),
        'tool_value_pass_rate': rate([r['tool_values_match'] is True for r in tools]),
        'errors': sum(bool(r['error']) for r in rows),
        'latency_p50_ms': statistics.median(timings) if timings else None,
        'latency_p95_ms': timings[max(0, math.ceil(.95 * len(timings)) - 1)] if timings else None,
        'categories': {category: {'questions': len(group), 'expected_span_answer_rate': rate([r['expected_span_present'] for r in group if r['answerable'] and r['category'] != 'tool'])} for category in sorted({r['category'] for r in rows}) for group in [[r for r in rows if r['category'] == category]]},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['extractive', 'ollama'], default='extractive')
    parser.add_argument('--model', default='qwen2.5:1.5b')
    args = parser.parse_args()
    if not shutil.which('tesseract'):
        raise SystemExit('This evaluation includes an image; install Tesseract first.')
    if args.mode == 'ollama' and args.model not in ollama_models():
        raise SystemExit('Start the local Ollama server and install the selected model first.')
    cases = json.loads((ROOT / 'evals/expanded-questions.json').read_text())
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / 'expanded.sqlite3')
        files = [*sorted((ROOT / 'data/samples').iterdir()), ROOT / 'data/practice-project-notes.pdf', ROOT / 'data/practice-workshop.png', *sorted((ROOT / 'evals/fixtures').iterdir())]
        ids = {path.name: store.ingest(path.name, path.read_bytes())['id'] for path in files if path.is_file()}
        for case in cases:
            begin = time.perf_counter()
            rank = None
            if case['answerable'] and case['category'] != 'tool':
                sources = store.search(case['question'], k=10)
                ranks = [i + 1 for i, s in enumerate(sources) if s['name'] == case['relevant_document'] and case['expected_text'].lower() in s['text'].lower()]
                rank = min(ranks) if ranks else None
            error, result = None, {}
            try:
                kwargs = {'mode': args.mode, 'model': args.model}
                if case['category'] == 'tool':
                    kwargs.update(document_id=ids[case['relevant_document']], operation=case['operation'], column=case.get('column'))
                result = run(store, case['question'], **kwargs)
            except Exception as exc:
                error = str(exc)
            answer = result.get('answer', '')
            expected = case.get('expected_text')
            tool_match = None
            if case['category'] == 'tool' and not error:
                values = json.loads(answer)
                tool_match = all(values.get(key) == value for key, value in case['expected_values'].items())
            row = {**case, 'answer': answer, 'rank': rank, 'abstained': answer == NO_EVIDENCE,
                'expected_span_present': bool(expected and expected.lower() in answer.lower()),
                'citation_valid': bool((result.get('citation_check') or {}).get('valid')),
                'tool_values_match': tool_match, 'latency_ms': round((time.perf_counter() - begin) * 1000, 2),
                'error': error, 'actual_mode': result.get('mode'), 'sources': result.get('sources', [])}
            rows.append(row)
            print(f'{len(rows)}/{len(cases)} {case["id"]}: ' + ('ERROR' if error else 'abstained' if row['abstained'] else 'answered'), flush=True)
    report = {'mode': args.mode, 'model': args.model if args.mode == 'ollama' else None,
        'machine': platform.platform(), 'dataset': '62 authored synthetic questions across text, PDF, image OCR, and CSV fixtures',
        'limitations': 'Author-labeled development set, not independent or held-out. Expected-span matching does not establish semantic correctness or faithfulness. Sequential latency includes retrieval and full answer generation, not TTFT or concurrent load. Ambiguity and injection safety need manual review.',
        **summarize(rows), 'results': rows}
    prefix = ROOT / f'evals/expanded-{args.mode}'
    prefix.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    with prefix.with_suffix('.csv').open('w', newline='') as handle:
        fields = ['id', 'category', 'question', 'answer', 'expected_text', 'abstained', 'expected_span_present', 'error', 'human_supported', 'human_relevant', 'human_notes']
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({k:v for k,v in report.items() if k != 'results'}, indent=2))


if __name__ == '__main__':
    main()
