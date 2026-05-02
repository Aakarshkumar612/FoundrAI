import logging
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from backend.rag.encoder import get_encoder

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    text: str
    source: str
    score: float
    doc_type: str
    chunk_index: int


def retrieve(
    query: str,
    founder_id: str,
    top_k: int = 5,
    supabase_client=None,
) -> List[DocumentChunk]:
    """Encode a query and retrieve the top-k most similar chunks from pgvector."""
    if supabase_client is None:
        logger.debug("retrieve: no DB client — returning empty context")
        return []

    encoder = get_encoder()
    query_vec: np.ndarray = encoder.encode([query], normalize_embeddings=True)[0]

    try:
        # Standardize the RPC call to handle potential missing fields gracefully
        result = supabase_client.rpc(
            "match_document_embeddings",
            {
                "query_embedding": query_vec.tolist(),
                "founder_uuid": founder_id,
                "match_count": top_k,
            },
        ).execute()
    except Exception as exc:
        logger.error("pgvector retrieval failed for founder=%s: %s", founder_id, str(exc))
        return []

    chunks = []
    for row in (result.data or []):
        chunks.append(DocumentChunk(
            text=row.get("chunk_text") or row.get("text") or "",
            source=row.get("source_filename") or row.get("source") or "unknown",
            score=float(row.get("similarity") or 0.0),
            doc_type=row.get("doc_type") or "unknown",
            chunk_index=int(row.get("chunk_index") or 0),
        ))

    return chunks
