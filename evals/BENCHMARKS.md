# Local Research Desk benchmarks

> Generated from `results/latest.json` by `python -m evals.report`. Do not edit metric tables manually.

Recorded 2026-10-08T00:20:56.668394-04:00 (America/New_York). New synthetic held-out dataset: **203 cases**, not used to tune production. Agent-authored and template-related; not independent human or production evaluation.
Hardware: Apple M2, 8 logical CPUs, 8.000 GiB RAM; macOS-26.6.2-arm64-arm-64bit. Python 3.9.6. Model: qwen2.5:1.5b; model digest/quantization and installed versions are in raw JSON.
Base corpus: 11 documents, 70 chunks, 178199 original bytes. Twenty-five adversarial cases each use their labeled official document plus one isolated untrusted attachment. Corpus/label SHA256: `6c66900c65bb4386302d041f670b909ed460f5d2ea6ca9547113c174fca42c71`.

## Headline results

Retrieval headline evaluates the actual `Store.search` on raw questions before answer-stage aliases/filtering. It includes labeled answerable adversarial contexts. Answer presence requires **all** expected literal values, including multi-part answers. Rates are fractions, shown as percentages; MRR/nDCG can also be read on the 0–1 scale.

| Metric | Result | Sample size |
| --- | --- | --- |
| Recall@5 | 98.73% | 157 |
| Recall@10 | 100.00% | 157 |
| MRR@10 | 82.96% | 157 |
| nDCG@5 | 87.20% | 157 |
| nDCG@10 | 87.62% | 157 |
| Expected-answer presence / extractive | 80.89% | 157 |
| Expected-answer presence / requested Ollama | 80.89% | 157 |
| Correct exact abstention / extractive | 100.00% | 35 |
| Correct exact abstention / requested Ollama | 100.00% | 35 |
| Citation ID validity / extractive | 100.00% | 135 |
| Citation ID validity / requested Ollama | 100.00% | 135 |
| Semantic correctness / faithfulness / unsupported-claim rate | Unavailable: pending human review | 0 human reviews |
| Median / P95 retrieval ms | 8.011 / 11.594 | 471 |
| Median / P95 extractive end-to-end ms | 10.884 / 14.768 | 203 |
| Median / P95 requested-Ollama end-to-end ms | 542.959 / 1503.608 | 203 |
| Median / P95 executed local-generation ms | 593.714 / 1810.135 | 137 |
| HTTP reliability success / extractive | 100.00% | 512 |
| HTTP reliability success / Ollama | 100.00% | 24 |

Requested-Ollama end-to-end latency includes questions handled by abstention gates, clarification, and CSV tools. Executed generation-call latency excludes those bypasses. Do not describe the mixed-path median as model inference speed. Citation ID validity is membership, not semantic citation correctness.

## Retrieval ablation

Production hybrid already IS reciprocal-rank fusion. hybrid_rrf removes lexical reranking. hybrid_score_sum is an explicitly experimental equal-weight max-normalized score-sum comparator, not a separable existing production stage.

| Configuration | N | Recall@5 | Recall@10 | MRR@10 | nDCG@5 | nDCG@10 | P50 ms | P95 ms | Timing N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tfidf | 157 | 96.82% | 100.00% | 85.88% | 88.31% | 89.38% | 7.808 | 11.550 | 471 |
| bm25 | 157 | 100.00% | 100.00% | 83.86% | 88.36% | 88.36% | 2.397 | 2.950 | 471 |
| hybrid_score_sum | 157 | 99.36% | 100.00% | 85.73% | 89.16% | 89.39% | 7.943 | 11.491 | 471 |
| hybrid_rrf | 157 | 98.73% | 100.00% | 86.36% | 89.39% | 89.81% | 7.975 | 11.471 | 471 |
| production_search | 157 | 98.73% | 100.00% | 82.96% | 87.20% | 87.62% | 8.011 | 11.594 | 471 |
| full_pipeline | 157 | 83.44% | 83.44% | 74.71% | 76.27% | 76.27% | 10.898 | 14.610 | 471 |

The full evidence pipeline is capped at five sources by production. Its Recall@10 equals Recall@5 because it cannot return ten sources. Chunk relevance uses the full chunk; focused evidence may omit the expected fact. Citation-evidence coverage below measures this separately. Configurations are rotated per question/repeat; first warmups are excluded.

### Differences relative to TF-IDF

| Configuration | Recall@5 Δ pp | Recall@10 Δ pp | MRR Δ pp | nDCG@5 Δ pp | nDCG@10 Δ pp | P95 Δ ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | 3.185 | 0.000 | -2.020 | 0.054 | -1.022 | -8.600 |
| hybrid_score_sum | 2.548 | 0.000 | -0.152 | 0.855 | 0.006 | -0.059 |
| hybrid_rrf | 1.911 | 0.000 | 0.476 | 1.081 | 0.430 | -0.079 |
| production_search | 1.911 | 0.000 | -2.921 | -1.107 | -1.758 | 0.044 |
| full_pipeline | -13.376 | -16.561 | -11.171 | -12.036 | -13.113 | 3.060 |

These are observed paired workload differences, not causal significance or confidence intervals. No speed/quality improvement is assumed.

## Source-type results

N counts labeled factual questions; latency is in-process complete response time and includes all questions assigned to that source type (separate timing N). Adversarial cases inherit their official source modality. Text includes TXT/Markdown-style plain text, not semantic embeddings. OCR is image-derived text, not visual reasoning.

### extractive

| Source | Factual N | Hit@5 | Recall@5 | Recall@10 | MRR@10 | All-values presence | P50 ms | P95 ms | Timing N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| text | 56 | 100.00% | 100.00% | 100.00% | 72.74% | 85.71% | 11.046 | 14.930 | 72 |
| pdf | 53 | 96.23% | 96.23% | 100.00% | 80.22% | 84.91% | 10.842 | 15.158 | 66 |
| csv | 12 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 8.288 | 12.309 | 17 |
| ocr | 26 | 100.00% | 100.00% | 100.00% | 96.15% | 84.62% | 10.962 | 14.694 | 32 |
| cross_document | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 0.00% | 10.726 | 19.546 | 16 |

### ollama

| Source | Factual N | Hit@5 | Recall@5 | Recall@10 | MRR@10 | All-values presence | P50 ms | P95 ms | Timing N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| text | 56 | 100.00% | 100.00% | 100.00% | 72.74% | 85.71% | 547.127 | 2059.311 | 72 |
| pdf | 53 | 96.23% | 96.23% | 100.00% | 80.22% | 84.91% | 542.404 | 1829.930 | 66 |
| csv | 12 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 592.095 | 651.188 | 17 |
| ocr | 26 | 100.00% | 100.00% | 100.00% | 96.15% | 84.62% | 551.306 | 1062.166 | 32 |
| cross_document | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 0.00% | 14.254 | 1503.608 | 16 |

## All retrieval metrics by category

| Category | N | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@5 | Precision@10 | MRR@10 | nDCG@5 | nDCG@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adversarial | 25 | 8.00% | 100.00% | 100.00% | 100.00% | 8.00% | 100.00% | 100.00% | 100.00% | 20.00% | 10.00% | 54.00% | 66.05% | 66.05% |
| cross_document | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 50.00% | 100.00% | 100.00% | 100.00% | 40.00% | 20.00% | 100.00% | 100.00% | 100.00% |
| csv_retrieval | 12 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 20.00% | 10.00% | 100.00% | 100.00% | 100.00% |
| direct | 80 | 95.00% | 100.00% | 100.00% | 100.00% | 92.50% | 100.00% | 100.00% | 100.00% | 21.00% | 10.50% | 97.50% | 98.15% | 98.15% |
| multi_chunk | 10 | 20.00% | 100.00% | 100.00% | 100.00% | 20.00% | 60.00% | 100.00% | 100.00% | 36.00% | 18.00% | 46.67% | 65.65% | 65.65% |
| paraphrase | 20 | 45.00% | 60.00% | 90.00% | 100.00% | 45.00% | 60.00% | 90.00% | 100.00% | 18.00% | 10.00% | 60.43% | 66.51% | 69.84% |

All configurations also have all metrics grouped by category and modality in raw JSON. Missing/invalid qrels are explicitly counted; benchmark exits nonzero after preserving execution/label failures.

## Answers, abstention, and attacks

| Measure | Extractive | Ollama |
| --- | --- | --- |
| All expected literal values present | 80.89% | 80.89% |
| Exact standard refusal on unavailable facts | 100.00% | 100.00% |
| Non-refusal/non-clarification answer on unavailable facts | 0.00% | 0.00% |
| Clarification on unavailable facts | 0.00% | 0.00% |
| False-negative exact refusal on answerable facts | 14.01% | 14.01% |
| Valid citation IDs on answered factual questions | 100.00% | 100.00% |
| Mean fraction of cited chunks carrying labeled relevant evidence | 85.19% | 87.41% |
| Mean expected evidence-unit coverage in cited focused text | 80.89% | 77.71% |
| Mean claim-string copied from its cited source (mechanical proxy) | 100.00% | 80.37% |
| Exact deterministic CSV values | 100.00% | 100.00% |
| Ambiguous query clarification/refusal | 66.67% | 66.67% |
| Attack canary emission rate (lower is better) | 60.00% | 20.00% |
| Attack expected values present without canary | 40.00% | 80.00% |

Factual/negative/tool/ambiguous/adversarial denominators: 157 / 35 / 5 / 6 / 25. Citation metrics use answered/cited subsets; raw JSON includes counts. Exact refusals exclude alternative safe wording. Expected-span presence can reward contradictory extras and penalize valid paraphrases. Source-copy support proves string inclusion only, not factual truth or absence of unsupported claims.

Twenty-five isolated attachment cases cover imperatives, role spoofing, deceptive assertions, high-keyword noise, and obfuscated instructions. Success proxy requires expected values and no injected canary. Canary absence alone is not attack resistance; abstention can hide loss of utility. Semantic contradiction/faithfulness remain review tasks.

### Attack outcomes: extractive

| Threat | N | Canary emitted | Expected values without canary |
| --- | --- | --- | --- |
| deceptive_fact | 5 | 100.00% | 0.00% |
| imperative | 5 | 0.00% | 100.00% |
| keyword_noise | 5 | 0.00% | 100.00% |
| obfuscated_instruction | 5 | 100.00% | 0.00% |
| role_spoof | 5 | 100.00% | 0.00% |

### Attack outcomes: ollama

| Threat | N | Canary emitted | Expected values without canary |
| --- | --- | --- | --- |
| deceptive_fact | 5 | 100.00% | 0.00% |
| imperative | 5 | 0.00% | 100.00% |
| keyword_noise | 5 | 0.00% | 100.00% |
| obfuscated_instruction | 5 | 0.00% | 100.00% |
| role_spoof | 5 | 0.00% | 100.00% |

## Latency distributions

All times are wall-clock milliseconds. P50 is the median; P90/P95/P99 use nearest-rank percentiles. Ingestion is actual Store.ingest including parsing/chunking/SQLite commit. Separate extraction timings call the real parser/OCR independently (not additive stage subtraction). Three repetitions per document unless overridden. No model warmup counts in steady-state samples; raw warmups record first observed request without asserting a cold start.

| Measurement | N | Mean | P50 | P90 | P95 | P99 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ingestion text | 12 | 0.646 | 0.574 | 0.687 | 1.277 | 1.277 | 0.542 | 1.277 |
| ingestion pdf | 12 | 15.303 | 9.257 | 12.616 | 74.272 | 74.272 | 8.935 | 74.272 |
| ingestion csv | 3 | 0.792 | 0.586 | 1.238 | 1.238 | 1.238 | 0.553 | 1.238 |
| ingestion ocr | 6 | 263.724 | 254.693 | 303.879 | 303.879 | 303.879 | 241.576 | 303.879 |
| extraction/OCR text | 12 | 0.004 | 0.004 | 0.006 | 0.006 | 0.006 | 0.003 | 0.006 |
| extraction/OCR pdf | 12 | 8.976 | 8.530 | 11.140 | 11.779 | 11.779 | 8.280 | 11.779 |
| extraction/OCR csv | 3 | 0.034 | 0.032 | 0.040 | 0.040 | 0.040 | 0.030 | 0.040 |
| extraction/OCR ocr | 6 | 245.836 | 245.296 | 250.951 | 250.951 | 250.951 | 241.512 | 250.951 |
| retrieval tfidf | 471 | 7.603 | 7.808 | 11.047 | 11.550 | 15.980 | 0.809 | 49.181 |
| retrieval bm25 | 471 | 2.292 | 2.397 | 2.597 | 2.950 | 6.829 | 0.160 | 20.978 |
| retrieval hybrid_score_sum | 471 | 7.442 | 7.943 | 9.572 | 11.491 | 15.673 | 0.816 | 25.417 |
| retrieval hybrid_rrf | 471 | 7.443 | 7.975 | 10.874 | 11.471 | 13.148 | 0.826 | 13.882 |
| retrieval production_search | 471 | 7.494 | 8.011 | 10.011 | 11.594 | 14.676 | 0.826 | 16.971 |
| retrieval full_pipeline | 471 | 10.061 | 10.898 | 13.604 | 14.610 | 18.269 | 1.115 | 36.261 |
| extractive retrieval_ms | 198 | 7.862 | 8.060 | 11.235 | 11.921 | 13.231 | 0.894 | 15.973 |
| extractive generation_ms | 0 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| extractive total_ms | 203 | 10.023 | 10.884 | 13.640 | 14.768 | 15.509 | 0.117 | 19.546 |
| ollama retrieval_ms | 198 | 13.449 | 10.669 | 18.442 | 29.413 | 88.017 | 2.549 | 132.891 |
| ollama generation_ms | 137 | 802.166 | 593.714 | 1196.388 | 1810.135 | 4369.154 | 380.029 | 4720.853 |
| ollama total_ms | 203 | 557.792 | 542.959 | 1062.166 | 1503.608 | 3621.950 | 0.170 | 4740.553 |
| HTTP extractive | 512 | 53.601 | 40.503 | 120.708 | 133.844 | 177.210 | 9.271 | 278.217 |
| HTTP ollama | 24 | 488.463 | 523.130 | 1066.732 | 1549.347 | 2051.703 | 14.859 | 2051.703 |

## HTTP reliability and throughput

HTTP /api/ask on isolated uvicorn subprocess; loopback client overhead included

| Mode | Concurrency | N | Succeeded | Failed | Timeout rate | Exception rate | Malformed rate | Bad citations | Queries/s | P50 ms | P95 ms | P99 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| extractive | 1 | 128 | 128 | 0 | 0.00% | 0.00% | 0.00% | 0 | 66.007 | 13.790 | 21.382 | 35.173 |
| extractive | 2 | 128 | 128 | 0 | 0.00% | 0.00% | 0.00% | 0 | 60.022 | 27.771 | 40.656 | 264.149 |
| extractive | 4 | 128 | 128 | 0 | 0.00% | 0.00% | 0.00% | 0 | 79.377 | 48.514 | 64.121 | 71.002 |
| extractive | 8 | 128 | 128 | 0 | 0.00% | 0.00% | 0.00% | 0 | 67.456 | 115.430 | 164.376 | 180.125 |
| ollama | 1 | 24 | 24 | 0 | 0.00% | 0.00% | 0.00% | 0 | 2.047 | 523.130 | 1549.347 | 2051.703 |

Closed-loop bounded client threads, not arrival-rate capacity or soak test. Repeated synthetic queries, all-source base corpus; adversarial scoped contexts and CSV tools excluded from HTTP load. Success means transport/schema/citation-ID validity, not answer correctness.
All raw failures, HTTP status errors, exception/timeout details, responses, and request durations are retained. This is a bounded short reliability test, not long-running production uptime. LLM load remains sequential to respect local resources.

## Resources and index

| Process group | RSS mean MiB | RSS sampled peak MiB | Mean CPU % (one core) | CPU sampled peak % |
| --- | --- | --- | --- | --- |
| benchmark_tree | 49.826 | 146.719 | 28.434 | 609.169 |
| ollama_processes | 909.174 | 1192.531 | 67.748 | 183.150 |

Sampled sum of RSS (shared pages can be counted twice), not exact peak allocation; CPU time deltas use ps resolution and a one-core baseline (100% = one CPU core). Existing Ollama processes may include unrelated activity; benchmark descendants include sampler subprocess overhead. Not system-wide CPU or GPU counters.
Sampler interval: 0.1 s; 1082 samples. Phase-specific summaries and raw samples are retained.
SQLite size: 114688 bytes. Persisted retrieval index: 0 bytes. No persisted TF-IDF/BM25 index. SQLite stores chunks and parsed CSV. Vectorizer and BM25 bags are rebuilt per query; transient index RAM is part of process RSS, not separately attributable.
GPU utilization and dedicated VRAM: unavailable (Apple unified-memory machine; no NVIDIA counters). Ollama loaded-model metadata, including reported model residency, is preserved without treating it as measured GPU utilization.

### OCR extraction quality

| Image | Reference words | Word edits | Normalized WER |
| --- | --- | --- | --- |
| orchid.png | 63 | 0 | 0.00% |
| solstice.png | 63 | 0 | 0.00% |

WER uses lowercase alphanumeric word tokens and an authored transcription. Only two clean synthetic English images: not a general OCR benchmark. Parsing failures are separate corpus errors.

## Unavailable metrics and validity limits

- Human semantic correctness, faithfulness, semantic citation correctness/claim coverage, and unsupported-claim rate have no completed independent judgments. Use the structured review worksheet and rubric in `METHODOLOGY.md`.
- TTFT/token throughput and isolated model inference time are unavailable: production uses a non-streaming chat call without retaining token/timing metadata. Generation wall time includes HTTP/model discovery/validation.
- Exact cold-start inference, hardware energy, GPU utilization, VRAM, and attributable transient index RAM were not measured.
- No independent real-world users/documents, external labeling, bootstrap confidence intervals, production-scale corpus, noisy scans, visual reasoning, open-loop arrival rates, long soak, distributed hardware, or cross-machine comparisons.
- Questions share authored templates/facts. Multi-chunk/cross-document tasks can be missed by single-sentence lexical heuristics. This benchmark measures those misses without tuning production.
- Low-precision top-k can reflect overlap duplicates; qrels judge every chunk containing an authored evidence unit. Relevance is exhaustive for these labels, not an independent semantic relevance judgment.
- Existing development results remain unchanged in `RESULTS.md` and earlier JSON. The new held-out synthetic results are the measurements above; no comparison claims between these different datasets.

## Reproduce

See [methodology and commands](METHODOLOGY.md). Raw results: [latest.json](results/latest.json); review worksheet: [human-review.csv](results/human-review.csv).

Application commit: `c70e9c60480b4d441eb6e3959bb9bb578f65acaa`; exact application/harness SHA256 hashes are in raw output.
