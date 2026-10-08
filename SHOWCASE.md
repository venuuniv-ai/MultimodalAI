# Local Research Desk — portfolio showcase

**Developer:** Venu Madhav · Personal project built with coding-agent assistance.

## Project pitch

A private, local document research app that turns PDFs, text files, CSVs, and text-containing images into inspectable answers. It combines lexical retrieval, local LLM generation, deterministic tools, citations, and recorded evaluations in one React interface.

## What to demonstrate

1. Upload `data/practice-project-notes.pdf`; ask “Who leads Atlas Research?” and expand the supporting passage.
2. Upload `data/practice-workshop.png`; ask “What is the workshop registration fee?” to demonstrate OCR evidence and local AI.
3. Choose `sales.csv` and numeric summary; select `revenue`, submit, and show count 4, sum 6600, and mean 1650.
4. Ask “What is the 2027 workshop registration fee?” to demonstrate a missing-year refusal.
5. Open **Evaluation results**, compare the recorded baseline and latest runs, and explain why expected-text matching differs from semantic correctness.
6. Export an answer as Markdown, then show the backend tests and browser tests.

## Skills the code demonstrates

| Area | Concrete evidence |
|---|---|
| Python backend | FastAPI routes, validation, parsers, SQLite storage, deterministic calculations |
| React and TypeScript | Uploads, asynchronous state, source selection, CSV controls, responsive UI, evaluation dashboard |
| Retrieval | TF-IDF, BM25, reciprocal rank fusion, sentence filtering, title-derived scope hints |
| Local generative AI | Ollama integration, structured outputs, validated source IDs, conservative evidence checks |
| Multiformat ingestion | Selectable-text PDFs, CSV rows, text, and Tesseract image OCR |
| Evaluation | Synthetic datasets, preserved baselines, denominator handling, failures, review worksheets |
| Engineering quality | Backend tests, isolated Playwright tests, startup checks, Docker definition, CI configuration |

## Resume bullet options

- Built a local document research application with Python/FastAPI, React/TypeScript, and SQLite, supporting PDF, text, CSV, and image OCR workflows with optional local LLM generation.
- Implemented hybrid TF-IDF/BM25 retrieval, evidence filtering, structured model outputs, validated citations, and deterministic CSV tools; exposed supporting passages and workflow steps in the interface.
- Developed a 62-case synthetic evaluation suite, preserved baseline comparisons, and added automated backend and browser checks to assess retrieval, missing-fact behavior, ambiguity, and tool calculations.

The recorded results come from a development dataset used during implementation. Describe them that way; do not claim production factuality, independent accuracy validation, cloud deployment, or hardware inference optimizations absent from the repository.

## Repository presentation

Use the README as the landing document, include the screenshots in `evals/`, and link `evals/RESULTS.md` and `INTERVIEW_GUIDE.md`. A sensible repository description is “Local document research with citations, OCR, deterministic CSV tools, and reproducible evaluations.” Suggested topics: `rag`, `fastapi`, `react`, `typescript`, `ollama`, `ocr`, `evaluation`.

No repository has been published or remote CI executed by this work. The source archive is ready for review and upload to a repository you choose.
