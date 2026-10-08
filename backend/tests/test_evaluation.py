import json
from pathlib import Path

from scripts.evaluate_expanded import summarize


def test_evaluation_errors_and_ambiguous_cases_have_honest_denominators():
    baseline = dict(answerable=True, category='direct', abstained=False, error=None, rank=1, expected_span_present=True, citation_valid=True, tool_values_match=None, latency_ms=10)
    rows = [baseline, {**baseline, 'error': 'Model failed', 'rank': None, 'expected_span_present': False},
            {**baseline, 'answerable': False, 'category': 'unanswerable', 'abstained': True},
            {**baseline, 'answerable': False, 'category': 'ambiguous'},
            {**baseline, 'category': 'tool', 'error': 'Invalid column', 'tool_values_match': None}]
    result = summarize(rows)
    assert result['expected_span_answer_rate'] == .5
    assert result['unanswerable_abstention_rate'] == 1
    assert result['tool_value_pass_rate'] == 0
    assert result['errors'] == 2
    assert result['ambiguous_questions_for_manual_review'] == 1
    assert result['citation_valid_rate_on_answered_factual_questions'] == 1


def test_expanded_dataset_ids_and_labels_are_complete():
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / 'evals/expanded-questions.json').read_text())
    assert len(cases) >= 50
    assert len({case['id'] for case in cases}) == len(cases)
    for case in cases:
        assert case['question'] and case['category']
        if case['answerable']:
            assert case['relevant_document']
            if case['category'] == 'tool':
                assert case['expected_values']
            else:
                assert case['expected_text']
