#!/usr/bin/env bash
# Bootstrap Superset for FoundrAI: DB upgrade → admin user → Supabase connection → dashboards.
# Run inside the superset container:
#   docker compose -f superset/docker-compose.yml exec superset bash /app/init.sh
set -euo pipefail

ADMIN_USER="${SUPERSET_ADMIN_USER:-admin}"
ADMIN_PASS="${SUPERSET_ADMIN_PASS:-admin}"
ADMIN_EMAIL="${SUPERSET_ADMIN_EMAIL:-admin@foundrai.com}"
SUPABASE_URI="${SUPABASE_DB_URI:-}"   # postgresql://postgres:<pass>@db.<ref>.supabase.co:5432/postgres

echo "==> Upgrading Superset DB schema..."
superset db upgrade

echo "==> Initialising roles and permissions..."
superset init

echo "==> Creating admin user (idempotent)..."
superset fab create-admin \
  --username  "$ADMIN_USER" \
  --firstname Superset \
  --lastname  Admin \
  --email     "$ADMIN_EMAIL" \
  --password  "$ADMIN_PASS" 2>/dev/null || echo "   Admin already exists — skipping."

if [ -z "$SUPABASE_URI" ]; then
  echo "⚠  SUPABASE_DB_URI not set — skipping database connection and dashboard import."
  echo "   Set SUPABASE_DB_URI and re-run to create dashboards."
  exit 0
fi

echo "==> Registering Supabase database connection..."
python3 /app/dashboards/create_dashboards.py \
  --admin-user  "$ADMIN_USER" \
  --admin-pass  "$ADMIN_PASS" \
  --superset-url "http://localhost:8088" \
  --supabase-uri "$SUPABASE_URI"

echo "==> Done. Open http://localhost:8088 and embed dashboards in FoundrAI."
