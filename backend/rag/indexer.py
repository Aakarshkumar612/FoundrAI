"""Document indexer: chunks text and stores embeddings in pgvector via Supabase."""

import io
import logging
import uuid
from typing import List, Optional

import numpy as np
import pandas as pd

from backend.rag.encoder import get_encoder

logger = logging.getLogger(__name__)

CHUNK_SIZE = 400      # tokens (approx chars / 4)
CHUNK_OVERLAP = 80    # overlap between chunks


def _chunk_text(text: str) -> List[str]:
    """Split text into overlapping chunks by character count.

    Args:
        text: Raw text to chunk.

    Returns:
        List of chunk strings.
    """
    size = CHUNK_SIZE * 4       # approx chars per token
    overlap = CHUNK_OVERLAP * 4
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start += size - overlap
    return [c for c in chunks if c]


def _csv_to_text(file_bytes: bytes) -> str:
    """Convert a CSV file to a readable text representation for embedding.

    Args:
        file_bytes: Raw CSV bytes.

    Returns:
        Human-readable string summarising all CSV rows.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    lines = [f"Columns: {', '.join(df.columns)}"]
    for _, row in df.iterrows():
        lines.append(" | ".join(f"{k}: {v}" for k, v in row.items()))
    return "\n".join(lines)


def index_document(
    content: bytes,
    founder_id: str,
    doc_type: str,
    source_filename: str,
    supabase_client=None,
) -> int:
    """Chunk, encode, and upsert a document's embeddings into pgvector.

    Args:
        content: Raw file bytes (CSV supported; plain text also works).
        founder_id: UUID of the owning founder (used for RLS filtering).
        doc_type: One of 'financial', 'news', 'manual'.
        source_filename: Original filename for display in retrieved results.
        supabase_client: Supabase client instance. If None, skips DB write
                         (useful for offline/test mode).

    Returns:
        Number of chunks indexed.
    """
    # Convert CSV to text; treat everything else as plain text
    try:
        text = _csv_to_text(content)
    except Exception:
        text = content.decode("utf-8", errors="replace")

    chunks = _chunk_text(text)
    if not chunks:
        logger.warning("No chunks produced for %s", source_filename)
        return 0

    encoder = get_encoder()
    embeddings: np.ndarray = encoder.encode(chunks, normalize_embeddings=True)

    if supabase_client is None:
        logger.info(
            "index_document (no DB): %d chunks for founder=%s file=%s",
            len(chunks), founder_id, source_filename,
        )
        return len(chunks)

    rows = [
        {
            "id": str(uuid.uuid4()),
            "founder_id": founder_id,
            "doc_type": doc_type,
            "source_filename": source_filename,
            "chunk_text": chunk,
            "chunk_index": i,
            "embedding": embeddings[i].tolist(),
            "metadata": {"doc_type": doc_type},
        }
        for i, chunk in enumerate(chunks)
    ]

    try:
        supabase_client.table("document_embeddings").upsert(rows).execute()
        logger.info(
            "Indexed %d chunks for founder=%s file=%s", len(rows), founder_id, source_filename
        )
    except Exception as exc:
        logger.error("pgvector upsert failed for %s: %s", source_filename, str(exc))
        raise

    return len(rows)


def delete_founder_index(founder_id: str, supabase_client=None) -> None:
    """Remove all embeddings for a founder from pgvector.

    Args:
        founder_id: UUID of the founder whose index to clear.
        supabase_client: Supabase client instance.
    """
    if supabase_client is None:
        logger.info("delete_founder_index (no DB): founder=%s", founder_id)
        return
    try:
        supabase_client.table("document_embeddings").delete().eq(
            "founder_id", founder_id
        ).execute()
        logger.info("Deleted all embeddings for founder=%s", founder_id)
    except Exception as exc:
        logger.error("Failed to delete index for founder=%s: %s", founder_id, str(exc))
        raise
