"""RAG pipeline: unified interface for indexing and querying documents."""

import logging
from typing import List, Optional

from backend.rag.indexer import index_document, delete_founder_index
from backend.rag.retriever import DocumentChunk, retrieve

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Coordinates document indexing and retrieval for a single founder.

    Wraps indexer + retriever behind a clean interface so callers don't
    need to manage the Supabase client or encoder separately.
    """

    def __init__(self, supabase_client=None):
        """Args:
            supabase_client: Supabase client for DB reads/writes.
                             If None, pipeline runs in no-op/offline mode.
        """
        self._db = supabase_client

    def index(
        self,
        content: bytes,
        founder_id: str,
        doc_type: str,
        source_filename: str,
    ) -> int:
        """Index a document for a founder.

        Args:
            content: Raw file bytes.
            founder_id: Owning founder's UUID.
            doc_type: 'financial', 'news', or 'manual'.
            source_filename: Display name for retrieved results.

        Returns:
            Number of chunks indexed.
        """
        return index_document(content, founder_id, doc_type, source_filename, self._db)

    def query(self, question: str, founder_id: str, top_k: int = 5) -> List[DocumentChunk]:
        """Retrieve top-k relevant chunks for a question.

        Args:
            question: Natural language query.
            founder_id: Limits retrieval to this founder's documents.
            top_k: Number of chunks to return.

        Returns:
            List of DocumentChunk sorted by relevance.
        """
        return retrieve(question, founder_id, top_k, self._db)

    def clear(self, founder_id: str) -> None:
        """Remove all indexed documents for a founder.

        Args:
            founder_id: UUID of founder whose index to clear.
        """
        delete_founder_index(founder_id, self._db)

    def chunks_to_context(self, chunks: List[DocumentChunk]) -> str:
        """Format retrieved chunks into a prompt-ready context string.

        Args:
            chunks: Chunks returned by query().

        Returns:
            Formatted context string for injection into agent prompts.
        """
        if not chunks:
            return "No relevant context found."
        lines = []
        for i, c in enumerate(chunks, 1):
            lines.append(f"[{i}] ({c.source}, score={c.score:.2f}): {c.text}")
        return "\n".join(lines)
