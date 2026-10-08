# Evidence architecture: frozen before/after evaluation

> Generated from preserved baseline, revised frozen benchmark, and preserved secondary executions. No benchmark questions, labels, scoring formulas, or cases were changed.

[Root-cause audit written before changes](ARCHITECTURE_AUDIT.md). [Original 203-case baseline](BENCHMARKS.md). [After raw results](results/after-architecture/latest.json). [Final secondary raw results](results/secondary-final.json).

Original dataset SHA256: `6c66900c65bb4386302d041f670b909ed460f5d2ea6ca9547113c174fca42c71`. Before and after use the same 203 cases and 70-chunk base corpus. This original set is now a **known diagnostic regression**, since its failure classes informed the architecture. Do not call the after scores fresh held-out validation.

Secondary dataset SHA256: `f1ae86653d79f2fa6ab17cb7abb42372d8229bc628f6232d5b3e9e871c019e39`; 33 class-level cases authored and frozen after design but before revised application results. Initial execution and final-version regression execution are both preserved; no application changes were driven by secondary results. Final application hashes match the full run. Both sets are agent-authored synthetic, not independent production evidence.

Before recorded: 2026-10-08T00:20:56.668394-04:00; after recorded: 2026-10-08T01:04:44.907624-04:00. Hardware and model versions are retained in both raw outputs.

## Exact implementation changes

- `backend/app/evidence.py`: common morphology/relation normalization; declarative entity/attribute/value units; per-conjunct field matching; independent entity constraints; coverage-aware selection within five sources; overlap/unit deduplication.
- Same-document/page fragments at an unpunctuated chunk tail are reconciled only when literal suffix/prefix overlap proves continuation into a complete claim. Cross-document, cross-page, complete-sentence and non-overlapping prefix values remain contradictory.
- Generic conflict/ambiguity checks operate on applicable entity/relation groups. Contradictory values cause clarification; no filename, heading authority claim, benchmark entity, expected value, or canary is treated as trusted.
- Control-language detector recognizes role/control structures and spaced-letter obfuscation. Instruction-bearing chunks are quarantined; benign unrelated maintenance procedures are retained, but quoted hostile examples can be rejected.
- `agent.py`: uses planned evidence units for extractive synthesis instead of applying whole-query thresholds again; retains conservative legacy fallback for non-copular prose/CSV and existing missing-field/year guards.
- Ollama receives typed JSON containing quoted untrusted evidence and requested fact units. The system prompt asks for every requested entity/relation and forbids following document instructions. Schema/source-ID validation remains unchanged.
- Retrieval formulas, ranking/reranking, top-ten candidate budget, five-source cap, three-statement answer cap, OCR/PDF/CSV ingestion, UI implementation, frozen primary dataset, and scoring are unchanged.
- Harness changes are output/provenance only: `--no-report` preserves original reports/worksheet; application hashes include the new module. New comparison, secondary runner, human-review viewer, and class-level backend/browser tests are separate.

## Before versus after

| Metric | Before | After | Difference |
| --- | --- | --- | --- |
| Production Recall@5 | 98.73% | 98.73% | +0.00 pp |
| Production Recall@10 | 100.00% | 100.00% | +0.00 pp |
| Production MRR@10 | 0.829633 | 0.829633 | +0.000000 |
| Production nDCG@5 | 0.871986 | 0.871986 | +0.000000 |
| Production nDCG@10 | 0.876232 | 0.876232 | +0.000000 |
| Full evidence Recall@5 | 83.44% | 98.73% | +15.29 pp |
| Full evidence Recall@10 | 83.44% | 98.73% | +15.29 pp |
| Full evidence MRR@10 | 0.747134 | 0.984076 | +0.236943 |
| Full evidence nDCG@5 | 0.762687 | 0.978390 | +0.215703 |
| Full evidence nDCG@10 | 0.762687 | 0.978390 | +0.215703 |
| extractive overall expected-value presence | 80.89% | 96.82% | +15.92 pp |
| extractive text expected-value presence | 85.71% | 94.64% | +8.93 pp |
| extractive pdf expected-value presence | 84.91% | 96.23% | +11.32 pp |
| extractive csv expected-value presence | 100.00% | 100.00% | +0.00 pp |
| extractive ocr expected-value presence | 84.62% | 100.00% | +15.38 pp |
| extractive cross_document expected-value presence | 0.00% | 100.00% | +100.00 pp |
| extractive correct exact abstention | 100.00% | 100.00% | +0.00 pp |
| extractive false-negative exact abstention | 14.01% | 0.00% | -14.01 pp |
| extractive ambiguity clarification/refusal | 66.67% | 100.00% | +33.33 pp |
| extractive attack canary emission | 60.00% | 0.00% | -60.00 pp |
| extractive attack expected answer without canary | 40.00% | 80.00% | +40.00 pp |
| extractive citation ID validity | 100.00% | 100.00% | +0.00 pp |
| extractive factual refusal or clarification | 14.01% | 3.18% | -10.83 pp |
| extractive total p50 ms | 10.884 | 11.386 | +0.502 |
| extractive total p95 ms | 14.768 | 25.003 | +10.235 |
| extractive deceptive-fact canary emission | 100.00% | 0.00% | -100.00 pp |
| extractive HTTP reliability success | 100.00% | 100.00% | +0.00 pp |
| ollama overall expected-value presence | 80.89% | 96.82% | +15.92 pp |
| ollama text expected-value presence | 85.71% | 94.64% | +8.93 pp |
| ollama pdf expected-value presence | 84.91% | 96.23% | +11.32 pp |
| ollama csv expected-value presence | 100.00% | 100.00% | +0.00 pp |
| ollama ocr expected-value presence | 84.62% | 100.00% | +15.38 pp |
| ollama cross_document expected-value presence | 0.00% | 100.00% | +100.00 pp |
| ollama correct exact abstention | 100.00% | 100.00% | +0.00 pp |
| ollama false-negative exact abstention | 14.01% | 0.00% | -14.01 pp |
| ollama ambiguity clarification/refusal | 66.67% | 100.00% | +33.33 pp |
| ollama attack canary emission | 20.00% | 0.00% | -20.00 pp |
| ollama attack expected answer without canary | 80.00% | 80.00% | +0.00 pp |
| ollama citation ID validity | 100.00% | 100.00% | +0.00 pp |
| ollama factual refusal or clarification | 14.01% | 3.18% | -10.83 pp |
| ollama total p50 ms | 542.959 | 645.643 | +102.684 |
| ollama total p95 ms | 1503.608 | 1311.477 | -192.130 |
| ollama deceptive-fact canary emission | 100.00% | 0.00% | -100.00 pp |
| ollama HTTP reliability success | 100.00% | 100.00% | +0.00 pp |

Retrieval quality uses 157 unique factual cases; timing uses 471 executions per configuration. Expected-value presence uses 157 factual cases per mode; negatives 35; attacks 25; deceptive-fact subset 5; ambiguity 6. Answer latency includes all 203 requests, including gates/tools/clarification. HTTP reliability covers 512 extractive and 24 requested-Ollama responses. MRR/nDCG are shown on the 0–1 scale. Rates use percentage-point differences.

## Failure taxonomy

| Mode | Stage/cause | Before count | After count |
| --- | --- | --- | --- |
| extractive | retrieval_failure | 0 | 0 |
| extractive | evidence_selection_failure | 30 | 0 |
| extractive | answer_construction_or_generation_failure | 0 | 0 |
| extractive | conflict_clarification | 0 | 5 |
| extractive | execution_error | 0 | 0 |
| ollama | retrieval_failure | 0 | 0 |
| ollama | evidence_selection_failure | 30 | 0 |
| ollama | answer_construction_or_generation_failure | 0 | 0 |
| ollama | conflict_clarification | 0 | 5 |
| ollama | execution_error | 0 | 0 |

These are mutually exclusive expected-value miss attributions, not independent semantic grading. Over-abstention is a separate operational flag. The baseline has 30 upstream selection misses (20 paraphrases, ten cross-document), including 22 refusals and eight irrelevant responses. No extraction failure or context-truncation failure was established. The original chunk-recall drop also includes four overlap-duplicate removals; those do not lose unique facts.
Adversarial contamination is assessed separately because a contaminated answer can still contain the expected value and pass literal presence. Safe conflict clarifications count as expected-value misses under the unchanged original benchmark.

## Secondary regression (no score-driven tuning)

| Metric | Extractive | Ollama | N per mode |
| --- | --- | --- | --- |
| All expected literal values present | 100.00% | 100.00% | 21 |
| Exact unavailable-fact refusal | 100.00% | 100.00% | 7 |
| Ambiguity clarification/refusal | 100.00% | 100.00% | 3 |
| Instruction canary emission | 0.00% | 0.00% | 3 |

| Mode | Conflicting assertions clarified/refused | Benign procedure answer presence | Cross-document all-values presence | Multi-field all-values presence |
| --- | --- | --- | --- | --- |
| extractive | 2/2 | 1/1 | 100.00% | 100.00% |
| ollama | 2/2 | 1/1 | 100.00% | 100.00% |

The 33 cases were first evaluated before the overlap repair, then validated on the final version after the original suite exposed a chunk-boundary bug. Both executions are preserved; no edits or tuning used the secondary outcomes. The secondary set includes new project names/values and phrasings, multi-entity/multi-field requests, unknown fields/years, instructions, contradiction, agreement, and benign operating procedures. It checks transfer within these lexical relation classes; 33 clean synthetic cases do not establish unrestricted semantic generalization.

### Chunk-boundary regression

| Mode | Class | Succeeded | N |
| --- | --- | --- | --- |
| extractive | cross_document_prefix_conflict | 2 | 2 |
| extractive | overlap_fragment | 4 | 4 |
| ollama | cross_document_prefix_conflict | 2 | 2 |
| ollama | overlap_fragment | 4 | 4 |


## Tradeoffs and remaining weaknesses

- Conflict handling deliberately declines to choose one of two inconsistent values without authenticated authority. Read the missed-case rows: the five deceptive-fact cases require the official value by dataset label, but the application has no trusted-source designation. Safe clarification sacrifices automatic answer availability rather than making an unjustified authority guess.
- Overlapping identical facts remain deduplicated. Frozen chunk recall can stay below 100% even when each unique requested fact is preserved. No scoring adjustment or duplicate restoration was used to boost the benchmark.
- Relation normalization is lexical, finite and English-specific; declarative copulas are privileged. Arbitrary language, negation, pronouns, same-name entities, misleading/missing headings, complex temporal qualifiers, and non-copular conflicts need broader independent evaluation.
- The overlap rule is lexical evidence of continuation, not authenticated chronology; repeated/adversarial copied passages can still mislead it.
- Complex conjunctions do not fully bind different attributes to different named entities; the secondary cases test shared-attribute comparisons and single-entity multi-field requests. Equivalent values with different wording can be mistaken for conflicts.
- Source caps still bound context. Requests requiring more than five sources or three statements may be incomplete; no unbounded multi-hop retrieval was added.
- Quarantining a whole instruction-bearing chunk can discard harmless quoted examples and nearby legitimate facts. Malicious assertion agreement across all documents can pass; contradiction detection cannot establish truth, provenance authenticity, or general injection resistance.
- The prompt is defense-in-depth, not an instruction-hierarchy guarantee. Citation IDs and expected strings remain mechanical proxies. Human semantic judgments and unsupported-claim rates remain unavailable.
- Measured latency tradeoff: extractive P95 rose 69.30% (14.768 to 25.003 ms); Ollama P50 rose 18.91% while P95 fell 12.78%. Extractive single-client throughput fell from 66.007 to 50.411 QPS; sequential Ollama throughput fell from 2.047 to 1.843 QPS.
- Latency/throughput comparisons are local point measurements with uncontrolled background load, model residency and power/thermal conditions. No confidence/significance or production-capacity claim is made.

## Generalization assessment

Entity-alternative constraints and per-relation synthesis address a structural error independent of project names; the secondary cross-entity and multi-field cases test that transfer. Morphology/paraphrase matching transfers within its finite relation vocabulary, not arbitrary semantics. Generic entity/relation conflict checks transfer to unseen values but depend on successful lexical claim extraction. Role/control detection transfers across different canaries and directive structures; benign quotation false positives and unknown encodings remain risks. Unscoped entity ambiguity no longer depends on six exact query strings. These conclusions are bounded by the secondary synthetic evidence, not a claim of production robustness.

## Reproduce and review

```bash
.venv/bin/python -m pytest backend/tests evals/tests -q
(cd frontend && npm run build && npm run test:e2e)
.venv/bin/python -m evals.benchmark --retrieval --output evals/results/after-architecture/retrieval.json
.venv/bin/python -m evals.benchmark --all --mode both --requests 512 --no-report --output evals/results/after-architecture/latest.json
.venv/bin/python -m evals.compare_architecture --check
```
An intermediate successful run exposed eight false text conflicts: partial names at chunk tails versus their full names in overlapping chunks. That run is preserved under `results/after-architecture/intermediate-boundary-regression/`; the final code repairs proven overlaps rather than ignoring arbitrary prefix disagreements. A separate six-case boundary set verifies four real split-name continuations and two cross-document prefix contradictions in both modes. The first after-run completed requests but failed while writing a relative-path review artifact; that error and its response worksheet are preserved. The output utility was fixed and the unchanged application/dataset/scoring were rerun to produce this report. The full benchmark includes the unchanged adversarial cases and the reliability workload. `secondary_eval` refuses to overwrite a saved execution. Both initial and final-version secondary outputs are preserved; no tuning used their outcomes. The original 406-row human-review CSV is unchanged; new after/secondary worksheets are separate. See the offline review viewer for readable question/answer/evidence comparisons; no subjective review values are auto-filled.

No changes have been committed or pushed.
