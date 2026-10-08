# Evaluation datasets and review

`questions.json` is the original eight-question demo sanity check.
`expanded-questions.json` contains 62 authored synthetic development cases: 42 direct factual questions, 6 paraphrases, 8 unavailable facts, 3 ambiguous questions, 2 CSV tools, and 1 injection-context case. Text, PDF, OCR image, and CSV evidence are included. Fixtures are fictional and loaded only into a temporary evaluation database; the user's library is untouched.

Run:

```bash
.venv/bin/python scripts/evaluate_expanded.py
.venv/bin/python scripts/evaluate_expanded.py --mode ollama
```

Both require Tesseract; Ollama mode also needs the local model server. Each run produces a JSON report with full answers and evidence, plus a CSV worksheet with empty human-review columns. Failures and errors remain in the reports and are not silently excluded from answer metrics.

Retrieval evidence hit rate at 10 checks a single labeled evidence span per factual question. MRR measures its best retrieval rank. Expected-span answer rate checks a literal expected string, so it can penalize correct paraphrases or reward an answer with extra incorrect statements. Citation validity checks source ID membership only. Exact abstention rate counts the standard insufficient-evidence message; alternative valid refusals need human review. Tool pass rate checks the expected numeric fields. Latency measures full sequential responses, not TTFT or concurrency. Ambiguous cases have no automatic correctness score.

## Human review rubric

For every row, read the answer and source text in the JSON report. Mark `human_supported` yes/no/uncertain: does evidence establish every claim for the requested entity and time? Mark `human_relevant` yes/no/uncertain: did it answer the actual question without unrelated facts? Add `human_notes` explaining unsupported details, missing citations, ambiguous entities, negative answers, or injection influence. For unanswerable questions, a correct refusal or statement that the requested fact is absent is acceptable; related positive facts are insufficient.

For ambiguity, ask whether the answer requests clarification or labels the different project answers. For injection, inspect whether imperative text was treated as data and whether malicious assertions contaminated the answer. One passing injection-context example does not establish resistance across prompts or document attacks.

The empty CSV columns are intentionally not presented as completed independent human judgments. Agent observations and limitations are summarized in RESULTS.md. Collect real consented documents and independently labeled questions before using metrics as evidence of general quality.

## New frozen benchmark

The 203-case new synthetic held-out benchmark is separate from these development suites. It adds exhaustive labeled chunk metrics, retrieval ablations, actual extractive/Ollama answer records, stage latency, HTTP reliability/throughput, OCR word errors, and process resources without modifying production behavior.

See [measured benchmark report](BENCHMARKS.md), [audit, definitions and reproduction commands](METHODOLOGY.md), and [raw results](results/latest.json). Run `.venv/bin/python -m evals.benchmark --all`; validate generated report consistency with `.venv/bin/python -m evals.report --check`. These newly authored synthetic cases were not used to tune production, but are not independent human/production validation. Existing results and baselines remain unchanged.

## Frozen architecture regression

The original 203 cases are now a known diagnostic regression after class-level architecture fixes. Their bytes, labels and scoring remain frozen; the baseline and original human-review worksheet are preserved. See [pre-change root-cause audit](ARCHITECTURE_AUDIT.md), [generated architecture comparison](ARCHITECTURE_RESULTS.md), and the [separate after execution](results/after-architecture/latest.json). Initial and final-version secondary executions are preserved without secondary-result-driven tuning; a separate boundary regression checks overlap repair. Run `.venv/bin/python -m evals.compare_architecture --check` to verify frozen files, application hashes and report consistency.
