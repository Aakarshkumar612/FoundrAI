"""Tests for Layer 5: RAG pipeline — indexer, retriever, pipeline class.

All sentence-transformers model calls and Supabase DB calls are mocked.
No model download or network required.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.rag.indexer import _chunk_text, _csv_to_text, index_document, delete_founder_index
from backend.rag.retriever import retrieve, DocumentChunk
from backend.rag.pipeline import RAGPipeline

FOUNDER_ID = "ffffffff-0000-0000-0000-000000000001"
EMBED_DIM = 384


def _mock_encoder(n_chunks: int = 1) -> MagicMock:
    """Return a mock encoder that returns unit vectors."""
    enc = MagicMock()
    enc.encode.return_value = np.ones((n_chunks, EMBED_DIM), dtype=np.float32)
    return enc


def _mock_supabase(rows=None) -> MagicMock:
    sb = MagicMock()
    sb.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
    sb.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=rows or [])
    return sb


# ── Chunker tests ─────────────────────────────────────────────────────────────

class TestChunker:
    def test_short_text_is_single_chunk(self):
        result = _chunk_text("hello world")
        assert len(result) == 1
        assert result[0] == "hello world"

    def test_long_text_produces_multiple_chunks(self):
        # ~3000 chars → should produce 2+ chunks
        text = "Revenue grew steadily. " * 140
        result = _chunk_text(text)
        assert len(result) >= 2

    def test_chunks_are_non_empty(self):
        text = "A " * 500
        for chunk in _chunk_text(text):
            assert chunk.strip()

    def test_empty_text_returns_empty_list(self):
        assert _chunk_text("") == []


# ── CSV→text conversion tests ─────────────────────────────────────────────────

class TestCSVToText:
    def test_converts_csv_to_readable_text(self):
        csv = b"month,revenue,burn_rate\n2026-01,85000,42000\n2026-02,92000,43000\n"
        text = _csv_to_text(csv)
        assert "revenue" in text.lower()
        assert "85000" in text
        assert "Columns:" in text

    def test_uses_real_synthetic_csv_if_present(self):
        p = Path("data/synthetic/financials.csv")
        if p.exists():
            text = _csv_to_text(p.read_bytes())
            assert "revenue" in text.lower()
            assert len(text) > 100


# ── Indexer tests ─────────────────────────────────────────────────────────────

class TestIndexer:
    CSV_BYTES = b"month,revenue,burn_rate,headcount,cac,ltv\n2026-01,85000,42000,12,450,2100\n" * 5

    def test_index_document_no_db_returns_chunk_count(self):
        with patch("backend.rag.indexer.get_encoder", return_value=_mock_encoder(n_chunks=2)):
            count = index_document(self.CSV_BYTES, FOUNDER_ID, "financial", "fin.csv", None)
        assert count > 0

    def test_index_document_writes_to_supabase(self):
        sb = _mock_supabase()
        with patch("backend.rag.indexer.get_encoder", return_value=_mock_encoder(n_chunks=3)):
            count = index_document(self.CSV_BYTES, FOUNDER_ID, "financial", "fin.csv", sb)
        assert count > 0
        sb.table.assert_called_with("document_embeddings")

    def test_index_document_handles_plain_text(self):
        text = b"Monthly revenue grew 12% in Q1 2026."
        with patch("backend.rag.indexer.get_encoder", return_value=_mock_encoder()):
            count = index_document(text, FOUNDER_ID, "news", "article.txt", None)
        assert count >= 1

    def test_delete_founder_index_no_db_is_noop(self):
        # Should not raise
        delete_founder_index(FOUNDER_ID, supabase_client=None)

    def test_delete_founder_index_calls_supabase(self):
        sb = _mock_supabase()
        delete_founder_index(FOUNDER_ID, supabase_client=sb)
        sb.table.assert_called_with("document_embeddings")


# ── Retriever tests ───────────────────────────────────────────────────────────

class TestRetriever:
    DB_ROWS = [
        {
            "id": "aaa",
            "chunk_text": "Revenue grew 12% MoM over last 6 months.",
            "source_filename": "financials.csv",
            "doc_type": "financial",
            "chunk_index": 0,
            "similarity": 0.91,
        },
        {
            "id": "bbb",
            "chunk_text": "CAC increased from $420 to $510 in Q3.",
            "source_filename": "financials.csv",
            "doc_type": "financial",
            "chunk_index": 1,
            "similarity": 0.87,
        },
    ]

    def test_retrieve_no_db_returns_empty(self):
        result = retrieve("What is my runway?", FOUNDER_ID, top_k=5, supabase_client=None)
        assert result == []

    def test_retrieve_returns_document_chunks(self):
        sb = _mock_supabase(rows=self.DB_ROWS)
        with patch("backend.rag.retriever.get_encoder", return_value=_mock_encoder()):
            result = retrieve("What is my revenue trend?", FOUNDER_ID, top_k=2, supabase_client=sb)
        assert len(result) == 2
        assert isinstance(result[0], DocumentChunk)
        assert result[0].score == 0.91
        assert "Revenue" in result[0].text

    def test_retrieve_calls_rpc_with_correct_args(self):
        sb = _mock_supabase(rows=[])
        with patch("backend.rag.retriever.get_encoder", return_value=_mock_encoder()):
            retrieve("question", FOUNDER_ID, top_k=3, supabase_client=sb)
        sb.rpc.assert_called_once_with(
            "match_document_embeddings",
            {
                "query_embedding": sb.rpc.call_args[0][1]["query_embedding"],
                "founder_uuid": FOUNDER_ID,
                "match_count": 3,
            },
        )

    def test_retrieve_handles_db_error_gracefully(self):
        sb = MagicMock()
        sb.rpc.side_effect = Exception("DB connection lost")
        with patch("backend.rag.retriever.get_encoder", return_value=_mock_encoder()):
            result = retrieve("question", FOUNDER_ID, supabase_client=sb)
        assert result == []


# ── Pipeline class tests ──────────────────────────────────────────────────────

class TestRAGPipeline:
    CSV_BYTES = b"month,revenue,burn_rate,headcount,cac,ltv\n2026-01,85000,42000,12,450,2100\n"

    def test_pipeline_no_db_index_returns_count(self):
        pipeline = RAGPipeline(supabase_client=None)
        with patch("backend.rag.indexer.get_encoder", return_value=_mock_encoder()):
            count = pipeline.index(self.CSV_BYTES, FOUNDER_ID, "financial", "fin.csv")
        assert count >= 1

    def test_pipeline_no_db_query_returns_empty(self):
        pipeline = RAGPipeline(supabase_client=None)
        result = pipeline.query("question", FOUNDER_ID)
        assert result == []

    def test_chunks_to_context_formats_correctly(self):
        pipeline = RAGPipeline()
        chunks = [
            DocumentChunk("Revenue grew 12%.", "financials.csv", 0.91, "financial", 0),
            DocumentChunk("CAC rose to $510.", "financials.csv", 0.87, "financial", 1),
        ]
        context = pipeline.chunks_to_context(chunks)
        assert "[1]" in context
        assert "[2]" in context
        assert "0.91" in context

    def test_chunks_to_context_empty_returns_message(self):
        pipeline = RAGPipeline()
        context = pipeline.chunks_to_context([])
        assert "No relevant context" in context

    def test_pipeline_clear_no_db_is_noop(self):
        pipeline = RAGPipeline(supabase_client=None)
        pipeline.clear(FOUNDER_ID)  # should not raise
