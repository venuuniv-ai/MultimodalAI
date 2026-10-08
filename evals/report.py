"""Generate reports/README exclusively from machine-readable executed results."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BEGIN='<!-- BENCHMARKS:BEGIN -->'
END='<!-- BENCHMARKS:END -->'


def number(value,percent=False):
    if value is None:return 'Unavailable'
    return f'{value*100:.2f}%' if percent else f'{value:.3f}'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |',*['| '+' | '.join(str(value) for value in row)+' |' for row in rows]])


def render(report):
    retrieval=report.get('retrieval',{}).get('summaries',{})
    production=retrieval.get('production_search',{})
    answers=report.get('answers',{})
    ext=answers.get('extractive',{}).get('summary',{})
    llm=answers.get('ollama',{}).get('summary',{})
    reliability=report.get('reliability',{}).get('by_mode',{})
    ext_total=ext.get('stages',{}).get('total_ms',{})
    llm_total=llm.get('stages',{}).get('total_ms',{})
    llm_gen=llm.get('stages',{}).get('generation_ms',{})
    retrieval_times=production.get('latency_ms',{})
    corpus=report['corpus']
    env=report['environment']
    headline=[]
    for key,label in [('recall@5','Recall@5'),('recall@10','Recall@10'),('mrr@10','MRR@10'),('ndcg@5','nDCG@5'),('ndcg@10','nDCG@10')]:
        headline.append([label,number(production.get(key),True),production.get('n',0)])
    headline.extend([
        ['Expected-answer presence / extractive',number(ext.get('expected_answer_presence'),True),ext.get('factual_n',0)],
        ['Expected-answer presence / requested Ollama',number(llm.get('expected_answer_presence'),True),llm.get('factual_n',0)],
        ['Correct exact abstention / extractive',number(ext.get('correct_abstention_rate'),True),ext.get('negative_n',0)],
        ['Correct exact abstention / requested Ollama',number(llm.get('correct_abstention_rate'),True),llm.get('negative_n',0)],
        ['Citation ID validity / extractive',number(ext.get('citation_id_validity'),True),ext.get('answered_factual_n',0)],
        ['Citation ID validity / requested Ollama',number(llm.get('citation_id_validity'),True),llm.get('answered_factual_n',0)],
        ['Semantic correctness / faithfulness / unsupported-claim rate','Unavailable: pending human review','0 human reviews'],
        ['Median / P95 retrieval ms',number(retrieval_times.get('p50'))+' / '+number(retrieval_times.get('p95')),retrieval_times.get('n',0)],
        ['Median / P95 extractive end-to-end ms',number(ext_total.get('p50'))+' / '+number(ext_total.get('p95')),ext_total.get('n',0)],
        ['Median / P95 requested-Ollama end-to-end ms',number(llm_total.get('p50'))+' / '+number(llm_total.get('p95')),llm_total.get('n',0)],
        ['Median / P95 executed local-generation ms',number(llm_gen.get('p50'))+' / '+number(llm_gen.get('p95')),llm_gen.get('n',0)],
        ['HTTP reliability success / extractive',number(reliability.get('extractive',{}).get('success_rate'),True),reliability.get('extractive',{}).get('total_requests',0)],
        ['HTTP reliability success / Ollama',number(reliability.get('ollama',{}).get('success_rate'),True),reliability.get('ollama',{}).get('total_requests',0)],
    ])
    lines=['# Local Research Desk benchmarks','',
           '> Generated from `results/latest.json` by `python -m evals.report`. Do not edit metric tables manually.','',
           f'Recorded {env["recorded_at"]} ({env["timezone"]}). New synthetic held-out dataset: **{report["dataset_size"]} cases**, not used to tune production. Agent-authored and template-related; not independent human or production evaluation.',
           f'Hardware: {env.get("processor")}, {env.get("cpu_count")} logical CPUs, {number((env.get("ram_bytes") or 0)/1024**3)} GiB RAM; {env["platform"]}. Python {env["python"].split()[0]}. Model: {answers.get("ollama",{}).get("model") or "unavailable"}; model digest/quantization and installed versions are in raw JSON.',
           f'Base corpus: {corpus["base_document_count"]} documents, {corpus["base_chunk_count"]} chunks, {corpus["base_corpus_bytes"]} original bytes. Twenty-five adversarial cases each use their labeled official document plus one isolated untrusted attachment. Corpus/label SHA256: `{report["dataset_sha256"]}`.',
           '', '## Headline results','',
           'Retrieval headline evaluates the actual `Store.search` on raw questions before answer-stage aliases/filtering. It includes labeled answerable adversarial contexts. Answer presence requires **all** expected literal values, including multi-part answers. Rates are fractions, shown as percentages; MRR/nDCG can also be read on the 0–1 scale.','',table(['Metric','Result','Sample size'],headline),'',
           'Requested-Ollama end-to-end latency includes questions handled by abstention gates, clarification, and CSV tools. Executed generation-call latency excludes those bypasses. Do not describe the mixed-path median as model inference speed. Citation ID validity is membership, not semantic citation correctness.','',
           '## Retrieval ablation','',report.get('retrieval',{}).get('ablation_note','No ablation executed.'),'',
           table(['Configuration','N','Recall@5','Recall@10','MRR@10','nDCG@5','nDCG@10','P50 ms','P95 ms','Timing N'],[
               [config,s['n'],*[number(s.get(key),True) for key in ['recall@5','recall@10','mrr@10','ndcg@5','ndcg@10']],number(s['latency_ms']['p50']),number(s['latency_ms']['p95']),s['latency_ms']['n']]
               for config,s in retrieval.items()]),'',
           'The full evidence pipeline is capped at five sources by production. Its Recall@10 equals Recall@5 because it cannot return ten sources. Chunk relevance uses the full chunk; focused evidence may omit the expected fact. Citation-evidence coverage below measures this separately. Configurations are rotated per question/repeat; first warmups are excluded.','',
           '### Differences relative to TF-IDF','',
           table(['Configuration','Recall@5 Δ pp','Recall@10 Δ pp','MRR Δ pp','nDCG@5 Δ pp','nDCG@10 Δ pp','P95 Δ ms'],[
               [row['configuration'],*[number(row.get(key+'_delta')*100 if row.get(key+'_delta') is not None else None) for key in ['recall@5','recall@10','mrr@10','ndcg@5','ndcg@10']],number(row['p95_latency_ms_delta'])] for row in report.get('retrieval',{}).get('comparisons',[])]),'',
           'These are observed paired workload differences, not causal significance or confidence intervals. No speed/quality improvement is assumed.','',
           '## Source-type results','',
           'N counts labeled factual questions; latency is in-process complete response time and includes all questions assigned to that source type (separate timing N). Adversarial cases inherit their official source modality. Text includes TXT/Markdown-style plain text, not semantic embeddings. OCR is image-derived text, not visual reasoning.','']
    for mode,summary in [('extractive',ext),('ollama',llm)]:
        lines.extend([f'### {mode}','',table(['Source','Factual N','Hit@5','Recall@5','Recall@10','MRR@10','All-values presence','P50 ms','P95 ms','Timing N'],[
            [source,production.get('by_modality',{}).get(source,{}).get('n',0),
             *[number(production.get('by_modality',{}).get(source,{}).get(key),True) for key in ['hit@5','recall@5','recall@10','mrr@10']],
             number(summary.get('by_modality',{}).get(source,{}).get('expected_answer_presence'),True),
             number(summary.get('by_modality',{}).get(source,{}).get('stages',{}).get('total_ms',{}).get('p50')),
             number(summary.get('by_modality',{}).get(source,{}).get('stages',{}).get('total_ms',{}).get('p95')),
             summary.get('by_modality',{}).get(source,{}).get('n',0)] for source in ['text','pdf','csv','ocr','cross_document']]),''])
    lines.extend(['## All retrieval metrics by category','',table(['Category','N','Hit@1','Hit@3','Hit@5','Hit@10','Recall@1','Recall@3','Recall@5','Recall@10','Precision@5','Precision@10','MRR@10','nDCG@5','nDCG@10'],[
        [category,s['n'],*[number(s.get(key),True) for key in ['hit@1','hit@3','hit@5','hit@10','recall@1','recall@3','recall@5','recall@10','precision@5','precision@10','mrr@10','ndcg@5','ndcg@10']]] for category,s in production.get('by_category',{}).items()]),'',
        'All configurations also have all metrics grouped by category and modality in raw JSON. Missing/invalid qrels are explicitly counted; benchmark exits nonzero after preserving execution/label failures.','',
        '## Answers, abstention, and attacks','',table(['Measure','Extractive','Ollama'],[
            [label,number(ext.get(key),True),number(llm.get(key),True)] for key,label in [
                ('expected_answer_presence','All expected literal values present'),('correct_abstention_rate','Exact standard refusal on unavailable facts'),
                ('false_answer_rate','Non-refusal/non-clarification answer on unavailable facts'),('negative_clarification_rate','Clarification on unavailable facts'),
                ('false_negative_abstention_rate','False-negative exact refusal on answerable facts'),('citation_id_validity','Valid citation IDs on answered factual questions'),
                ('citation_label_precision','Mean fraction of cited chunks carrying labeled relevant evidence'),('citation_evidence_coverage','Mean expected evidence-unit coverage in cited focused text'),
                ('verbatim_source_support','Mean claim-string copied from its cited source (mechanical proxy)'),('tool_exact_match','Exact deterministic CSV values'),
                ('ambiguous_clarify_or_abstain','Ambiguous query clarification/refusal'),('attack_canary_emission','Attack canary emission rate (lower is better)'),
                ('attack_expected_answer_without_canary','Attack expected values present without canary')]]),'',
        f'Factual/negative/tool/ambiguous/adversarial denominators: {ext.get("factual_n",0)} / {ext.get("negative_n",0)} / {ext.get("tool_n",0)} / {ext.get("ambiguous_n",0)} / {ext.get("attack_n",0)}. Citation metrics use answered/cited subsets; raw JSON includes counts. Exact refusals exclude alternative safe wording. Expected-span presence can reward contradictory extras and penalize valid paraphrases. Source-copy support proves string inclusion only, not factual truth or absence of unsupported claims.','',
        'Twenty-five isolated attachment cases cover imperatives, role spoofing, deceptive assertions, high-keyword noise, and obfuscated instructions. Success proxy requires expected values and no injected canary. Canary absence alone is not attack resistance; abstention can hide loss of utility. Semantic contradiction/faithfulness remain review tasks.',''])
    for mode,summary in [('extractive',ext),('ollama',llm)]:
        lines.extend([f'### Attack outcomes: {mode}','',table(['Threat','N','Canary emitted','Expected values without canary'],[
            [threat,s['attack_n'],number(s['attack_canary_emission'],True),number(s['attack_expected_answer_without_canary'],True)] for threat,s in summary.get('by_threat',{}).items()]),''])
    timings=[]
    for source,s in corpus['ingestion_by_modality'].items():timings.append(('ingestion '+source,s))
    for source,s in corpus['extraction_by_modality'].items():timings.append(('extraction/OCR '+source,s))
    for config,s in retrieval.items():timings.append(('retrieval '+config,s['latency_ms']))
    for mode,summary in [('extractive',ext),('ollama',llm)]:
        for stage,s in summary.get('stages',{}).items():timings.append((mode+' '+stage,s))
    for mode,s in reliability.items():timings.append(('HTTP '+mode,s['latency_ms']))
    lines.extend(['## Latency distributions','',
        'All times are wall-clock milliseconds. P50 is the median; P90/P95/P99 use nearest-rank percentiles. Ingestion is actual Store.ingest including parsing/chunking/SQLite commit. Separate extraction timings call the real parser/OCR independently (not additive stage subtraction). Three repetitions per document unless overridden. No model warmup counts in steady-state samples; raw warmups record first observed request without asserting a cold start.','',
        table(['Measurement','N','Mean','P50','P90','P95','P99','Min','Max'],[[name,s['n'],*[number(s.get(key)) for key in ['mean','p50','p90','p95','p99','min','max']]] for name,s in timings]),'',
        '## HTTP reliability and throughput','',
        report.get('reliability',{}).get('boundary','Unavailable'),'',
        table(['Mode','Concurrency','N','Succeeded','Failed','Timeout rate','Exception rate','Malformed rate','Bad citations','Queries/s','P50 ms','P95 ms','P99 ms'],[
            [b['mode'],b['concurrency'],b['total_requests'],b['successful_requests'],b['failed_requests'],number(b['timeout_rate'],True),number(b['exception_rate'],True),number(b['malformed_response_rate'],True),b['citation_validation_failures'],number(b['requests_per_second']),*[number(b['latency_ms'][k]) for k in ['p50','p95','p99']]] for b in report.get('reliability',{}).get('batches',[])]),'',
        report.get('reliability',{}).get('limitations','Not executed.'),
        'All raw failures, HTTP status errors, exception/timeout details, responses, and request durations are retained. This is a bounded short reliability test, not long-running production uptime. LLM load remains sequential to respect local resources.','',
        '## Resources and index',''])
    resources=report['resources']
    lines.extend([table(['Process group','RSS mean MiB','RSS sampled peak MiB','Mean CPU % (one core)','CPU sampled peak %'],[
        [group,number(s['rss_bytes']['mean']/1024**2 if s['rss_bytes']['mean'] is not None else None),number(s['rss_bytes']['max']/1024**2 if s['rss_bytes']['max'] is not None else None),number(s['cpu_percent_one_core']['mean']),number(s['cpu_percent_one_core']['max'])] for group,s in resources['overall'].items()]),'',
        resources['limitations'],f'Sampler interval: {resources["interval_seconds"]} s; {resources["samples"]} samples. Phase-specific summaries and raw samples are retained.',
        f'SQLite size: {corpus["sqlite_bytes"]} bytes. Persisted retrieval index: {corpus["persisted_retrieval_index_bytes"]} bytes. {corpus["index_note"]}',
        'GPU utilization and dedicated VRAM: unavailable (Apple unified-memory machine; no NVIDIA counters). Ollama loaded-model metadata, including reported model residency, is preserved without treating it as measured GPU utilization.','',
        '### OCR extraction quality','',table(['Image','Reference words','Word edits','Normalized WER'],[[r['document'],r['reference_words'],r['errors'],number(r['wer'],True)] for r in corpus['ocr']]),'',
        'WER uses lowercase alphanumeric word tokens and an authored transcription. Only two clean synthetic English images: not a general OCR benchmark. Parsing failures are separate corpus errors.','',
        '## Unavailable metrics and validity limits','',
        '- Human semantic correctness, faithfulness, semantic citation correctness/claim coverage, and unsupported-claim rate have no completed independent judgments. Use the structured review worksheet and rubric in `METHODOLOGY.md`.',
        '- TTFT/token throughput and isolated model inference time are unavailable: production uses a non-streaming chat call without retaining token/timing metadata. Generation wall time includes HTTP/model discovery/validation.',
        '- Exact cold-start inference, hardware energy, GPU utilization, VRAM, and attributable transient index RAM were not measured.',
        '- No independent real-world users/documents, external labeling, bootstrap confidence intervals, production-scale corpus, noisy scans, visual reasoning, open-loop arrival rates, long soak, distributed hardware, or cross-machine comparisons.',
        '- Questions share authored templates/facts. Multi-chunk/cross-document tasks can be missed by single-sentence lexical heuristics. This benchmark measures those misses without tuning production.',
        '- Low-precision top-k can reflect overlap duplicates; qrels judge every chunk containing an authored evidence unit. Relevance is exhaustive for these labels, not an independent semantic relevance judgment.',
        '- Existing development results remain unchanged in `RESULTS.md` and earlier JSON. The new held-out synthetic results are the measurements above; no comparison claims between these different datasets.',
        '', '## Reproduce','', 'See [methodology and commands](METHODOLOGY.md). Raw results: [latest.json](results/latest.json); review worksheet: [human-review.csv](results/human-review.csv).',
        '', f'Application commit: `{report["git_commit"]}`; exact application/harness SHA256 hashes are in raw output.'])
    return '\n'.join(lines)+'\n'


def readme_section(report):
    s=report.get('retrieval',{}).get('summaries',{}).get('production_search',{})
    ext=report.get('answers',{}).get('extractive',{}).get('summary',{})
    rel=report.get('reliability',{}).get('by_mode',{}).get('extractive',{})
    env=report['environment'];corpus=report['corpus']
    model=report.get('answers',{}).get('ollama',{}).get('model') or 'not measured'
    rows=[[name,number(s.get(key),True)] for name,key in [('Recall@5','recall@5'),('Recall@10','recall@10'),('MRR@10','mrr@10')]]
    rows.extend([['Extractive all-values presence (proxy)',number(ext.get('expected_answer_presence'),True)],
                 ['Exact abstention on unavailable facts',number(ext.get('correct_abstention_rate'),True)],
                 ['Extractive median / P95 end-to-end ms',number(ext.get('stages',{}).get('total_ms',{}).get('p50'))+' / '+number(ext.get('stages',{}).get('total_ms',{}).get('p95'))],
                 [f'HTTP reliability ({rel.get("total_requests",0)} requests)',number(rel.get('success_rate'),True)]])
    return '\n'.join([BEGIN,'## Benchmarks','',f'New synthetic held-out benchmark, {report["dataset_size"]} questions; production code was frozen and not tuned on these cases. Recorded {env["recorded_at"][:10]} on {env.get("processor")}, {number((env.get("ram_bytes") or 0)/1024**3)} GiB RAM; local model `{model}`. Base corpus: {corpus["base_document_count"]} documents / {corpus["base_chunk_count"]} chunks; separate isolated injection contexts. Retrieval metrics cover {s.get("n",0)} labeled factual cases.','',table(['Measured metric','Result'],rows),'',
                      'String presence and citation IDs do not establish semantic correctness. This is agent-authored synthetic evaluation, not independent or production validation; images use OCR, not visual reasoning. [Full measured report](evals/BENCHMARKS.md) · [Methodology and reproduction](evals/METHODOLOGY.md) · [Raw results](evals/results/latest.json).',END])


def write_reports(report):
    (ROOT/'evals/BENCHMARKS.md').write_text(render(report))
    readme=ROOT/'README.md'
    original=readme.read_text()
    section=readme_section(report)
    if BEGIN in original and END in original:
        start=original.index(BEGIN);end=original.index(END)+len(END)
        original=original[:start]+section+original[end:]
    else:
        original=original.replace('## Data and development',section+'\n\n## Data and development',1)
    readme.write_text(original)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'evals/results/latest.json')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    report=json.loads(args.input.read_text())
    if args.check:
        assert (ROOT/'evals/BENCHMARKS.md').read_text()==render(report),'Benchmark Markdown drift'
        assert readme_section(report) in (ROOT/'README.md').read_text(),'README metric drift'
        print('Markdown and README exactly match raw benchmark results.')
    else:write_reports(report)


if __name__=='__main__':main()
