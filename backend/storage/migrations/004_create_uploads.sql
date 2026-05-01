-- Migration 004: uploads table for tracking financial CSV uploads
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS uploads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    storage_path    TEXT,           -- Path in Supabase Storage bucket
    file_type       TEXT NOT NULL DEFAULT 'financial',
    row_count       INTEGER NOT NULL DEFAULT 0,
    columns         TEXT[] NOT NULL DEFAULT '{}',
    upload_status   TEXT NOT NULL DEFAULT 'ready',  -- ready | indexing | indexed | error
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uploads_founder_id ON uploads (founder_id);
CREATE INDEX IF NOT EXISTS idx_uploads_created    ON uploads (created_at DESC);

ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;

CREATE POLICY uploads_select_own
    ON uploads FOR SELECT
    TO authenticated
    USING (founder_id = auth.uid());

CREATE POLICY uploads_insert_own
    ON uploads FOR INSERT
    TO authenticated
    WITH CHECK (founder_id = auth.uid());
