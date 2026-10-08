"""Run frozen evaluations against the actual application without tuning it."""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from backend.app import agent
from .corpus import Corpus, label_chunks, load_dataset, normalize
from .latency_eval import measured_run
from .metrics import aggregate_ranking, answer_summary, distribution, mean, ranking_metrics
from .reliability_eval import run_http
from .resources import ResourceSampler, environment
from .retrieval_eval import CONFIGS, retrieve

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'evals/results'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ollama_snapshot(endpoint):
    try:
        with urllib.request.urlopen(agent.OLLAMA+endpoint,timeout=3) as response:
            return json.load(response)
    except (OSError,ValueError) as exc:
        return {'unavailable':str(exc)}


def retrieval_evaluation(corpus,cases,configs,repeats=3):
    raw={config:[] for config in configs}
    eligible=[case for case in cases if case['answerable'] and case['evidence']]
    # Warm all configurations; exclude from steady-state timing.
    warmup=[]
    for config in configs:
        try:
            retrieve(corpus.store,eligible[0]['question'],config)
            warmup.append({'config':config,'error':None})
        except Exception as exc:
            warmup.append({'config':config,'error':f'{type(exc).__name__}: {exc}'})
    for repeat in range(repeats):
        for j,case in enumerate(eligible):
            store,mapping=corpus.context(case)
            qrels,missing=label_chunks(case,mapping)
            order=list(configs)
            offset=(j+repeat)%len(order)
            order=order[offset:]+order[:offset]
            for config in order:
                error=None
                sources=[]
                start=time.perf_counter()
                try:sources=retrieve(store,case['question'],config)
                except Exception as exc:error=f'{type(exc).__name__}: {exc}'
                ms=(time.perf_counter()-start)*1000
                keys=[mapping[s['id']]['key'] for s in sources]
                metrics=None if missing else ranking_metrics(keys,qrels)
                raw[config].append(dict(id=case['id'],category=case['category'],modality=case['modality'],repeat=repeat,
                                        ranked=keys,qrels=qrels,metrics=metrics,latency_ms=ms,error=error,
                                        label_error=missing or None,
                                        focused_evidence=[s.get('evidence_text') for s in sources] if config=='full_pipeline' else None))
        print(f'Retrieval repeat {repeat+1}/{repeats} complete ({len(eligible)} questions, {len(configs)} configurations).',flush=True)
    summaries={}
    for config,rows in raw.items():
        summary=aggregate_ranking([r for r in rows if r['repeat']==0])
        summary['latency_ms']=distribution(r['latency_ms'] for r in rows)
        summary['execution_errors']=sum(bool(r['error']) for r in rows)
        for dimension in ['category','modality']:
            for group in summary['by_'+dimension]:
                summary['by_'+dimension][group]['latency_ms']=distribution(r['latency_ms'] for r in rows if r[dimension]==group)
        summaries[config]=summary
    comparisons=[]
    baseline=summaries.get('tfidf')
    if baseline:
        for config,summary in summaries.items():
            if config=='tfidf':continue
            comparisons.append(dict(baseline='tfidf',configuration=config,n=summary['n'],
                                    **{key+'_delta':summary.get(key)-baseline.get(key) if summary.get(key) is not None and baseline.get(key) is not None else None for key in ['recall@5','recall@10','mrr@10','ndcg@5','ndcg@10']},
                                    p95_latency_ms_delta=summary['latency_ms']['p95']-baseline['latency_ms']['p95']))
    return dict(summaries=summaries,comparisons=comparisons,raw=raw,warmup=warmup,repeats=repeats,
                metric_boundary='production_search: actual Store.search on raw query, top 10. full_pipeline: actual aliases + Store.search + focus_evidence, max 5 sources; chunk relevance is judged on complete returned source text. Focused-evidence coverage is assessed separately in answers.',
                ablation_note='Production hybrid already IS reciprocal-rank fusion. hybrid_rrf removes lexical reranking. hybrid_score_sum is an explicitly experimental equal-weight max-normalized score-sum comparator, not a separable existing production stage.')


def grade_answer(case,result,error,timings,retrieved,mapping):
    answer=result.get('answer','')
    sources=result.get('sources',[])
    qrels,missing=label_chunks(case,mapping)
    cited_numbers=[int(n) for n in re.findall(r'\[S(\d+)\]',answer)]
    cited=[sources[n-1] for n in set(cited_numbers) if 1<=n<=len(sources)]
    citation_precision=mean(mapping[s['id']]['key'] in qrels for s in cited)
    covered=[any(s['name']==label['document'] and normalize(label['span']) in normalize(s.get('evidence_text',s['text'])) for s in cited) for label in case['evidence']]
    statements=[line.strip() for line in answer.split('\n\n') if re.search(r'\[S\d+\]',line)]
    support=[]
    for line in statements:
        text=normalize(re.sub(r'\[S\d+\]','',line))
        refs=[int(n) for n in re.findall(r'\[S(\d+)\]',line)]
        support.append(any(text in normalize(sources[n-1].get('evidence_text',sources[n-1]['text'])) for n in refs if 1<=n<=len(sources)))
    tool_match=None
    if case['category']=='csv_tool':
        try:
            parsed=json.loads(answer)
            tool_match=not error and all(parsed.get(k)==v for k,v in case['expected_values'].items())
        except (ValueError,AttributeError):tool_match=False
    return dict(id=case['id'],category=case['category'],modality=case['modality'],answerable=case['answerable'],
                question=case['question'],expected_answers=case['expected_answers'],answer=answer,sources=sources,
                actual_mode=result.get('mode'),error=error,warning=result.get('warning'),
                abstained=answer==agent.NO_EVIDENCE,clarified=result.get('mode')=='clarification',
                expected_present=bool(case['expected_answers']) and not error and all(normalize(value) in normalize(answer) for value in case['expected_answers']),
                citation_valid=bool((result.get('citation_check') or {}).get('valid')),
                citation_label_precision=citation_precision,citation_evidence_coverage=mean(covered),
                verbatim_support=mean(support),tool_match=tool_match,
                canary_emitted=any(normalize(value) in normalize(answer) for value in case.get('forbidden_strings',[])),
                threat=case.get('threat'),label_error=missing or None,**timings)


def answer_evaluation(corpus,cases,mode,model,warmups=3):
    first=next(case for case in cases if case['category']=='direct')
    warmup=[]
    loaded_before=ollama_snapshot('/api/ps') if mode=='ollama' else None
    for _ in range(warmups):
        result,error,timings,retrieved=measured_run(corpus.store,first,mode,model,corpus.ids)
        warmup.append({'error':error,'actual_mode':result.get('mode'),**timings})
    rows=[]
    for index,case in enumerate(cases):
        store,mapping=corpus.context(case)
        result,error,timings,retrieved=measured_run(store,case,mode,model,corpus.ids)
        rows.append(grade_answer(case,result,error,timings,retrieved,mapping))
        if (index+1)%25==0 or index+1==len(cases):
            print(f'{mode} answers {index+1}/{len(cases)}; errors so far {sum(bool(r["error"]) for r in rows)}.',flush=True)
    summary=answer_summary(rows)
    summary['by_category']={category:answer_summary([r for r in rows if r['category']==category]) for category in sorted({r['category'] for r in rows})}
    summary['by_modality']={category:answer_summary([r for r in rows if r['modality']==category]) for category in sorted({r['modality'] for r in rows})}
    summary['by_threat']={threat:answer_summary([r for r in rows if r['threat']==threat]) for threat in sorted({r['threat'] for r in rows if r['threat']})}
    return dict(requested_mode=mode,model=model if mode=='ollama' else None,summary=summary,raw=rows,warmup=warmup,
                loaded_models_before=loaded_before,loaded_models_after=ollama_snapshot('/api/ps') if mode=='ollama' else None,
                cold_start_note='First observed warmup recorded, but NOT asserted cold: Ollama may already have resident model weights. No model unloading or modification performed.',
                timing_note='In-process agent.run wall time (no HTTP); retrieval is Store.search only; generation is the entire generated_answer call including model discovery, HTTP inference, JSON validation/rendering. Gates/clarifications/tools count in total, not generation. True TTFT/token latency unavailable.')


def human_review(report,path):
    fields=['mode','id','category','question','expected_answers','answer','sources_json','human_correct','human_faithful',
            'claim_count','unsupported_claim_count','supported_cited_claim_count','claims_requiring_citation','human_abstention_correct','human_attack_success','reviewer','notes']
    # Never replace completed human annotations on rerun.
    if path.exists():
        with path.open() as handle:
            if any(row.get('reviewer') or row.get('human_correct') or row.get('notes') for row in csv.DictReader(handle)):
                path=path.with_name('human-review-'+report['run_id']+'.csv')
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        for mode,evaluation in report.get('answers',{}).items():
            for row in evaluation.get('raw',[]):
                writer.writerow(dict(mode=mode,id=row['id'],category=row['category'],question=row['question'],
                                     expected_answers=json.dumps(row['expected_answers']),answer=row['answer'],sources_json=json.dumps(row['sources'])))
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for phase in ['retrieval','ablation','latency','reliability','all']:
        parser.add_argument('--'+phase,action='store_true')
    parser.add_argument('--mode',choices=['extractive','ollama','both'],default='both')
    parser.add_argument('--model',default='qwen2.5:1.5b')
    parser.add_argument('--retrieval-repeats',type=int,default=3)
    parser.add_argument('--ingestion-repeats',type=int,default=3)
    parser.add_argument('--requests',type=int,default=512)
    parser.add_argument('--llm-http-requests',type=int,default=24)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--no-report',action='store_true',help='Preserve existing Markdown/README while saving a separate execution.')
    args=parser.parse_args()
    if not any(getattr(args,p) for p in ['retrieval','ablation','latency','reliability','all']):parser.error('Choose a benchmark phase or --all.')
    if min(args.retrieval_repeats,args.ingestion_repeats,args.requests)<1 or args.llm_http_requests<0:parser.error('Repeat/request counts must be positive (LLM HTTP count can be zero).')
    dataset,manifest=load_dataset()
    machine=environment()
    report=dict(schema_version=1,run_id=machine['recorded_at'].replace(':','').replace('+','_'),environment=machine,
                git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                application_sha256={name:digest(ROOT/name) for name in ['backend/app/store.py','backend/app/agent.py','backend/app/main.py','backend/app/evidence.py']},
                harness_sha256={str(path.relative_to(ROOT)):digest(path) for path in sorted((ROOT/'evals').glob('*.py'))},
                dataset_sha256=manifest['dataset_sha256'],dataset_provenance=dataset['provenance'],dataset_size=len(dataset['cases']),
                command=[str(arg) for arg in __import__('sys').argv],ollama_tags=ollama_snapshot('/api/tags'),unavailable={})
    with tempfile.TemporaryDirectory(prefix='research-desk-benchmark-') as directory:
        with ResourceSampler() as sampler:
            sampler.phase='ingestion'
            corpus=Corpus(directory,dataset,args.ingestion_repeats)
            report['corpus']=corpus.report()
            report['qrels']={case['id']:{'labels':case['evidence'],'chunk_grades':label_chunks(case,corpus.context(case)[1])[0],
                                      'missing_labels':label_chunks(case,corpus.context(case)[1])[1]} for case in dataset['cases'] if case['evidence']}
            report['chunk_catalog']=list(corpus.mapping.values())
            if args.all or args.retrieval or args.ablation:
                sampler.phase='retrieval'
                configs=CONFIGS if args.all or args.ablation else ['production_search','full_pipeline']
                report['retrieval']=retrieval_evaluation(corpus,dataset['cases'],configs,args.retrieval_repeats)
            models=agent.ollama_models()
            use_llm=args.mode in ['ollama','both'] and args.model in models
            if args.mode in ['ollama','both'] and not use_llm:
                report['unavailable']['ollama']='Requested model not available through running local Ollama; no generation scores invented.'
            if args.all or args.latency:
                report['answers']={}
                for mode in ['extractive','ollama']:
                    if mode=='extractive' and args.mode=='ollama':continue
                    if mode=='ollama' and not use_llm:continue
                    sampler.phase='answers_'+mode
                    report['answers'][mode]=answer_evaluation(corpus,dataset['cases'],mode,args.model)
            if args.all or args.reliability:
                sampler.phase='http_load'
                try:report['reliability']=run_http(corpus,dataset,directory,args.requests,args.model,args.llm_http_requests if use_llm else 0)
                except Exception as exc:
                    report['reliability']={'error':f'{type(exc).__name__}: {exc}'}
            sampler.phase='finalize'
        report['resources']=sampler.report()
    RESULTS.mkdir(exist_ok=True)
    phase='latest' if args.all else '-'.join(p for p in ['retrieval','ablation','latency','reliability'] if getattr(args,p))
    output=(args.output or RESULTS/(phase+'.json')).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    # Persist raw measurements before optional review/report artifacts.
    output.write_text(json.dumps(report,indent=2)+'\n')
    if report.get('answers'):report['human_review_file']=human_review(report,output.parent/('human-review.csv' if args.all else phase+'-human-review.csv'))
    output.write_text(json.dumps(report,indent=2)+'\n')
    if args.all and not args.no_report:
        from .report import write_reports
        write_reports(report)
    print(f'Saved {output}',flush=True)
    # Fail conspicuously after preserving all raw failures; quality misses are valid measurements.
    failures=report['corpus']['errors']
    retrieval_errors=sum(s['execution_errors'] for s in report.get('retrieval',{}).get('summaries',{}).values())
    answer_errors=sum(e['summary']['errors'] for e in report.get('answers',{}).values())
    label_errors=sum(bool(q['missing_labels']) for q in report['qrels'].values())
    reliability_errors=bool(report.get('reliability',{}).get('error')) or sum(s['failed_requests'] for s in report.get('reliability',{}).get('by_mode',{}).values())
    if failures or retrieval_errors or answer_errors or label_errors or reliability_errors:
        raise SystemExit('Benchmark completed with execution/label/HTTP failures; inspect raw report. No failures hidden.')


if __name__=='__main__':
    main()
