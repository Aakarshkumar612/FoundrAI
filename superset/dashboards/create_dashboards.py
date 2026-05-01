"""Create the 3 FoundrAI Superset dashboards via REST API.

Called by init.sh after the Supabase DB connection is registered.
Uses Superset's /api/v1/ endpoints to create:
  - Database connection  (Supabase PostgreSQL)
  - Dataset             (financial_rows view per founder)
  - Charts              (Revenue, Unit Economics, Growth Health)
  - Dashboards          (one per theme, 3 charts each)
"""

import argparse
import sys
import time
import requests

# ── SQL for each chart ────────────────────────────────────────────────────────

CHARTS = [
    # ── Revenue Overview ──────────────────────────────────────────────────────
    {
        "dashboard": "Revenue Overview",
        "slice_name": "Monthly Revenue vs Burn",
        "viz_type": "echarts_timeseries_line",
        "sql": """
            SELECT month, revenue, burn_rate
            FROM financial_rows
            WHERE founder_id = '{{current_username()}}'
            ORDER BY month
        """,
        "metrics": ["revenue", "burn_rate"],
    },
    {
        "dashboard": "Revenue Overview",
        "slice_name": "MoM Revenue Growth %",
        "viz_type": "echarts_timeseries_bar",
        "sql": """
            SELECT month,
                   ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
                         / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 2) AS mom_growth_pct
            FROM financial_rows
            WHERE founder_id = '{{current_username()}}'
            ORDER BY month
        """,
        "metrics": ["mom_growth_pct"],
    },
    {
        "dashboard": "Revenue Overview",
        "slice_name": "Burn Coverage Ratio",
        "viz_type": "echarts_timeseries_line",
        "sql": """
            SELECT month,
                   ROUND(revenue / NULLIF(burn_rate, 0), 3) AS burn_coverage
            FROM financial_rows
            WHERE founder_id = '{{current_username()}}'
            ORDER BY month
        """,
        "metrics": ["burn_coverage"],
    },
    # ── Unit Economics ────────────────────────────────────────────────────────
    {
        "dashboard": "Unit Economics",
        "slice_name": "CAC over Time",
        "viz_type": "echarts_timeseries_line",
        "sql": """
            SELECT month, cac FROM financial_rows
            WHERE founder_id = '{{current_username()}}' ORDER BY month
        """,
        "metrics": ["cac"],
    },
    {
        "dashboard": "Unit Economics",
        "slice_name": "LTV over Time",
        "viz_type": "echarts_timeseries_line",
        "sql": """
            SELECT month, ltv FROM financial_rows
            WHERE founder_id = '{{current_username()}}' ORDER BY month
        """,
        "metrics": ["ltv"],
    },
    {
        "dashboard": "Unit Economics",
        "slice_name": "LTV / CAC Ratio",
        "viz_type": "echarts_timeseries_bar",
        "sql": """
            SELECT month,
                   ROUND(ltv / NULLIF(cac, 0), 2) AS ltv_cac_ratio
            FROM financial_rows
            WHERE founder_id = '{{current_username()}}' ORDER BY month
        """,
        "metrics": ["ltv_cac_ratio"],
    },
    # ── Growth Health ─────────────────────────────────────────────────────────
    {
        "dashboard": "Growth Health",
        "slice_name": "Headcount Growth",
        "viz_type": "echarts_timeseries_bar",
        "sql": """
            SELECT month, headcount FROM financial_rows
            WHERE founder_id = '{{current_username()}}' ORDER BY month
        """,
        "metrics": ["headcount"],
    },
    {
        "dashboard": "Growth Health",
        "slice_name": "Revenue per Head",
        "viz_type": "echarts_timeseries_line",
        "sql": """
            SELECT month,
                   ROUND(revenue / NULLIF(headcount, 0), 2) AS revenue_per_head
            FROM financial_rows
            WHERE founder_id = '{{current_username()}}' ORDER BY month
        """,
        "metrics": ["revenue_per_head"],
    },
    {
        "dashboard": "Growth Health",
        "slice_name": "Burn Rate Trend",
        "viz_type": "echarts_timeseries_line",
        "sql": """
            SELECT month, burn_rate FROM financial_rows
            WHERE founder_id = '{{current_username()}}' ORDER BY month
        """,
        "metrics": ["burn_rate"],
    },
]

DASHBOARD_TITLES = ["Revenue Overview", "Unit Economics", "Growth Health"]


def login(base: str, user: str, pwd: str) -> str:
    r = requests.post(f"{base}/api/v1/security/login",
                      json={"username": user, "password": pwd, "provider": "db", "refresh": False},
                      timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def csrf_token(base: str, token: str) -> str:
    r = requests.get(f"{base}/api/v1/security/csrf_token/", headers=headers(token), timeout=10)
    r.raise_for_status()
    return r.json()["result"]


def create_database(base: str, token: str, uri: str) -> int:
    payload = {
        "database_name": "FoundrAI Supabase",
        "sqlalchemy_uri": uri,
        "expose_in_sqllab": True,
        "allow_dml": False,
    }
    r = requests.post(f"{base}/api/v1/database/", headers=headers(token), json=payload, timeout=15)
    if r.status_code == 422 and "already exists" in r.text:
        # fetch existing
        r2 = requests.get(f"{base}/api/v1/database/?q=(filters:!((col:database_name,opr:eq,val:'FoundrAI Supabase')))",
                          headers=headers(token), timeout=10)
        return r2.json()["result"][0]["id"]
    r.raise_for_status()
    return r.json()["id"]


def create_dataset(base: str, token: str, db_id: int, sql: str, name: str) -> int:
    payload = {
        "database": db_id,
        "schema": "public",
        "sql": sql.strip(),
        "table_name": name,
    }
    r = requests.post(f"{base}/api/v1/dataset/", headers=headers(token), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()["id"]


def create_chart(base: str, token: str, chart: dict, dataset_id: int, dashboard_id: int) -> int:
    payload = {
        "slice_name": chart["slice_name"],
        "viz_type": chart["viz_type"],
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": '{"metrics": ' + str(chart["metrics"]) + '}',
        "dashboards": [dashboard_id],
    }
    r = requests.post(f"{base}/api/v1/chart/", headers=headers(token), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()["id"]


def create_dashboard(base: str, token: str, title: str) -> int:
    r = requests.post(f"{base}/api/v1/dashboard/",
                      headers=headers(token),
                      json={"dashboard_title": title, "published": True},
                      timeout=15)
    r.raise_for_status()
    return r.json()["id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-user",   required=True)
    parser.add_argument("--admin-pass",   required=True)
    parser.add_argument("--superset-url", default="http://localhost:8088")
    parser.add_argument("--supabase-uri", required=True)
    args = parser.parse_args()

    base = args.superset_url.rstrip("/")

    print("  Logging in to Superset...")
    token = login(base, args.admin_user, args.admin_pass)

    print("  Registering Supabase database connection...")
    db_id = create_database(base, token, args.supabase_uri)
    print(f"  Database id={db_id}")

    # Create dashboards first so charts can reference them
    dash_ids: dict[str, int] = {}
    for title in DASHBOARD_TITLES:
        did = create_dashboard(base, token, title)
        dash_ids[title] = did
        print(f"  Dashboard '{title}' id={did}")

    # Create one dataset + chart per chart definition
    for chart in CHARTS:
        ds_id = create_dataset(base, token, db_id, chart["sql"], chart["slice_name"])
        dash_id = dash_ids[chart["dashboard"]]
        c_id = create_chart(base, token, chart, ds_id, dash_id)
        print(f"  Chart '{chart['slice_name']}' id={c_id} → dashboard '{chart['dashboard']}'")

    print("\n  All dashboards created successfully.")


if __name__ == "__main__":
    main()
