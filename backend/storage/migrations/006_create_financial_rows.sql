-- Migration 006: financial_rows — stores every row from uploaded financial CSVs
-- Powers Superset dashboards (Revenue Overview, Unit Economics, Growth Health)
-- Run after 005_create_simulation_results.sql

CREATE TABLE IF NOT EXISTS financial_rows (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id   UUID NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    founder_id  UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    month       TEXT NOT NULL,
    revenue     NUMERIC(15,2),
    burn_rate   NUMERIC(15,2),
    headcount   INTEGER,
    cac         NUMERIC(15,2),
    ltv         NUMERIC(15,2),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_finrows_founder ON financial_rows (founder_id);
CREATE INDEX IF NOT EXISTS idx_finrows_upload  ON financial_rows (upload_id);
CREATE INDEX IF NOT EXISTS idx_finrows_month   ON financial_rows (founder_id, month);

ALTER TABLE financial_rows ENABLE ROW LEVEL SECURITY;

CREATE POLICY finrows_select_own
    ON financial_rows FOR SELECT TO authenticated
    USING (founder_id = auth.uid());

CREATE POLICY finrows_insert_own
    ON financial_rows FOR INSERT TO authenticated
    WITH CHECK (founder_id = auth.uid());
