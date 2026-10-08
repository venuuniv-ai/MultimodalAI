# Portfolio description

## Resume wording for the implementation in this repository

**Local Multimodal Retrieval & Document Research Platform — Personal Project**

- Built a local document research application using Python, FastAPI, React, TypeScript, and SQLite, supporting text, selectable-text PDFs, CSV data, and an optional image OCR pipeline.
- Implemented hybrid TF-IDF/BM25 retrieval with reciprocal rank fusion, lexical reranking, source citations, reference validation, and optional local LLM generation through Ollama.
- Added deterministic CSV analysis tools, an inspectable workflow trace, automated backend tests, and a reproducible evaluation harness measuring evidence retrieval and citation validity on a 62-question synthetic development dataset covering direct questions, paraphrases, unavailable facts, ambiguous entities, CSV tools, and untrusted evidence.

Local Ollama generation has now been exercised on the practice PDF. Local Tesseract OCR has also been exercised on a clean English sample image in PNG and JPEG formats. Describe this as image text extraction, not general visual scene understanding. Do not describe this as production employment work. Resume claims should reflect your own work, understanding, and measured results.

## Learn the project

1. Load demo data and ask about the weekly research review. Expand the source card and verify Thursday at 10 AM.
2. Select sales.csv, choose numeric summary, and enter `revenue`. Verify count 4, sum 6600, and mean 1650.
3. Read `backend/app/store.py`: parsing, word-based chunking, storage, two retrieval scorers, rank fusion, and CSV calculations.
4. Read `backend/app/agent.py`: workflow routing, evidence assembly, source excerpts, local generation, reference validation.
5. Read `backend/app/main.py`: input validation and API endpoints.
6. Read `frontend/src/main.tsx`: uploads, source selection, questions, result cards, trace.
7. Run tests and the evaluation. Change a question and explain why retrieval ranking changes.
8. Install Ollama and Tesseract only when ready to exercise those optional paths.

## Useful next improvements

The repository now contains 62 authored synthetic development questions. Next collect independently labeled real-world questions, including unanswerable cases, and review the failures in `evals/RESULTS.md`. Compare lexical retrieval to local sentence embeddings and FAISS. Measure actual answer support through human review. Add conversation history and model-selected tools with explicit tool schemas and validation. Cache indexes and profile ingestion/query latency. Add streaming only after the basic generation workflow is reliable.

Hardware-specific inference optimizations require matching hardware and measurements; do not assume an Apple Silicon laptop supports the NVIDIA CUDA/TensorRT stack in the original resume.
