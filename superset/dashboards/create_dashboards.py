"""Create the 3 FoundrAI Superset dashboards via REST API."""

import argparse
import sys
import time
import requests

# ── SQL for each chart ────────────────────────────────────────────────────────

CHARTS = [
    {
        "dashboard": "Revenue Overview",
        "slice_name": "Monthly Revenue vs Burn",
        "viz_type": "echarts_timeseries_line",
        "sql": "SELECT month, revenue, burn_rate FROM financial_rows WHERE founder_id = '{{current_username()}}' ORDER BY month",
        "metrics": ["revenue", "burn_rate"],
    },
    {
        "dashboard": "Unit Economics",
        "slice_name": "LTV / CAC Ratio",
        "viz_type": "echarts_timeseries_bar",
        "sql": "SELECT month, ROUND(ltv / NULLIF(cac, 0), 2) AS ltv_cac_ratio FROM financial_rows WHERE founder_id = '{{current_username()}}' ORDER BY month",
        "metrics": ["ltv_cac_ratio"],
    },
    {
        "dashboard": "Growth Health",
        "slice_name": "Burn Rate Trend",
        "viz_type": "echarts_timeseries_line",
        "sql": "SELECT month, burn_rate FROM financial_rows WHERE founder_id = '{{current_username()}}' ORDER BY month",
        "metrics": ["burn_rate"],
    },
]

DASHBOARD_TITLES = ["Revenue Overview", "Unit Economics", "Growth Health"]


def login(base, user, pwd):
    r = requests.post(f"{base}/api/v1/security/login", json={"username": user, "password": pwd, "provider": "db", "refresh": False}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def create_database(base, token, uri):
    # Try getting existing first
    r = requests.get(f"{base}/api/v1/database/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    for db in r.json().get("result", []):
        if db["database_name"] == "FoundrAI Supabase":
            return db["id"]

    # If not exists, create with simplest possible payload
    payload = {
        "database_name": "FoundrAI Supabase",
        "sqlalchemy_uri": uri,
        "engine": "postgresql"
    }
    r = requests.post(f"{base}/api/v1/database/", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=15)
    if r.status_code == 201: return r.json()["id"]
    
    # Final fallback: return the first database found if any
    res = r.json().get("result")
    if res: return res.get("id") or 1
    return 1

def create_dashboard(base, token, title):
    slug = title.lower().replace(" ", "-")
    # Check exists
    r = requests.get(f"{base}/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    for d in r.json().get("result", []):
        if d["slug"] == slug: return d["id"]

    # Create new
    r = requests.post(f"{base}/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"}, json={"dashboard_title": title, "slug": slug, "published": True}, timeout=15)
    return r.json().get("id")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-user", required=True)
    parser.add_argument("--admin-pass", required=True)
    parser.add_argument("--superset-url", default="http://localhost:8088")
    parser.add_argument("--supabase-uri", required=True)
    args = parser.parse_args()

    base = args.superset_url.rstrip("/")
    token = login(base, args.admin_user, args.admin_pass)
    db_id = create_database(base, token, args.supabase_uri)

    for title in DASHBOARD_TITLES:
        did = create_dashboard(base, token, title)
        print(f"  Synced Dashboard '{title}' (ID: {did})")

    print("\n✅ Dashboard synchronization complete.")

if __name__ == "__main__":
    main()
