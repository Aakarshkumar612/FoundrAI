"""Create the 3 FoundrAI Superset dashboards via REST API and ENABLE embedding."""

import argparse
import sys
import time
import requests

DASHBOARD_TITLES = ["Revenue Overview", "Unit Economics", "Growth Health"]

def login(base, user, pwd):
    r = requests.post(f"{base}/api/v1/security/login", json={"username": user, "password": pwd, "provider": "db", "refresh": False}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def create_database(base, token, uri):
    r = requests.get(f"{base}/api/v1/database/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    for db in r.json().get("result", []):
        if db["database_name"] == "FoundrAI Supabase": return db["id"]
    payload = {"database_name": "FoundrAI Supabase", "sqlalchemy_uri": uri, "engine": "postgresql"}
    r = requests.post(f"{base}/api/v1/database/", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=15)
    return r.json().get("id") or 1

def setup_dashboard(base, token, title):
    slug = title.lower().replace(" ", "-")
    # 1. Get or Create Dashboard
    r = requests.get(f"{base}/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    dash_id = None
    for d in r.json().get("result", []):
        if d["slug"] == slug: 
            dash_id = d["id"]
            break

    if not dash_id:
        r = requests.post(f"{base}/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"}, json={"dashboard_title": title, "slug": slug, "published": True}, timeout=15)
        dash_id = r.json().get("id")

    # 2. ENABLE EMBEDDING (Crucial for 404 fix)
    # The 'embedded' ID is what the frontend actually needs.
    # Try to GET existing first
    r_get = requests.get(f"{base}/api/v1/dashboard/{dash_id}/embedded", headers={"Authorization": f"Bearer {token}"})
    if r_get.status_code == 200:
        embedded_id = r_get.json()["result"]["uuid"]
    else:
        # Create it
        embed_payload = {"allowed_domains": ["localhost", "127.0.0.1"]}
        r_embed = requests.post(f"{base}/api/v1/dashboard/{dash_id}/embedded", headers={"Authorization": f"Bearer {token}"}, json=embed_payload)
        embedded_id = r_embed.json()["result"]["uuid"]

    return slug, embedded_id

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-user", required=True)
    parser.add_argument("--admin-pass", required=True)
    parser.add_argument("--superset-url", default="http://localhost:8088")
    parser.add_argument("--supabase-uri", required=True)
    args = parser.parse_args()

    base = args.superset_url.rstrip("/")
    token = login(base, args.admin_user, args.admin_pass)
    create_database(base, token, args.supabase_uri)

    for title in DASHBOARD_TITLES:
        try:
            slug, embedded_id = setup_dashboard(base, token, title)
            print(f"  Dashboard '{title}' -> Slug: {slug}, Embedded ID: {embedded_id}")
        except Exception as e:
            print(f"  ❌ Error syncing {title}: {e}")

    print("\n✅ Superset Sync Complete. Use the Embedded IDs above in backend/routers/charts.py")

if __name__ == "__main__":
    main()
