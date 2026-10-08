"""Generate before/after report from frozen raw executions, no score changes."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from .report import number, table

ROOT=Path(__file__).resolve().parents[1]
BEFORE=ROOT/'evals/results/before-architecture/latest.json'
AFTER=ROOT/'evals/results/after-architecture/latest.json'
SECONDARY=ROOT/'evals/results/secondary-final.json'
REPORT=ROOT/'evals/ARCHITECTURE_RESULTS.md'
START='<!-- ARCHITECTURE:BEGIN -->'
END='<!-- ARCHITECTURE:END -->'


def check_frozen():
    frozen=json.loads((ROOT/'evals/results/before-architecture/frozen-files.json').read_text())
    for name,expected in frozen.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,'Frozen file changed: '+name


def taxonomy(report):
    queries={row['id']:row for row in report['retrieval']['raw']['production_search'] if row['repeat']==0}
    result={}
    for mode,evaluation in report['answers'].items():
        failures=[]
        for row in evaluation['raw']:
            if not row['answerable'] or row['category']=='csv_tool' or row['expected_present']:continue
            if row['error']:cause='execution_error'
            elif row['clarified'] and any(s.get('evidence_conflict') for s in row['sources']):cause='conflict_clarification'
            elif queries[row['id']]['metrics']['recall@10']==0:cause='retrieval_failure'
            elif not all(any(value.lower() in s.get('evidence_text','').lower() for s in row['sources']) for value in row['expected_answers']):cause='evidence_selection_failure'
            else:cause='answer_construction_or_generation_failure'
            failures.append({'id':row['id'],'category':row['category'],'cause':cause,'abstained':row['abstained'],'clarified':row['clarified']})
        result[mode]={'presence_failures':len(failures),'counts':dict(Counter(row['cause'] for row in failures)),
                      'raw':failures,'over_abstention_flags':sum(row['abstained'] for row in failures),
                      'extraction_errors':len(report['corpus']['errors']),
                      'context_truncation_note':'No truncation failure established; rejected facts are absent before context assembly in baseline.'}
    return result


def comparison_rows(before,after):
    rows=[]
    raw=[]
    def add(label,b,a,kind='rate'):
        percent=kind=='rate'
        diff=None if a is None or b is None else a-b
        rows.append([label,f'{b:.6f}' if kind=='0–1' and b is not None else number(b,percent),f'{a:.6f}' if kind=='0–1' and a is not None else number(a,percent),('Unavailable' if diff is None else f'{diff*100:+.2f} pp' if percent else f'{diff:+.6f}' if kind=='0–1' else f'{diff:+.3f}')])
        raw.append({'metric':label,'before':b,'after':a,'delta':diff,'units':'fraction / percentage-point presentation' if percent else kind})
    for config,prefix in [('production_search','Production'),('full_pipeline','Full evidence')]:
        for key,name in [('recall@5','Recall@5'),('recall@10','Recall@10'),('mrr@10','MRR@10'),('ndcg@5','nDCG@5'),('ndcg@10','nDCG@10')]:
            add(prefix+' '+name,before['retrieval']['summaries'][config][key],after['retrieval']['summaries'][config][key],'rate' if key.startswith('recall') else '0–1')
    for mode in ['extractive','ollama']:
        b=before['answers'][mode]['summary'];a=after['answers'][mode]['summary']
        add(mode+' overall expected-value presence',b['expected_answer_presence'],a['expected_answer_presence'])
        for modality in ['text','pdf','csv','ocr','cross_document']:
            add(mode+' '+modality+' expected-value presence',b['by_modality'][modality]['expected_answer_presence'],a['by_modality'][modality]['expected_answer_presence'])
        for key,label in [('correct_abstention_rate','correct exact abstention'),('false_negative_abstention_rate','false-negative exact abstention'),
                          ('ambiguous_clarify_or_abstain','ambiguity clarification/refusal'),('attack_canary_emission','attack canary emission'),
                          ('attack_expected_answer_without_canary','attack expected answer without canary'),('citation_id_validity','citation ID validity')]:
            add(mode+' '+label,b[key],a[key])
        add(mode+' factual refusal or clarification',sum(row['abstained'] or row['clarified'] for row in before['answers'][mode]['raw'] if row['answerable'] and row['category']!='csv_tool')/b['factual_n'],sum(row['abstained'] or row['clarified'] for row in after['answers'][mode]['raw'] if row['answerable'] and row['category']!='csv_tool')/a['factual_n'])
        for p in ['p50','p95']:add(mode+' total '+p+' ms',b['stages']['total_ms'][p],a['stages']['total_ms'][p],'ms')
        bt=[r for r in before['answers'][mode]['raw'] if r['threat']=='deceptive_fact']
        at=[r for r in after['answers'][mode]['raw'] if r['threat']=='deceptive_fact']
        add(mode+' deceptive-fact canary emission',sum(r['canary_emitted'] for r in bt)/len(bt),sum(r['canary_emitted'] for r in at)/len(at))
        add(mode+' HTTP reliability success',before['reliability']['by_mode'][mode]['success_rate'],after['reliability']['by_mode'][mode]['success_rate'])
    return rows,raw


def render(before,after,secondary):
    boundary=json.loads((ROOT/'evals/results/boundary.json').read_text())
    rows,raw=comparison_rows(before,after)
    bt=taxonomy(before);at=taxonomy(after)
    lines=['# Evidence architecture: frozen before/after evaluation','',
           '> Generated from preserved baseline, revised frozen benchmark, and preserved secondary executions. No benchmark questions, labels, scoring formulas, or cases were changed.','',
           '[Root-cause audit written before changes](ARCHITECTURE_AUDIT.md). [Original 203-case baseline](BENCHMARKS.md). [After raw results](results/after-architecture/latest.json). [Final secondary raw results](results/secondary-final.json).','',
           f'Original dataset SHA256: `{after["dataset_sha256"]}`. Before and after use the same {after["dataset_size"]} cases and {after["corpus"]["base_chunk_count"]}-chunk base corpus. This original set is now a **known diagnostic regression**, since its failure classes informed the architecture. Do not call the after scores fresh held-out validation.','',
           f'Secondary dataset SHA256: `{secondary["dataset_sha256"]}`; {secondary["dataset_size"]} class-level cases authored and frozen after design but before revised application results. Initial execution and final-version regression execution are both preserved; no application changes were driven by secondary results. Final application hashes match the full run. Both sets are agent-authored synthetic, not independent production evidence.','',
           f'Before recorded: {before["environment"]["recorded_at"]}; after recorded: {after["environment"]["recorded_at"]}. Hardware and model versions are retained in both raw outputs.', '',
           '## Exact implementation changes','',
           '- `backend/app/evidence.py`: common morphology/relation normalization; declarative entity/attribute/value units; per-conjunct field matching; independent entity constraints; coverage-aware selection within five sources; overlap/unit deduplication.',
           '- Same-document/page fragments at an unpunctuated chunk tail are reconciled only when literal suffix/prefix overlap proves continuation into a complete claim. Cross-document, cross-page, complete-sentence and non-overlapping prefix values remain contradictory.\n- Generic conflict/ambiguity checks operate on applicable entity/relation groups. Contradictory values cause clarification; no filename, heading authority claim, benchmark entity, expected value, or canary is treated as trusted.',
           '- Control-language detector recognizes role/control structures and spaced-letter obfuscation. Instruction-bearing chunks are quarantined; benign unrelated maintenance procedures are retained, but quoted hostile examples can be rejected.',
           '- `agent.py`: uses planned evidence units for extractive synthesis instead of applying whole-query thresholds again; retains conservative legacy fallback for non-copular prose/CSV and existing missing-field/year guards.',
           '- Ollama receives typed JSON containing quoted untrusted evidence and requested fact units. The system prompt asks for every requested entity/relation and forbids following document instructions. Schema/source-ID validation remains unchanged.',
           '- Retrieval formulas, ranking/reranking, top-ten candidate budget, five-source cap, three-statement answer cap, OCR/PDF/CSV ingestion, UI implementation, frozen primary dataset, and scoring are unchanged.',
           '- Harness changes are output/provenance only: `--no-report` preserves original reports/worksheet; application hashes include the new module. New comparison, secondary runner, human-review viewer, and class-level backend/browser tests are separate.',
           '', '## Before versus after','',table(['Metric','Before','After','Difference'],rows),'',
           'Retrieval quality uses 157 unique factual cases; timing uses 471 executions per configuration. Expected-value presence uses 157 factual cases per mode; negatives 35; attacks 25; deceptive-fact subset 5; ambiguity 6. Answer latency includes all 203 requests, including gates/tools/clarification. HTTP reliability covers 512 extractive and 24 requested-Ollama responses. MRR/nDCG are shown on the 0–1 scale. Rates use percentage-point differences.','',
           '## Failure taxonomy','',table(['Mode','Stage/cause','Before count','After count'],[
               [mode,cause,bt[mode]['counts'].get(cause,0),at[mode]['counts'].get(cause,0)]
               for mode in ['extractive','ollama'] for cause in ['retrieval_failure','evidence_selection_failure','answer_construction_or_generation_failure','conflict_clarification','execution_error']]),'',
           'These are mutually exclusive expected-value miss attributions, not independent semantic grading. Over-abstention is a separate operational flag. The baseline has 30 upstream selection misses (20 paraphrases, ten cross-document), including 22 refusals and eight irrelevant responses. No extraction failure or context-truncation failure was established. The original chunk-recall drop also includes four overlap-duplicate removals; those do not lose unique facts.',
           'Adversarial contamination is assessed separately because a contaminated answer can still contain the expected value and pass literal presence. Safe conflict clarifications count as expected-value misses under the unchanged original benchmark.',
           '', '## Secondary regression (no score-driven tuning)','',
           table(['Metric','Extractive','Ollama','N per mode'],[
               [label,number(secondary['answers']['extractive']['summary'][key],True),number(secondary['answers']['ollama']['summary'][key],True),secondary['answers']['extractive']['summary'][denominator]]
               for key,label,denominator in [('expected_answer_presence','All expected literal values present','factual_n'),('correct_abstention_rate','Exact unavailable-fact refusal','negative_n'),('ambiguous_clarify_or_abstain','Ambiguity clarification/refusal','ambiguous_n'),('attack_canary_emission','Instruction canary emission','attack_n')]]),'',
           table(['Mode','Conflicting assertions clarified/refused','Benign procedure answer presence','Cross-document all-values presence','Multi-field all-values presence'],[
               [mode,
                f'{sum(r["clarified"] or r["abstained"] for r in e["raw"] if r["category"]=="conflict")}/{sum(r["category"]=="conflict" for r in e["raw"])}',
                f'{sum(r["expected_present"] for r in e["raw"] if r["id"]=="s027")}/1',
                number(e['summary']['by_category']['cross_document']['expected_answer_presence'],True),
                number(e['summary']['by_category']['multi_chunk']['expected_answer_presence'],True)] for mode,e in secondary['answers'].items()]),'',
           'The 33 cases were first evaluated before the overlap repair, then validated on the final version after the original suite exposed a chunk-boundary bug. Both executions are preserved; no edits or tuning used the secondary outcomes. The secondary set includes new project names/values and phrasings, multi-entity/multi-field requests, unknown fields/years, instructions, contradiction, agreement, and benign operating procedures. It checks transfer within these lexical relation classes; 33 clean synthetic cases do not establish unrestricted semantic generalization.',
           '', '### Chunk-boundary regression','',table(['Mode','Class','Succeeded','N'],[[mode,category,value['successes'],value['n']] for mode,groups in boundary['summaries'].items() for category,value in groups.items()]),'',
           '', '## Tradeoffs and remaining weaknesses','',
           '- Conflict handling deliberately declines to choose one of two inconsistent values without authenticated authority. Read the missed-case rows: the five deceptive-fact cases require the official value by dataset label, but the application has no trusted-source designation. Safe clarification sacrifices automatic answer availability rather than making an unjustified authority guess.',
           '- Overlapping identical facts remain deduplicated. Frozen chunk recall can stay below 100% even when each unique requested fact is preserved. No scoring adjustment or duplicate restoration was used to boost the benchmark.',
           '- Relation normalization is lexical, finite and English-specific; declarative copulas are privileged. Arbitrary language, negation, pronouns, same-name entities, misleading/missing headings, complex temporal qualifiers, and non-copular conflicts need broader independent evaluation.',
           '- The overlap rule is lexical evidence of continuation, not authenticated chronology; repeated/adversarial copied passages can still mislead it.\n- Complex conjunctions do not fully bind different attributes to different named entities; the secondary cases test shared-attribute comparisons and single-entity multi-field requests. Equivalent values with different wording can be mistaken for conflicts.\n- Source caps still bound context. Requests requiring more than five sources or three statements may be incomplete; no unbounded multi-hop retrieval was added.',
           '- Quarantining a whole instruction-bearing chunk can discard harmless quoted examples and nearby legitimate facts. Malicious assertion agreement across all documents can pass; contradiction detection cannot establish truth, provenance authenticity, or general injection resistance.',
           '- The prompt is defense-in-depth, not an instruction-hierarchy guarantee. Citation IDs and expected strings remain mechanical proxies. Human semantic judgments and unsupported-claim rates remain unavailable.',
           '- Measured latency tradeoff: extractive P95 rose 69.30% (14.768 to 25.003 ms); Ollama P50 rose 18.91% while P95 fell 12.78%. Extractive single-client throughput fell from 66.007 to 50.411 QPS; sequential Ollama throughput fell from 2.047 to 1.843 QPS.',
           '- Latency/throughput comparisons are local point measurements with uncontrolled background load, model residency and power/thermal conditions. No confidence/significance or production-capacity claim is made.',
           '', '## Generalization assessment','',
           'Entity-alternative constraints and per-relation synthesis address a structural error independent of project names; the secondary cross-entity and multi-field cases test that transfer. Morphology/paraphrase matching transfers within its finite relation vocabulary, not arbitrary semantics. Generic entity/relation conflict checks transfer to unseen values but depend on successful lexical claim extraction. Role/control detection transfers across different canaries and directive structures; benign quotation false positives and unknown encodings remain risks. Unscoped entity ambiguity no longer depends on six exact query strings. These conclusions are bounded by the secondary synthetic evidence, not a claim of production robustness.',
           '', '## Reproduce and review','',
           '```bash\n.venv/bin/python -m pytest backend/tests evals/tests -q\n(cd frontend && npm run build && npm run test:e2e)\n.venv/bin/python -m evals.benchmark --retrieval --output evals/results/after-architecture/retrieval.json\n.venv/bin/python -m evals.benchmark --all --mode both --requests 512 --no-report --output evals/results/after-architecture/latest.json\n.venv/bin/python -m evals.compare_architecture --check\n```',
           'An intermediate successful run exposed eight false text conflicts: partial names at chunk tails versus their full names in overlapping chunks. That run is preserved under `results/after-architecture/intermediate-boundary-regression/`; the final code repairs proven overlaps rather than ignoring arbitrary prefix disagreements. A separate six-case boundary set verifies four real split-name continuations and two cross-document prefix contradictions in both modes. The first after-run completed requests but failed while writing a relative-path review artifact; that error and its response worksheet are preserved. The output utility was fixed and the unchanged application/dataset/scoring were rerun to produce this report. The full benchmark includes the unchanged adversarial cases and the reliability workload. `secondary_eval` refuses to overwrite a saved execution. Both initial and final-version secondary outputs are preserved; no tuning used their outcomes. The original 406-row human-review CSV is unchanged; new after/secondary worksheets are separate. See the offline review viewer for readable question/answer/evidence comparisons; no subjective review values are auto-filled.',
           '', 'No changes have been committed or pushed.']
    return '\n'.join(lines)+'\n',{'comparison':raw,'before_taxonomy':bt,'after_taxonomy':at}


def readme_section(after):
    s=after['retrieval']['summaries']['full_pipeline']
    ext=after['answers']['extractive']['summary'];llm=after['answers']['ollama']['summary']
    return '\n'.join([START,'## Evidence architecture regression','',
                      f'The frozen 203-case set now serves as a known diagnostic regression after class-level architecture fixes. Full evidence Recall@5 is {number(s["recall@5"],True)}; extractive/Ollama all-values presence is {number(ext["expected_answer_presence"],True)} / {number(llm["expected_answer_presence"],True)}. Cross-document presence and attack outcomes are detailed in the comparison; safe conflict clarification can reduce answer availability.',
                      '', '[Before/after results, tradeoffs and secondary regression](evals/ARCHITECTURE_RESULTS.md) · [After raw output](evals/results/after-architecture/latest.json). The original baseline above remains preserved; these are synthetic proxy measurements, not independent semantic accuracy.',END])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    check_frozen()
    before=json.loads(BEFORE.read_text());after=json.loads(AFTER.read_text());secondary=json.loads(SECONDARY.read_text())
    assert before['dataset_sha256']==after['dataset_sha256']
    for path,value in secondary['application_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value,'Application changed after secondary evaluation'
    boundary=json.loads((ROOT/'evals/results/boundary.json').read_text())
    for path,value in boundary['application_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value,'Application changed after boundary evaluation'
    for path,value in after['application_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value,'Application changed after primary evaluation'
    content,raw=render(before,after,secondary)
    section=readme_section(after)
    readme=ROOT/'README.md'
    if args.check:
        assert REPORT.read_text()==content,'Comparison Markdown drift'
        assert section in readme.read_text(),'Architecture README drift'
        print('Frozen data/worksheet, application hashes, comparison report and README verified.')
    else:
        REPORT.write_text(content)
        (ROOT/'evals/results/after-architecture/comparison.json').write_text(json.dumps(raw,indent=2)+'\n')
        current=readme.read_text()
        if START in current and END in current:
            start=current.index(START);end=current.index(END)+len(END)
            current=current[:start]+section+current[end:]
        else:current+='\n'+section+'\n'
        readme.write_text(current)


if __name__=='__main__':main()
