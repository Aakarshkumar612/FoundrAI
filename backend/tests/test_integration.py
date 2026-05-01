"""End-to-end integration smoke test — simulates the full founder journey.

Runs entirely in-process via FastAPI TestClient (no real server needed).
External services (Supabase, Groq) are mocked so this is deterministic.

Flow tested:
  1. GET  /health
  2. POST /auth/register
  3. POST /auth/login
  4. GET  /auth/me
  5. POST /upload/financials  (real CSV from data/synthetic/)
  6. POST /query              (SSE stream, all 4 agents)
  7. POST /simulate           (Monte Carlo response)
  8. GET  /charts/embed-token
  9. GET  /charts/dashboards
"""

import io
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.main import app
from backend.config import Settings, get_settings

# ── Test config ───────────────────────────────────────────────────────────────

SECRET = "test-secret-32-chars-long-padded!!"
USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EMAIL   = "founder@teststartup.io"


def _mock_settings() -> Settings:
    return Settings(
        supabase_url="",
        supabase_key="k",
        supabase_service_role_key="sk",
        supabase_jwt_secret=SECRET,
        groq_api_key="gsk_test",
        cors_origins="http://localhost:5173",
        environment="development",
    )


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": USER_ID, "role": "authenticated", "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )


def _groq_resp(content: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    m = MagicMock()
    m.choices = [choice]
    return m


MARKET_JSON   = json.dumps({"market_size_assessment":"TAM $50B","competitor_threats":["A"],"opportunity_areas":["B"],"confidence":0.8})
RISK_JSON     = json.dumps({"risk_score":5.0,"primary_risks":[{"risk":"CAC rising","severity":"high"}],"runway_assessment":"14 months","mitigation_recommendations":["Cut spend"]})
REVENUE_JSON  = json.dumps({"forecast_narrative":"ARR $2M in 12mo","key_drivers":["Upsell"],"growth_levers":["Pricing"],"forecast_confidence":"medium"})
STRATEGY_JSON = json.dumps({"executive_summary":"Focus on retention","top_3_recommendations":["R1","R2","R3"],"immediate_actions":["A1"],"30_60_90_day_plan":{"30_days":["T1"],"60_days":["T2"],"90_days":["T3"]}})

FOUNDER_ROW = {
    "id": USER_ID, "email": EMAIL,
    "full_name": "Test Founder", "company_name": "TestCo",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


def _mock_sb_register() -> MagicMock:
    user = MagicMock(); user.id = USER_ID
    session = MagicMock()
    session.access_token = _token()
    session.refresh_token = "refresh-xyz"
    session.expires_in = 3600
    auth = MagicMock(); auth.user = user; auth.session = session
    sb = MagicMock()
    sb.auth.sign_up.return_value = auth
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[FOUNDER_ROW])
    return sb


def _mock_sb_login() -> MagicMock:
    user = MagicMock(); user.id = USER_ID
    session = MagicMock()
    session.access_token = _token()
    session.refresh_token = "refresh-xyz"
    session.expires_in = 3600
    auth = MagicMock(); auth.user = user; auth.session = session
    sb = MagicMock()
    sb.auth.sign_in_with_password.return_value = auth
    (sb.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.return_value) = MagicMock(data=FOUNDER_ROW)
    return sb


def _mock_groq() -> MagicMock:
    groq = MagicMock()
    groq.chat.completions.create.side_effect = [
        _groq_resp(MARKET_JSON),
        _groq_resp(RISK_JSON),
        _groq_resp(REVENUE_JSON),
        _groq_resp(STRATEGY_JSON),
    ]
    return groq


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override():
    app.dependency_overrides[get_settings] = _mock_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestFullFounderJourney:

    def test_01_health_check(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        print(f"\n✅ /health → {data}")

    def test_02_register(self, client):
        with patch("backend.auth.router.create_client", return_value=_mock_sb_register()):
            r = client.post("/auth/register", json={
                "email": EMAIL, "password": "securepass123",
                "full_name": "Test Founder", "company_name": "TestCo",
            })
        assert r.status_code == 201
        data = r.json()
        assert data["tokens"]["access_token"]
        assert data["founder"]["email"] == EMAIL
        print(f"\n✅ /auth/register → founder id: {data['founder']['id']}")

    def test_03_login(self, client):
        with patch("backend.auth.router.create_client", return_value=_mock_sb_login()):
            r = client.post("/auth/login", json={"email": EMAIL, "password": "securepass123"})
        assert r.status_code == 200
        data = r.json()
        assert data["tokens"]["token_type"] == "bearer"
        print(f"\n✅ /auth/login → token received, expires_in: {data['tokens']['expires_in']}s")

    def test_04_get_me(self, client):
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == USER_ID
        print(f"\n✅ /auth/me → id: {data['id']}")

    def test_05_upload_financials(self, client):
        csv_path = Path("data/synthetic/financials.csv")
        csv_bytes = csv_path.read_bytes() if csv_path.exists() else (
            b"month,revenue,burn_rate,headcount,cac,ltv\n"
            b"2026-01,85000,42000,12,450,2100\n"
            b"2026-02,92000,43000,13,440,2150\n"
        )
        r = client.post(
            "/upload/financials",
            files={"file": ("financials.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["upload_id"]
        assert "revenue" in [c.lower() for c in data["columns"]]
        print(f"\n✅ /upload/financials → upload_id: {data['upload_id']}, rows: {data['row_count']}, cols: {data['columns']}")

    def test_06_query_sse_stream(self, client):
        groq_mock = _mock_groq()
        with patch("backend.agents.orchestrator.Groq", return_value=groq_mock), \
             client.stream(
                 "POST", "/query",
                 json={"question": "What is my runway if CAC increases 20%?"},
                 headers={"Authorization": f"Bearer {_token()}"},
             ) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            raw = r.read().decode()

        events = [line for line in raw.split("\n") if line.startswith("event:")]
        print(f"\n✅ /query → SSE events received:")
        for e in events:
            print(f"   {e}")

        assert "event: rag_context" in raw
        assert "event: agent_update" in raw
        assert "MarketAgent" in raw
        assert "RiskAgent" in raw
        assert "RevenueAgent" in raw
        assert "StrategyAgent" in raw
        assert "event: final" in raw

    def test_07_simulate_base_scenario(self, client):
        r = client.post("/simulate", json={
            "upload_id": "fake-upload-id",
            "months_ahead": 12,
            "cac_change_pct": 0.20,
            "burn_change_pct": 0.05,
            "growth_scenario": "base",
        }, headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["forecast"]) == 12
        assert data["simulation_runs"] == 10_000
        first = data["forecast"][0]
        assert first["p10"] < first["p50"] < first["p90"]
        print(f"\n✅ /simulate → runway: {data['runway_months']} months, model: {data['model_used']}")
        print(f"   Month 1 → P10: ${first['p10']:,.0f} | P50: ${first['p50']:,.0f} | P90: ${first['p90']:,.0f}")

    def test_08_simulate_all_scenarios(self, client):
        results = {}
        for scenario in ("bear", "base", "bull"):
            r = client.post("/simulate", json={
                "upload_id": "x", "months_ahead": 6, "growth_scenario": scenario,
            }, headers={"Authorization": f"Bearer {_token()}"})
            assert r.status_code == 200
            results[scenario] = r.json()["forecast"][-1]["p50"]  # last month revenue P50
        assert results["bear"] < results["base"] < results["bull"]
        print(f"\n✅ /simulate scenarios → bear P50: ${results['bear']:,.0f} | base: ${results['base']:,.0f} | bull: ${results['bull']:,.0f}")

    def test_09_embed_token(self, client):
        r = client.get("/charts/embed-token", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        data = r.json()
        assert data["token"]
        assert data["expires_in"] > 0
        print(f"\n✅ /charts/embed-token → token: {data['token']}, expires_in: {data['expires_in']}s")

    def test_10_dashboards(self, client):
        r = client.get("/charts/dashboards", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["dashboards"]) == 3
        titles = [d["title"] for d in data["dashboards"]]
        print(f"\n✅ /charts/dashboards → {titles}")
