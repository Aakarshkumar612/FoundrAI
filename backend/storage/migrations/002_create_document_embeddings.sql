-- Migration 002: Document embeddings table with pgvector
-- Depends on: 001_create_founders.sql
-- Run in: Supabase Dashboard → SQL Editor

-- Enable pgvector extension (already enabled on Supabase by default)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.document_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id      UUID NOT NULL REFERENCES public.founders(id) ON DELETE CASCADE,
    doc_type        TEXT NOT NULL CHECK (doc_type IN ('financial', 'news', 'manual')),
    source_filename TEXT,
    chunk_text      TEXT NOT NULL,
    chunk_index     INT NOT NULL,
    embedding       VECTOR(384),   -- all-MiniLM-L6-v2 output dimension
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- IVFFlat index for fast approximate cosine similarity search
-- lists=100 is appropriate for up to ~1M rows
CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx
    ON public.document_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index on founder_id for fast per-founder filtering
CREATE INDEX IF NOT EXISTS document_embeddings_founder_idx
    ON public.document_embeddings (founder_id);

-- Enable RLS
ALTER TABLE public.document_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "embeddings_select_own" ON public.document_embeddings
    FOR SELECT USING (auth.uid() = founder_id);

-- INSERT/DELETE handled by service_role (backend bypasses RLS)

-- ── Retrieval RPC function ────────────────────────────────────────────────────
-- Called by retriever.py via supabase_client.rpc("match_document_embeddings", ...)
-- Returns top match_count chunks ordered by cosine similarity (highest first)

CREATE OR REPLACE FUNCTION public.match_document_embeddings(
    query_embedding VECTOR(384),
    founder_uuid    UUID,
    match_count     INT DEFAULT 5
)
RETURNS TABLE (
    id              UUID,
    chunk_text      TEXT,
    source_filename TEXT,
    doc_type        TEXT,
    chunk_index     INT,
    similarity      FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        chunk_text,
        source_filename,
        doc_type,
        chunk_index,
        1 - (embedding <=> query_embedding) AS similarity
    FROM public.document_embeddings
    WHERE founder_id = founder_uuid
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
