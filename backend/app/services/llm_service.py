"""
app/services/llm_service.py — Groq + Llama integration for grounded
generation. This is where the anti-hallucination behavior is enforced
through prompting (application logic also does its part — see
rag_pipeline.py, which never even calls the LLM if retrieval returns
nothing).
"""

import logging

from groq import Groq, GroqError

from app.services.vectorstore import RetrievedChunk

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are DocMind, a document-grounded assistant.

Rules you must always follow:
1. Answer using ONLY the supplied document context below. Do not invent information.
2. If the answer cannot be found in the retrieved context, say clearly that the
   document does not provide enough information to answer — do not guess.
3. Do not rely on outside/general knowledge for factual claims about the document.
4. Cite the relevant page numbers for every factual claim, using the format (Page N).
5. Keep answers clear, direct, and no longer than necessary.
6. If you are drawing a reasonable inference rather than stating something explicit
   in the text, say so explicitly (e.g. "The document implies..." vs "The document states...").
7. Never fabricate a page number or a citation that isn't backed by the provided context.
"""


class LLMServiceError(Exception):
    """User-facing error for any Groq/LLM failure."""


class LLMService:
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._api_key = api_key
        self._client = Groq(api_key=api_key) if api_key else None

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _build_context_block(self, chunks: list[RetrievedChunk]) -> str:
        blocks = []
        for i, chunk in enumerate(chunks, start=1):
            blocks.append(f"[Source {i} — Page {chunk.page_number}]\n{chunk.text}")
        return "\n\n".join(blocks)

    def generate_answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        if not self._client:
            raise LLMServiceError(
                "GROQ_API_KEY is not configured on the backend. Set it in your .env file."
            )

        context_block = self._build_context_block(chunks)
        user_prompt = (
            f"Document context (retrieved passages):\n\n{context_block}\n\n"
            f"---\n\nQuestion: {question}\n\n"
            f"Answer the question using only the context above, citing page numbers "
            f"as (Page N)."
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except GroqError as e:
            log.error("Groq API error: %s", e)
            raise LLMServiceError(
                "The language model request failed. This usually means an invalid "
                "API key, an exhausted rate limit, or a temporary Groq outage."
            ) from e
        except Exception as e:
            log.error("Unexpected error calling Groq: %s", e)
            raise LLMServiceError("Something went wrong while generating the answer.") from e

        return response.choices[0].message.content.strip()

    def generate_overview(self, document_name: str, sample_chunks: list[RetrievedChunk]) -> str:
        """Document Insights feature: a short, honest overview generated ONLY
        from a page-spread sample of the document's own chunks — never from
        outside knowledge about the topic."""
        if not self._client:
            raise LLMServiceError("GROQ_API_KEY is not configured on the backend.")

        context_block = "\n\n".join(
            f"[Page {c.page_number}]\n{c.text}" for c in sample_chunks
        )
        prompt = (
            f"Below are sampled excerpts from a document called '{document_name}', "
            f"taken from spread-out pages across the whole document.\n\n{context_block}\n\n"
            f"---\n\nWrite a concise 3-4 sentence overview of what this document appears "
            f"to be about, based only on these excerpts. Do not invent details not "
            f"supported by the text. If the excerpts are too fragmentary to summarize "
            f"confidently, say so."
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                max_tokens=300,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except GroqError as e:
            raise LLMServiceError("Couldn't generate a document overview (Groq API error).") from e

        return response.choices[0].message.content.strip()
