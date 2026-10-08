# Local validation

Validated on October 7, 2026 on this Apple Silicon Mac:

- Eight Python tests passed.
- TypeScript checks and the production frontend build passed.
- Live HTTP checks passed for the homepage, demo ingestion, cited answers, and CSV calculations.
- Chromium browser checks passed for asking a question, opening the workflow trace, calculating CSV revenue, and a 390px mobile viewport with no horizontal overflow or JavaScript page errors.
- Screenshots: `desktop-preview.png` and `mobile-preview.png`.
- The synthetic retrieval evaluation is recorded in `report.json`; it is a small demo sanity check, not a production benchmark.

Ollama generation, real Tesseract OCR, the Docker image, and remote GitHub Actions execution were not exercised. Their setup and limitations are documented in the README.

## Missing-evidence fix

The extractive answer selector now requires at least half the meaningful query terms to occur in a candidate sentence and excludes question words and possessive suffixes from matching. Eleven tests pass, including missing phone numbers with straight/curly apostrophes, known budgets and managers, and a phone number present in evidence. The retrieval demo remains 8/8; extractive expected-span presence is now 7/8 because the conservative coverage check declines one indirectly phrased retrieval question. This tradeoff is recorded in report.json. Restart the local server to load Python changes.

## Local AI integration

Ollama and qwen2.5:1.5b were installed and started with OLLAMA_NO_CLOUD=1. The server log confirmed cloud features disabled. Thirteen tests passed. Real local generation returned the correct manager and zero-dollar budget with validated source IDs; the conservative lexical evidence gate declined the missing phone-number query before generation. Results are saved in local-ai-check.json and can be repeated with scripts/check_local_ai.py. Chromium also verified selecting the local model, a generated cited budget answer, and missing-fact abstention. These are integration examples, not a broad factuality benchmark. Tesseract OCR and Docker remain untested.

## Image OCR integration

Tesseract 5.5.3 was installed locally. Sixteen tests passed, including real PNG and JPEG OCR/retrieval and rejection of blank/corrupt images. The clean English workshop image returned the correct coordinator (Elena Brooks), location (Cedar Room), and registration fee (25 dollars), with valid references. Results are saved in ocr-check.json. The live app accepted the image upload and Chromium verified source excerpts and an Ollama-generated registration-fee answer from OCR evidence. Screenshot: ocr-preview.png. This checks one clean text image, not general OCR accuracy or scene understanding. Docker and remote GitHub Actions remain untested.

## All-sources relevance and concise answers

Eighteen tests passed after introducing sentence-level relevance filtering, duplicate-evidence removal, focused model context, and a concise-answer instruction. Four real Ollama queries against the combined five-document local library returned one short cited statement each: workshop coordinator, location, fee, and project manager. Each retained a single relevant source. Full source text is preserved for inspection. Results: all-sources-check.json. The demo retrieval evaluation remains 8/8 evidence hits and 7/8 expected-span answers; conservative lexical filtering can reject paraphrases. No frontend changes were needed.


## Expanded evaluation and interview preparation

Twenty tests passed, including evaluation denominator/error handling and dataset label integrity. Both extractive and real local Ollama modes completed all 62 development cases without request errors. Findings, limitations, and priorities are recorded in RESULTS.md; full results and blank independent-review worksheets are included. This evaluation found unsupported, ambiguous, and malicious-evidence answers that earlier samples missed. These findings are preserved rather than presented as passed safety/faithfulness checks. Interview guidance is in INTERVIEW_GUIDE.md.

## Targeted grounding and clarification

Twenty-six tests passed and the production frontend built successfully. Both 62-question evaluation modes were rerun; baseline reports are preserved. All eight known missing-fact examples now produce the standard refusal in both modes, and all three generic ambiguity examples route to clarification. A browser check verified the clarification label, unsupported-year refusal, and filtering of the known imperative budget injection. Temporary browser-test records were removed from the live library. The local AI expected-string rate increased from 43/49 to 46/49, but q044 still includes another project's manager alongside the correct answer, so the rate is not a semantic correctness score. These rules target the known development failures; general entity resolution, unseen attacks, and semantic paraphrases remain open.

## Document scoping and explicit paraphrases

Twenty-nine tests passed, including named-project isolation for uppercase/lowercase questions and later document chunks. Both 62-question evaluations were rerun. Extractive expected-string presence is 49/49; local AI is 47/49. Both declined all eight known missing-fact cases and clarified the three generic ambiguous questions. The Atlas leadership example now returns only Maya Chen. Local AI still omits rank fusion from the answer to the score-combination question, and literal scoring flags a shorter correct scanned-PDF answer as a miss. A Chromium check exercised local model scoping, clarification, unsupported-year refusal, and known command filtering. Temporary browser fixtures were removed. These are development-set checks; title hints and explicit aliases are not general entity linking or semantic retrieval.

## Final local portfolio handoff

Thirty-two backend/evaluation tests passed. Two checked-in Playwright browser tests passed using an isolated database, covering focused evidence, Markdown export, numeric-column selection, deterministic CSV results, evaluation dashboard, and mobile overflow. Production build and startup shell syntax passed. Readiness checks found the installed local model and OCR engine. Startup was checked on port 8002 and gave a clear diagnostic for occupied port 8000. Updated research/evaluation/mobile screenshots were captured without JavaScript errors. The evaluation dashboard displays recorded summary fields only; full report answers and machine details are not returned by its API. Docker and remote GitHub Actions remain unexecuted.

## Source archive and clean installation

The final source archive was extracted into a new temporary directory with its executable bits preserved. Startup automatically chose installed Python 3.11 rather than incompatible default Python 3.14, created a new virtual environment, installed dependencies, and built the frontend. All 32 backend tests passed there, and live checks verified the homepage, demo ingestion, cited answers, and all four evaluation summaries. The temporary server was stopped. The main app was refreshed on port 8000 and checked with the original five-document library preserved; local AI, OCR, CSV metadata, and evaluation summaries were available. The archive excludes user databases, models, installed dependencies, secrets-style files, and logs. The existing model server remains running locally.
