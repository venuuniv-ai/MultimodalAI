import json
import math
from pathlib import Path

import pytest

from backend.app.agent import run
from backend.app.store import Store
from evals.benchmark import grade_answer
from evals.corpus import chunk_map, label_chunks, load_dataset
from evals.latency_eval import measured_run
from evals.metrics import answer_summary, distribution, ranking_metrics, word_error_rate
from evals.reliability_eval import inspect_response, summarize
from evals.retrieval_eval import ablated_search


def test_rank_metrics_known_hand_calculation():
    metrics=ranking_metrics(['noise','a','b'],{'a':2,'b':1,'c':1})
    assert metrics['hit@1']==0 and metrics['hit@3']==1
    assert metrics['recall@1']==0
    assert metrics['recall@3']==pytest.approx(2/3)
    assert metrics['precision@5']==pytest.approx(2/5)
    assert metrics['precision@10']==pytest.approx(2/10)
    assert metrics['mrr@10']==.5
    expected=(3/math.log2(3)+1/math.log2(4))/(3+1/math.log2(3)+1/math.log2(4))
    assert metrics['ndcg@5']==pytest.approx(expected)
    assert ranking_metrics([],{'a':1})['recall@10']==0
    assert ranking_metrics(['a'],{}) is None
    with pytest.raises(ValueError):ranking_metrics(['a','a'],{'a':1})


def test_nearest_rank_percentiles_and_empty_samples():
    s=distribution(range(1,101))
    assert s['p50']==50.5 and s['p90']==90 and s['p95']==95 and s['p99']==99
    assert s['mean']==50.5 and s['n']==100 and s['min']==1 and s['max']==100
    assert distribution([])['p50'] is None


@pytest.mark.parametrize('question',['launch date','Who is the project manager?','quantum nonsense','the and','budget deployments','Ω unicode',''])
@pytest.mark.parametrize('k',[1,5,10])
def test_scorer_replica_matches_production_order_and_scores(tmp_path,question,k):
    store=Store(tmp_path/'test.sqlite3')
    for i in range(35):
        store.ingest(f'{i}.txt',f'Project {i} briefing. The launch date is March {i+1}. The project manager is Person {i%4}. Deployment budget is {i*13} dollars.'.encode())
    actual=store.search(question,k=k)
    replica=ablated_search(store,question,'production_replica',k=k)
    assert replica==actual
    doc=store.documents()[0]['id']
    assert ablated_search(store,question,'production_replica',k=k,document_id=doc)==store.search(question,k=k,document_id=doc)


def test_frozen_dataset_structure_and_development_separation():
    dataset,manifest=load_dataset()
    cases=dataset['cases']
    assert len(cases)>=150
    assert len({c['id'] for c in cases})==len(cases)
    assert sum(c['category']=='unanswerable' for c in cases)>=30
    assert sum(c['category']=='adversarial' for c in cases)==25
    old=json.loads((Path(__file__).resolve().parents[1]/'expanded-questions.json').read_text())
    assert not {c['question'] for c in old} & {c['question'] for c in cases if c['category'] not in ['ambiguous']}
    for case in cases:
        assert case['split']=='new_synthetic_heldout'
        if case['answerable'] and case['category']!='csv_tool':assert case['evidence'] and case['expected_answers']
    assert manifest['case_count']==len(cases)


def test_instrumented_answers_are_behaviorally_identical_and_labels_exhaustive(tmp_path):
    store=Store(tmp_path/'test.sqlite3')
    store.ingest('a.txt',b'The Juniper manager is Nina Wallace. The Juniper launch date is February 14, 2028.')
    store.ingest('b.txt',b'The Juniper manager is Nina Wallace.')
    case=dict(question='Who is the Juniper manager?',category='direct',modality='text',id='t1',answerable=True,
              expected_answers=['Nina Wallace'],evidence=[{'document':'a.txt','span':'Nina Wallace'},{'document':'b.txt','span':'Nina Wallace'}])
    actual=run(store,case['question'])
    measured,error,timings,retrieved=measured_run(store,case,'extractive','unused',{})
    assert error is None and timings['total_ms']>=timings['retrieval_ms']>0 and timings['generation_ms'] is None
    assert {k:v for k,v in measured.items() if k!='latency_ms'}=={k:v for k,v in actual.items() if k!='latency_ms'}
    mapping=chunk_map(store)
    qrels,missing=label_chunks(case,mapping)
    assert len(qrels)==2 and not missing
    row=grade_answer(case,measured,error,timings,retrieved,mapping)
    assert row['expected_present'] and row['verbatim_support']==1
    assert row['citation_evidence_coverage']==.5  # Duplicate filtering drops one document, not both labels.


def test_errors_stay_in_answer_quality_denominators(tmp_path):
    store=Store(tmp_path/'test.sqlite3')
    store.ingest('a.txt',b'The Juniper manager is Nina Wallace.')
    case=dict(question='Who is the Juniper manager?',category='direct',modality='text',id='t1',answerable=True,
              expected_answers=['Nina Wallace'],evidence=[{'document':'a.txt','span':'Nina Wallace'}])
    result,error,timings,retrieved=measured_run(store,case,'extractive','unused',{})
    row=grade_answer(case,result,error,timings,retrieved,chunk_map(store))
    failure=grade_answer(case,{},'failure',timings,[],chunk_map(store))
    s=answer_summary([row,failure])
    assert s['expected_answer_presence']==.5 and s['errors']==1 and s['factual_n']==2
    assert s['citation_id_validity']==1 and s['answered_factual_n']==1
    assert s['semantic_correctness'] is None and s['unsupported_claim_rate'] is None


def test_http_failure_classification_and_all_attempt_latency():
    assert inspect_response([])=='malformed_response'
    base=dict(answer='Answer [S1]',sources=[dict(id='x',text='Answer',name='a.txt',page=1)],trace=[],mode='extractive')
    assert inspect_response(base) is None
    assert inspect_response({**base,'answer':'Answer [S99]'})=='citation_validation_failure'
    assert inspect_response({**base,'answer':'Answer'})=='citation_validation_failure'
    rows=[dict(failure=None,latency_ms=10),dict(failure='timeout',latency_ms=1000)]
    s=summarize(rows,2)
    assert s['success_rate']==.5 and s['timeout_rate']==.5 and s['latency_ms']['n']==2
    assert s['requests_per_second']==1 and s['successful_requests_per_second']==.5


def test_ocr_edit_distance():
    assert word_error_rate('The manager is Nina.','the manager is Nina')['wer']==0
    assert word_error_rate('one two three','one four three five')=={'errors':2,'reference_words':3,'wer':2/3}


def test_review_relative_output_path_and_preservation_of_completed_judgments(tmp_path,monkeypatch):
    import csv
    from evals import benchmark
    monkeypatch.setattr(benchmark,'ROOT',tmp_path)
    monkeypatch.chdir(tmp_path)
    Path('results').mkdir()
    report={'run_id':'second','answers':{'extractive':{'raw':[{'id':'t1','category':'direct','question':'test','expected_answers':['value'],'answer':'value','sources':[]}]}}}
    path=Path('results/review.csv')
    assert benchmark.human_review(report,path)=='results/review.csv'
    with path.open() as handle:
        reader=csv.DictReader(handle)
        fields=reader.fieldnames;rows=list(reader)
    rows[0]['reviewer']='Independent reviewer'
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    original=path.read_bytes()
    generated=benchmark.human_review(report,path)
    assert path.read_bytes()==original
    assert generated=='results/human-review-second.csv'
