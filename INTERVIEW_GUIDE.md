# Explain this project in an interview

## A 60-second introduction

“I built a local document research application that accepts text, PDFs, CSVs, and images containing text. It uses FastAPI, SQLite, and a React/TypeScript interface. The retrieval pipeline combines TF-IDF and BM25 rankings, filters relevant sentences, and either returns source excerpts or generates an answer with a small local Ollama model. Every generated statement includes validated source IDs. CSV calculations run in deterministic Python code. I added automated tests and a synthetic evaluation suite that exposes limitations in paraphrase retrieval, unsupported questions, and conflicting documents.”

Use this as a description of a personal project you can demonstrate and explain. Do not claim the code was independently written without assistance, production employment outcomes, or hardware optimizations not implemented here.

## Explain the request path

1. The UI sends a file to FastAPI. Format-specific parsers extract text; Tesseract reads text in images.
2. The parser creates overlapping word chunks, with document and page/row metadata stored in SQLite. CSV rows also retain structured values for calculations.
3. TF-IDF scores lexical similarity and BM25 scores term relevance. Reciprocal rank fusion combines their ranked lists without comparing incompatible score scales.
4. Sentence coverage and relevance filters reduce the evidence sent to the answerer. Full chunks stay visible for manual verification.
5. The local model returns structured statements and source IDs. Python validates IDs and renders citations. Extractive mode selects source sentences without an LLM.
6. A trace records workflow stages. The evaluation compares retrieval and answers against labeled development questions.

## Questions you should be able to answer

**Why use both BM25 and TF-IDF?** They emphasize different lexical signals. BM25 incorporates term frequency saturation and document length; TF-IDF cosine similarity compares weighted term vectors. Their overlap means combining them does not automatically prove a gain. This project needs an ablation against each alone before claiming an improvement.

**Is this semantic search?** No. The current retrieval is lexical. It can miss “Who leads Atlas?” when the document says “project manager.” Local sentence embeddings would be a useful comparison, followed by a larger independently labeled evaluation.

**What is reciprocal rank fusion?** For each retrieved item, add `1 / (60 + rank)` from each search list, with rank starting at 1. This combines ranks rather than raw similarity scores.

**Is this an autonomous agent?** The implementation is a controlled multi-stage workflow. CSV tools are selected explicitly in the UI. There is no autonomous tool-selection loop, LangGraph graph, or model-driven external action execution.

**Why use deterministic CSV tools?** Counting rows and computing numeric statistics are straightforward operations that do not require a language model. This avoids model arithmetic mistakes and makes results reproducible.

**Do citations guarantee accuracy?** No. Validation proves a reference points to retrieved evidence. It does not prove that the evidence supports the claim, is trustworthy, refers to the intended entity, or is current.

**How do you handle missing evidence?** A lexical coverage gate can decline generation, and the model can return an empty statement list. Targeted attribute/year checks and clarification routing now address several known failures, but the approach is incomplete: entity names, shared keywords, and time qualifiers can still create misleading matches. Expanded evaluation records these failures.

**What does multimodal mean here?** The ingestion supports several formats. Images are reduced to text through OCR; there is no general visual scene reasoning or image embedding model.

**Why a small local model?** It fits the cost goal and the available 8 GB Mac better than a large hosted model. It trades generation quality for local execution and modest resource requirements. Token speed and memory use still need measured profiling.

**What does your latency metric mean?** Expanded evaluation measures sequential request time for retrieval plus complete answer generation. It is not time to first token, a concurrent load result, or a production service guarantee. OCR ingestion time is outside the per-question latency.

**What does the evaluation measure?** It checks retrieval of a labeled evidence span, reciprocal rank, presence of an expected answer string, citation ID validity, exact refusal behavior, and CSV values. Expected-string presence is a proxy; it does not score semantic correctness. Ambiguous and adversarial cases require review.

**What would you improve next?** First expand independent human review of unsupported and conflicting questions. Then compare retrieval methods, broaden entity/time-aware evidence checks and ambiguity handling beyond the current rules, and independently evaluate prompt-injection resistance. Cache indexes for larger libraries. Add streaming, authentication, and multi-user isolation only with corresponding tests and measurements.

## A five-minute demonstration

- Upload the practice PDF and ask its project-manager question. Open the source card.
- Select the PNG and ask the workshop registration fee. Explain OCR versus visual understanding.
- Switch to all sources and repeat the coordinator question. Show the filtered source list.
- Select sales.csv and calculate the revenue summary: count 4, total 6600, mean 1650.
- Ask an unsupported question and discuss the refusal mechanism and its remaining weaknesses.
- Show `evals/RESULTS.md`, a failed evaluation example, and the automated test output.

## Evidence and boundaries

Read `evals/RESULTS.md` for the recorded run. The dataset is synthetic and authored alongside the implementation, so it is a development set, not an independent test. Do not claim 90% production faithfulness, GPU inference optimization, 100 concurrent requests, cloud deployment, or independently measured improvements over other retrieval systems. The strongest portfolio story is a reproducible local application with transparent evaluation and clearly understood failure modes.
