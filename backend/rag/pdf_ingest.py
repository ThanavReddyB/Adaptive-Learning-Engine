import io
from typing import List, Tuple

import pdfplumber

from memory.vector_store import get_vector_store


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF byte string using pdfplumber."""
    pages: List[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 400,
    overlap: int = 80,
) -> List[str]:
    """
    Split text into overlapping word-count chunks.
    chunk_size  – target words per chunk
    overlap     – words shared between successive chunks
    """
    words = text.split()
    chunks: List[str] = []
    step = max(chunk_size - overlap, 1)
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end == len(words):
            break
        start += step

    return chunks


# ---------------------------------------------------------------------------
# Ingestion pipeline
# ---------------------------------------------------------------------------

def ingest_pdf(
    file_bytes: bytes,
    topic: str,
    filename: str = "upload.pdf",
) -> Tuple[int, int]:
    """
    Extract → chunk → embed → store.

    Returns:
        (chunks_stored, total_characters)
    """
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        return 0, 0

    chunks = chunk_text(text)
    if not chunks:
        return 0, len(text)

    store = get_vector_store()
    metadatas = [
        {
            "topic": topic,
            "source": filename,
            "type": "pdf_chunk",
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    store.add_batch(chunks, metadatas)
    return len(chunks), len(text)
