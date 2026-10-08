# Architecture diagnosis before changes

This audit was written before application changes or secondary-set results. Baseline raw output and the original 406-row worksheet are preserved under `results/before-architecture/`; frozen corpus/questions/labels and the original worksheet have SHA256 fingerprints in `frozen-files.json`.

## Evidence-selection loss

The drop from 98.7261% production Recall@5 to 83.4395% full evidence Recall@5 is 24/157 macro recall units, or 15.2866 percentage points:

| Cause | Cases | Added macro recall loss |
| --- | --- | --- |
| Requires both named entities in every sentence | 10 cross-document | 10/157 = 6.3694 pp |
| Whole-query overlap rejects incident-owner relation | 10 paraphrases | 10/157 = 6.3694 pp |
| Retention paraphrase has insufficient sentence overlap | 2 OCR paraphrases | 2/157 = 1.2739 pp |
| Duplicate sentence removed from overlapping chunks | 4 location cases, each loses half of its chunk qrels | 2/157 = 1.2739 pp |

The five-source cap is not the cause of the ten cross-document refusals: evidence is already empty before the cap. Restoring duplicate sentences would inflate chunk recall without restoring information. Keep deduplication and distinguish chunk recall from expected evidence-unit coverage.

Eight text/PDF retention paraphrases retain repetitive checkpoint paragraphs rather than the expected retention statement. Two relevant chunks rank below five but all expected facts are present at ten. Full-chunk relevance can count a retained chunk even when its *focused sentence* omits the fact; that is why the 30 answer-presence failures exceed the 22 new complete chunk-retrieval misses.

## Cross-document trace

Query names two projects -> raw search returns both relevant chunks (all ten have Recall@5/10=1 and first relevant rank=1) -> `requested_scope` contains both entities -> `requested_scope <= explicitly_named` rejects each sentence naming only one project -> no sources -> no context or prompt reaches Ollama -> exact refusal. Generation and context length are not the initial failure. Extractive selection repeats whole-query matching and would also penalize independent facts if supplied.

## Answer completeness and abstention taxonomy

Both modes have 30/157 expected-value failures: 20 paraphrases and ten cross-document questions. Twenty-two are refusals (ten owner paraphrases, two OCR retention paraphrases, ten cross-document); eight answer irrelevant checkpoint text. There are no ingestion failures or model-call errors. All 30 have expected evidence somewhere in raw top ten, and none retain the expected value in focused text. These are upstream selection failures, not measured semantic model errors. Two cases additionally have raw top-five misses. Full per-case attribution is in the baseline taxonomy JSON.

## Adversarial contamination

The filter recognizes only a few sentence-start imperative words and a narrow `ignore ... instructions` phrase. Role markers, output directives elsewhere in a sentence, and spaced-letter obfuscation survive. Extractive mode copies them verbatim; validated IDs still point to untrusted text. Five conflicting factual assertions pass both modes because neither detects different values for the same entity/attribute and neither has authenticated provenance to select the correct one. A stronger model prompt alone cannot resolve which document is authoritative.

## Ambiguity

The clarification rule full-matches only project manager, cloud budget, or launch date forms. Unscoped deployment-location and retention-period queries return several project-specific answers without clarifying. The existing broad ranking/thresholds cannot resolve user intent from multiple equally applicable entities. Scope must be established before selecting one answer.

## Design decision

Keep retrieval formulas/reranking unchanged. Introduce an evaluation-independent evidence planner: normalize common lexical/morphological variants; identify candidate relation phrases from declarative evidence; match relations separately from requested entity names; cover entity/relation slots within the existing bounded source budget. Query paraphrase matching must describe relation classes, never benchmark IDs/project names/answer values or exact questions.

Detect instruction-bearing content as untrusted control attempts, use typed JSON data in model context, and detect incompatible values for the same entity/relation across documents. With no authenticated authority metadata, clarify rather than silently prioritize a filename/title. Preserve alternative evidence for review. Generalize ambiguity to multiple applicable entity/attribute slots, not a finite list of questions. Keep missing-field/year guards and refuse unsupported requested relations.

Before inspecting results of these changes, author and freeze a second dataset using new entities, facts, phrasings, contradictions, benign instructions and negative fields. Run it once after implementation is fixed; treat subsequent result-informed changes as tuning and disclose them.
