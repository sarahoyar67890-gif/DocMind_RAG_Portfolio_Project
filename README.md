# DocMind — RAG-Powered Document Intelligence & Q&A

Upload a PDF, ask it questions in plain English, and get answers grounded in
the document's actual text — with page-level citations you can verify
yourself.

---

## Table of contents

- [Overview](#overview)
- [Problem](#problem)
- [Solution](#solution)
- [Why RAG?](#why-rag)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Document processing](#document-processing)
- [Chunking](#chunking)
- [Embeddings](#embeddings)
- [Vector search](#vector-search)
- [LLM generation](#llm-generation)
- [Citation grounding](#citation-grounding)
- [Anti-hallucination strategy](#anti-hallucination-strategy)
- [FastAPI](#fastapi)
- [Streamlit](#streamlit)
- [Docker](#docker)
- [Environment variables](#environment-variables)
- [Installation](#installation)
- [Running locally](#running-locally)
- [Running with Docker](#running-with-docker)
- [Example questions](#example-questions)
- [Limitations](#limitations)
- [Future improvements](#future-improvements)
- [Responsible AI](#responsible-ai)

---

## Overview

DocMind is a full-stack Retrieval-Augmented Generation (RAG) application:
FastAPI backend, Streamlit frontend, ChromaDB vector store, Sentence-
Transformers embeddings, and Groq-hosted Llama for generation — all
containerized with Docker Compose.

## Problem

Long documents (policies, papers, manuals, reports) are hard to search when
you don't know the exact wording used. Ctrl+F only finds text you can
already guess. Pasting the whole document into an LLM's context works for
short files but doesn't scale, gets expensive, and gives you no way to
verify which part of the document actually supports an answer.

## Solution

DocMind retrieves only the passages relevant to a specific question and
gives *those* to the LLM as context, instead of the whole document. Every
answer comes back with the exact pages and excerpts it was built from, so
the user can verify it in seconds rather than trusting it blindly.

## Why RAG?

Three reasons, in order of importance for this project:

1. **Grounding** — the model answers from retrieved text, not free
   recall, which sharply reduces made-up answers about the *specific*
   document (see [Anti-hallucination strategy](#anti-hallucination-strategy)).
2. **Verifiability** — because retrieval is explicit, DocMind knows exactly
   which passages informed an answer and can cite them precisely.
3. **Scalability** — a 300-page PDF doesn't fit in every model's context
   window, and even when it does, stuffing the whole thing in wastes tokens
   and money on every single question. Retrieval sends only what's relevant.

## How it works

```
Upload PDF → Extract text (per page) → Chunk → Embed → Store in ChromaDB
    → Ask question → Embed question → Vector similarity search
    → Retrieve top-k chunks → Send to Groq/Llama as context
    → Generate grounded answer → Display answer + page citations
```

## Architecture

```
┌─────────────┐        HTTP         ┌──────────────┐
│  Streamlit  │  ───────────────►   │   FastAPI    │
│  frontend   │  ◄───────────────   │   backend    │
└─────────────┘                     └──────┬───────┘
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     ▼                      ▼                      ▼
             ┌───────────────┐     ┌────────────────┐     ┌──────────────┐
             │  pypdf         │     │  Sentence-      │     │  ChromaDB     │
             │  extraction    │     │  Transformers   │     │  vector store │
             └───────────────┘     └────────────────┘     └──────────────┘
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │  Groq + Llama   │
                                   │  (generation)   │
                                   └────────────────┘
```

Streamlit **never** talks to ChromaDB, the embedding model, or Groq
directly — everything RAG-related happens behind the FastAPI backend
(`api_client.py` in the frontend is a thin HTTP client, nothing more).
This separation is deliberate: it's the difference between "a Streamlit
script" and "an application with a real service boundary."

## Technology stack

| Layer | Technology |
|---|---|
| PDF extraction | `pypdf` |
| Chunking | `langchain-text-splitters` (RecursiveCharacterTextSplitter) |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2` by default, configurable) |
| Vector store | ChromaDB (persistent client) |
| LLM | Groq API, Llama models (configurable) |
| Backend | FastAPI + Pydantic |
| Frontend | Streamlit |
| Containerization | Docker + Docker Compose |

**Why not LangGraph:** the actual control flow here is a straight line —
retrieve, then generate, no branching, no agentic tool loops, no multi-step
planning. A graph orchestrator earns its complexity when there's real
branching or looping behavior to model; this pipeline doesn't have any, so
`rag_pipeline.py` is a plain, readable Python function instead. LangChain's
text splitter is used where it's genuinely useful (chunking) without pulling
in machinery the project doesn't need.

## Document processing

`pdf_processor.py` extracts text **per page** using `pypdf`, so every chunk
downstream can be traced back to an exact page number. Encrypted PDFs,
corrupt files, and image-only (no extractable text) PDFs are all detected
and rejected with a clear, human-readable message rather than crashing or
silently producing empty results.

## Chunking

`chunking.py` runs a `RecursiveCharacterTextSplitter` **independently on
each page's text** (not on the whole document concatenated together). This
is a deliberate tradeoff: a chunk can never span two pages, which means
every chunk has one unambiguous, correct page number — the thing that makes
citations trustworthy. The alternative (split the whole document, then map
character offsets back to pages) is more complex and has more ways to
silently misattribute a chunk to the wrong page.

- **Chunk size** (default 800 characters) — small enough that retrieval
  pulls focused, relevant text rather than diluted context; large enough to
  preserve a complete thought.
- **Chunk overlap** (default 150 characters) — without overlap, a sentence
  that happens to fall right at a chunk boundary gets cut in half and its
  meaning can be lost to both neighboring chunks. Overlap gives boundary
  content a chance to appear intact in at least one chunk.

Both are configurable via `CHUNK_SIZE` / `CHUNK_OVERLAP` environment
variables — see [Environment variables](#environment-variables).

## Embeddings

`embeddings.py` wraps Sentence-Transformers (default model
`all-MiniLM-L6-v2` — small, fast, strong general-purpose semantic
similarity). Embeddings are **L2-normalized**, which lets ChromaDB's cosine
similarity space work correctly and keeps similarity scores in a clean
`[0, 1]` range. The model is configurable via `EMBEDDING_MODEL`.

## Vector search

`vectorstore.py` wraps a persistent ChromaDB collection. Every chunk is
stored with `document_id`, `document_name`, and `page_number` metadata.
Retrieval queries always filter `where={"document_id": ...}` to the active
document, so chunks from a previously uploaded document can never leak into
answers for a different one — even though they may still live in the same
underlying collection (this is also what makes the processing cache safe).
Top-k is configurable via `RETRIEVAL_TOP_K`, not hard-coded.

## LLM generation

`llm_service.py` calls the Groq API with a system prompt that explicitly
instructs the model to answer only from the supplied context, decline when
the context doesn't cover the question, and cite page numbers — see the
full prompt in that file. Model, temperature, and max tokens are all
configurable via environment variables.

## Citation grounding

Every `/query` response includes a `sources` array: chunk id, document
name, page number, the actual excerpt text, and a `retrieval_similarity`
score (explicitly labeled as retrieval similarity, not "AI confidence" —
similarity measures how well a passage matched the question semantically,
which is a different thing from whether the final answer is factually
correct). The Streamlit UI renders these as distinct gold-accented source
cards, visually separated from the generated answer, with an "expand
sources" interaction so the evidence doesn't clutter the main answer.

## Anti-hallucination strategy

Two layers, deliberately not just one:

1. **Prompting** — the system prompt instructs the model to answer only
   from context, decline when context is insufficient, and never fabricate
   citations.
2. **Application logic** — if vector search returns *zero* chunks for the
   active document, `rag_pipeline.py` never calls the LLM at all; it
   returns a fixed, honest "not enough information" response directly. A
   prompt is a strong nudge, not a hard guarantee — for the one case where
   the code can be certain (no retrieved context exists), it doesn't rely
   on the model to police itself.

**Being direct about what this does and doesn't guarantee:** RAG grounding
substantially *reduces* unsupported claims about the specific document
compared to an ungrounded LLM answering from memory — but it does not
*eliminate* hallucination risk. A model can still misread or over-generalize
from retrieved text. That's exactly why every answer ships with its source
excerpts: verification is part of the design, not an afterthought.

## FastAPI

The backend (`backend/app/`) owns all RAG logic: upload handling, PDF
extraction, chunking, embedding, indexing, retrieval, and generation.
Routes are thin (`main.py`); the actual logic lives in `services/`. All
request/response shapes are Pydantic models (`schemas.py`), and every
foreseeable failure mode — invalid file type, empty file, oversized file,
corrupt/encrypted/image-only PDF, missing Groq key, Groq API failure, no
active document — returns a clean JSON error with an appropriate HTTP
status code, never a raw Python traceback.

## Streamlit

The frontend (`frontend/app.py` + `style.py`) is a custom-designed
interface: an editorial "document intelligence" visual identity (Fraunces
serif headlines, Inter body text, IBM Plex Mono for technical labels), a
signature animated "highlight sweep" hero panel that echoes the product's
core idea (answers traced back to a highlighted passage), a real processing
checklist during upload, a chat interface with distinct gold-accented
source cards, and a Document Insights panel. It degrades gracefully with no
backend running or no Groq key configured — the UI still renders fully with
a clear explanatory message instead of crashing.

**Unique feature — Document Insights:** after upload, the user can request
a concise, honest overview of the document, generated from a small sample
of chunks spread across the document's pages (not a fixed windowed 
excerpt) — giving a portfolio-relevant demonstration of RAG's building
blocks solving a second problem (summarization) with the same underlying
retrieval infrastructure.

## Docker

`docker-compose.yml` builds and runs both services. The frontend reaches
the backend via the Docker-internal service hostname `http://backend:8000`
— **not** `localhost`, since each Compose service gets its own network
namespace and `localhost` inside the frontend container means the frontend
container itself. ChromaDB's persisted data and the document registry are
both backed by named Docker volumes (`chroma_data`, `registry_data`), so
processed documents survive a container restart. The frontend's `depends_on`
uses a health check condition, so it won't start serving traffic against a
backend that isn't ready yet.

## Environment variables

See `.env.example` — copy it to `.env` and fill in your own values. `.env`
is git-ignored; no real secret is ever committed to this repository.

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Generation model |
| `LLM_TEMPERATURE` | `0.1` | Lower = more deterministic, grounded answers |
| `LLM_MAX_TOKENS` | `800` | Max answer length |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers model |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `RETRIEVAL_TOP_K` | `4` | Chunks retrieved per question |
| `MAX_UPLOAD_MB` | `30` | Upload size limit |
| `BACKEND_URL` | `http://localhost:8000` | Frontend → backend URL (Docker sets this to `http://backend:8000` automatically) |

## Installation

```powershell
git clone <this-repo>
cd DocMind
copy .env.example .env
# edit .env and add your GROQ_API_KEY
```

### Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```powershell
cd frontend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Running locally

```powershell
# Terminal 1 — backend
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
venv\Scripts\activate
set BACKEND_URL=http://localhost:8000
streamlit run app.py
```

Open `http://localhost:8501`.

## Running with Docker

Requires Docker Desktop on Windows.

```powershell
copy .env.example .env
# edit .env and add your GROQ_API_KEY
docker compose up --build
```

Frontend: `http://localhost:8501` · Backend docs: `http://localhost:8000/docs`

## Example questions

Once a document is uploaded, try questions like:

- "What is the main purpose of this document?"
- "What does this say about [specific topic in your document]?"
- "Are there any exceptions mentioned to [a rule in your document]?"
- A question about something the document *doesn't* cover — DocMind should
  clearly say it couldn't find enough information, rather than guessing.

## Limitations

- Text-based PDFs only — scanned/image-only PDFs without an existing text
  layer aren't supported (no OCR step in this version).
- One active document at a time by design; the architecture (document_id
  metadata in ChromaDB) supports extending to multiple simultaneous
  documents, but the current UI keeps one active document for reliability
  and simplicity.
- Chunking never spans a page boundary, so an answer that genuinely
  requires connecting the very end of one page to the very start of the
  next may retrieve both chunks but not merge them as fluidly as a
  document-level splitter would.
- RAG grounding reduces, but does not eliminate, the risk of an incorrect
  or over-generalized answer — always check the cited source pages for
  anything that matters.
- Groq API rate limits and the chosen model's context window (via
  `LLM_MAX_TOKENS` and retrieved chunk count) bound how much context can be
  supplied per question.

## Future improvements

- OCR fallback for scanned/image PDFs.
- True multi-document mode in the UI (the backend's `document_id` filtering
  already supports it).
- Streaming token-by-token answer rendering.
- Reranking retrieved chunks with a cross-encoder before generation.
- Conversation-aware retrieval (folding recent chat history into the query
  embedding for follow-up questions).

## Responsible AI

DocMind is built to reduce, not eliminate, the risk of an AI system stating
something false with confidence. It does this by grounding every answer in
retrieved document text and always showing that text back to the user.
Retrieval-augmented generation is a mitigation, not a guarantee — no claim
here should be read as "hallucinations are impossible." For anything where
correctness matters, treat DocMind's citations as a fast way to verify the
answer against the source, not as a replacement for reading the relevant
page yourself.
