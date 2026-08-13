"""
app/services/pdf_processor.py — PDF text extraction with page provenance.

The single most important contract of this module: every extracted unit of
text remembers exactly which page it came from. Everything downstream
(chunking, retrieval, citations) depends on that not breaking.
"""

import logging
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

log = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Raised for any PDF that can't be safely processed. Message is
    user-facing — safe to show directly in the API response."""


@dataclass
class PageText:
    page_number: int  # 1-indexed, matches what a human would call "page 14"
    text: str


def extract_pages(file_bytes: bytes, filename: str) -> list[PageText]:
    """Extracts text per page from PDF bytes. Raises PDFProcessingError with
    a clean, user-facing message on any failure (corrupt file, encrypted,
    no extractable text)."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except PdfReadError as e:
        raise PDFProcessingError(f"'{filename}' doesn't look like a valid PDF file.") from e
    except Exception as e:
        raise PDFProcessingError(f"Couldn't open '{filename}': unexpected file format.") from e

    if reader.is_encrypted:
        # Try an empty password (common for "restricted" but not truly locked PDFs);
        # if that fails, this PDF genuinely needs a password we don't have.
        try:
            reader.decrypt("")
        except Exception:
            pass
        if reader.is_encrypted:
            raise PDFProcessingError(
                f"'{filename}' is password-protected. Please upload an unlocked PDF."
            )

    if len(reader.pages) == 0:
        raise PDFProcessingError(f"'{filename}' has no pages.")

    pages: list[PageText] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            log.warning("Failed to extract text from page %d of '%s': %s", i, filename, e)
            text = ""
        pages.append(PageText(page_number=i, text=text.strip()))

    total_chars = sum(len(p.text) for p in pages)
    if total_chars < 20:
        raise PDFProcessingError(
            f"'{filename}' doesn't contain extractable text. It may be a scanned "
            f"image PDF — DocMind currently requires text-based PDFs."
        )

    log.info("Extracted %d pages (%d characters) from '%s'", len(pages), total_chars, filename)
    return pages
