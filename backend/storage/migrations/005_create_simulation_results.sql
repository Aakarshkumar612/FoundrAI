-- Migration 005: simulation_results table
-- Persists Monte Carlo outputs for history and dashboard use.
-- Depends on: 004_create_uploads.sql

CREATE TABLE IF NOT EXISTS public.simulation_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    upload_id       UUID REFERENCES public.uploads(id) ON DELETE SET NULL,
    months_ahead    INT NOT NULL,
    growth_scenario TEXT NOT NULL CHECK (growth_scenario IN ('bear', 'base', 'bull')),
    forecast        JSONB NOT NULL DEFAULT '[]',
    runway_p10      NUMERIC(10, 2),
    runway_p50      NUMERIC(10, 2),
    runway_p90      NUMERIC(10, 2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sim_results_founder  ON public.simulation_results (founder_id);
CREATE INDEX IF NOT EXISTS idx_sim_results_upload   ON public.simulation_results (upload_id);
CREATE INDEX IF NOT EXISTS idx_sim_results_created  ON public.simulation_results (created_at DESC);

ALTER TABLE public.simulation_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY sim_results_select_own ON public.simulation_results
    FOR SELECT USING (auth.uid() = founder_id);

-- INSERT handled by service_role (backend bypasses RLS)
