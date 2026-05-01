-- Migration 003: news_articles and ingestion_logs tables
-- Run in Supabase SQL Editor

-- ── news_articles ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS news_articles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL DEFAULT '',
    author          TEXT,
    published_date  TEXT,
    source          TEXT,
    full_text       TEXT NOT NULL DEFAULT '',
    topics          TEXT[] NOT NULL DEFAULT '{}',
    indexed         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_articles_url     ON news_articles (url);
CREATE INDEX IF NOT EXISTS idx_news_articles_created ON news_articles (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_indexed ON news_articles (indexed) WHERE indexed = FALSE;

-- RLS: news articles are global (readable by any authenticated user)
ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY;

CREATE POLICY news_articles_select_authenticated
    ON news_articles FOR SELECT
    TO authenticated
    USING (TRUE);

-- Service role (backend) can insert/update freely — no policy needed for service_role

-- ── ingestion_logs ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ingestion_logs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingested_count   INTEGER NOT NULL DEFAULT 0,
    skipped_count    INTEGER NOT NULL DEFAULT 0,
    error_count      INTEGER NOT NULL DEFAULT 0,
    duration_seconds NUMERIC(8, 2) NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_logs_created ON ingestion_logs (created_at DESC);

-- RLS: ingestion logs are internal — only service_role writes, no direct user reads needed
ALTER TABLE ingestion_logs ENABLE ROW LEVEL SECURITY;
