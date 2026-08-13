"""
app/services/chunking.py — Splits extracted page text into retrieval-sized
chunks while keeping page provenance intact.

DESIGN DECISION (documented, not hidden): chunking is done PER PAGE, not on
the whole document concatenated together. A RecursiveCharacterTextSplitter
runs independently on each page's text. This means a chunk never spans two
pages, which trades a small amount of cross-page context for a guarantee
that every chunk has one unambiguous, correct page number — which is what
makes citations trustworthy. The alternative (split the whole document,
then map character offsets back to pages) is more complex and has more ways
to silently misattribute a chunk to the wrong page.
"""

import hashlib
import logging
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.pdf_processor import PageText

log = logging.getLogger(__name__)


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    text: str


def chunk_pages(
    pages: list[PageText],
    document_id: str,
    document_name: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Chunk] = []
    for page in pages:
        if not page.text:
            continue
        page_chunks = splitter.split_text(page.text)
        for local_idx, text in enumerate(page_chunks):
            # Deterministic chunk_id: same document + page + position always
            # hashes the same way, which is what makes the processing cache safe.
            raw_id = f"{document_id}:p{page.page_number}:c{local_idx}"
            chunk_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:16]
            chunks.append(Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name=document_name,
                page_number=page.page_number,
                text=text.strip(),
            ))

    log.info(
        "Chunked '%s' into %d chunks (chunk_size=%d, overlap=%d)",
        document_name, len(chunks), chunk_size, chunk_overlap,
    )
    return chunks
