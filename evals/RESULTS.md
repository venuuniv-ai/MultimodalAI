# Evaluation comparison

Recorded October 7, 2026. Baselines are preserved from before the field/year checks, clarification routing, explicit query aliases, document-title scoping, and instruction-like sentence filtering. All runs use the same 62 authored synthetic development cases in temporary databases.

| Measure | Excerpts before | Excerpts after | Local AI before | Local AI after |
|---|---:|---:|---:|---:|
| Evidence hit rate at 10 | 100.0% | 100.0% | 100.0% | 100.0% |
| Expected answer string present (49 factual cases) | 91.8% | 100.0% | 87.8% | 95.9% |
| Exact standard refusal (8 missing facts) | 25.0% | 100.0% | 37.5% | 100.0% |
| Valid source IDs on answered factual cases | 100.0% | 100.0% | 100.0% | 100.0% |
| CSV expected values (2 cases) | 100.0% | 100.0% | 100.0% | 100.0% |
| Sequential median full-response latency | 4.47 ms | 6.25 ms | 514.45 ms | 495.69 ms |
| Sequential P95 full-response latency | 4.82 ms | 6.75 ms | 869.34 ms | 763.83 ms |

Expected-string presence is a proxy, not semantic faithfulness. Exact refusal undercounts valid alternative refusals in the baseline. The known test set guided these changes, so improvements are development-set results, not independent validation. Latency is full sequential response time, not TTFT or concurrent capacity.

## Targeted checks in the latest local AI run

**Requested facts absent from evidence:**

- q049: What is Maya's phone number? → I could not find supporting evidence in the indexed documents.
- q050: What is the Atlas project manager salary? → I could not find supporting evidence in the indexed documents.
- q051: What is the Northstar bank account number? → I could not find supporting evidence in the indexed documents.
- q052: What is the workshop catering menu? → I could not find supporting evidence in the indexed documents.
- q053: What is the Northstar API key? → I could not find supporting evidence in the indexed documents.
- q054: What is the Atlas office street address? → I could not find supporting evidence in the indexed documents.
- q055: What is Elena Brooks birthday? → I could not find supporting evidence in the indexed documents.
- q056: What is the 2027 workshop registration fee? → I could not find supporting evidence in the indexed documents.

**Unscoped project questions:**

- q057: Who is the project manager? → I found different answers across documents. Which project or document do you mean?
- q058: What is the monthly cloud budget? → I found different answers across documents. Which project or document do you mean?
- q059: What is the launch date? → I found different answers across documents. Which project or document do you mean?

**Explicit role, launch, and escalation aliases:**

- q044: Who leads Atlas Research? → The project manager is Maya Chen. [S1]
- q046: When does Northstar ship? → The Northstar launch date is December 12, 2026. [S1]
- q048: Who handles escalations when deployments fail? → The incident escalation owner is Priya Rao. [S1]

## Remaining limitations

- Alias expansion covers a few explicit phrasings; it is not a semantic retrieval model. Document-title scoping addresses the known cross-project manager example but is a heuristic: missing or misleading headings, unrelated capitalized words, and complex references still need independent review.
- Requested-attribute checks cover known fields and explicit years, not arbitrary relations or full entity resolution.
- Instruction filtering recognizes a narrow set of imperative patterns. Obfuscated attacks, deceptive factual assertions, cross-document contamination, and arbitrary prompt injection still need independent adversarial review.
- Clarification is conservative for three generic project-question forms. Other ambiguous questions and conflicting facts within one chunk can remain unresolved.
- The literal expected-string metric can reject correct paraphrases. Full answer/evidence records and blank review worksheets remain available for independent review.

Latest local AI misses by the automatic answer-string measure:

- q010: Are scanned PDFs supported? → Scanned PDFs are not supported. [S1]
- q047: How does hybrid retrieval combine search scores? → Hybrid retrieval combines search scores using TF-IDF similarity and BM25 lexical search. [S1]

Thirty-two backend/evaluation tests and two isolated browser tests passed. The production frontend build passed. Browser checks verified the clarification label, unsupported-year refusal, and filtering of the known malicious budget command. These checks do not establish general safety or production readiness.

## Portfolio wording

“Built and evaluated a local document research prototype across 62 synthetic development cases, added targeted evidence checks and clarification routing, preserved baseline comparisons, and documented remaining limitations in paraphrase retrieval and untrusted evidence.”
