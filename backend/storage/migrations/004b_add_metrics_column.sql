-- Migration 004b: add initial_metrics JSON column to uploads table
-- Run in Supabase SQL Editor after 004_create_uploads.sql

ALTER TABLE uploads
    ADD COLUMN IF NOT EXISTS initial_metrics JSONB DEFAULT '{}'::jsonb;
