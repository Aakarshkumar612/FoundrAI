-- Migration 001: Create founders table
-- Depends on: Supabase auth schema (auth.users must exist)
-- Run this in: Supabase Dashboard → SQL Editor, or via supabase CLI

-- Founders table: one row per authenticated user
CREATE TABLE IF NOT EXISTS public.founders (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL UNIQUE,
    full_name   TEXT,
    company_name TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER founders_updated_at
    BEFORE UPDATE ON public.founders
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Enable Row Level Security
ALTER TABLE public.founders ENABLE ROW LEVEL SECURITY;

-- Policy: founders can SELECT and UPDATE only their own row
CREATE POLICY "founders_select_own" ON public.founders
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "founders_update_own" ON public.founders
    FOR UPDATE USING (auth.uid() = id);

-- INSERT is handled by the backend using service_role (bypasses RLS)
-- DELETE is intentionally not exposed via RLS (admin-only operation)
