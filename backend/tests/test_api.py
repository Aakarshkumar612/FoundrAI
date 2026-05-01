"""Tests for the backend API layer: all routers, SSE streaming, CORS, validation.

Covers:
- GET /health (no auth)
- POST /upload/financials (auth, file type, size, schema validation)
- POST /query (auth, SSE stream structure)
- POST /simulate (auth, response schema, edge cases)
- GET /charts/embed-token and /charts/dashboards (auth)
- CORS preflight responses
"""

import io
import time
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.main import app
from backend.config import Settings, get_settings


# ── Helpers ───────────────────────────────────────────────────────────────────

TEST_JWT_SECRET = "test-secret-32-chars-long-padded!!"
TEST_USER_ID = "22222222-2222-2222-2222-222222222222"


def _make_token(exp_offset: int = 3600) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": TEST_USER_ID, "role": "authenticated", "iat": now, "exp": now + exp_offset},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


def _mock_settings() -> Settings:
    return Settings(
        supabase_url="",
        supabase_key="test-key",
        supabase_service_role_key="test-service-key",
        supabase_jwt_secret=TEST_JWT_SECRET,
        cors_origins="http://localhost:5173",
        environment="development",
    )


def _csv_bytes(valid: bool = True) -> bytes:
    if valid:
        return b"month,revenue,burn_rate,headcount,cac,ltv\n2026-01,85000,42000,12,450,2100\n"
    return b"col1,col2\n1,2\n"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_settings() -> Generator:
    """Apply mock settings for every test in this module."""
    app.dependency_overrides[get_settings] = _mock_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": f"Bearer {_make_token()}"}


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_no_auth_required(self, client: TestClient) -> None:
        # No Authorization header — should still succeed
        resp = client.get("/health")
        assert resp.status_code == 200


# ── Upload endpoint ───────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_valid_csv_succeeds(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/upload/financials",
            files={"file": ("financials.csv", io.BytesIO(_csv_bytes()), "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "upload_id" in data
        assert data["filename"] == "financials.csv"
        assert data["row_count"] == 1
        assert "revenue" in data["columns"]

    def test_upload_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/upload/financials",
            files={"file": ("financials.csv", io.BytesIO(_csv_bytes()), "text/csv")},
        )
        assert resp.status_code == 401

    def test_upload_wrong_columns_rejected(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/upload/financials",
            files={"file": ("bad.csv", io.BytesIO(_csv_bytes(valid=False)), "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "missing required columns" in resp.json()["detail"]["message"]

    def test_upload_empty_csv_rejected(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/upload/financials",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_upload_oversized_file_rejected(self, client: TestClient, auth_headers: dict) -> None:
        # 11MB of data — exceeds 10MB limit
        big_content = b"revenue,burn_rate,headcount,cac,ltv\n" + b"100,50,10,400,2000\n" * 600_000
        resp = client.post(
            "/upload/financials",
            files={"file": ("big.csv", io.BytesIO(big_content), "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "10MB" in resp.json()["detail"]["message"]

    def test_upload_non_csv_rejected(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/upload/financials",
            files={"file": ("report.pdf", io.BytesIO(b"%PDF-content"), "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── Query / SSE endpoint ──────────────────────────────────────────────────────

class TestQuery:
    def test_query_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/query", json={"question": "What is my runway?"})
        assert resp.status_code == 401

    def test_query_returns_sse_stream(self, client: TestClient, auth_headers: dict) -> None:
        with client.stream(
            "POST", "/query",
            json={"question": "What is my runway?"},
            headers=auth_headers,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            raw = resp.read().decode()

        # Verify key SSE events are present
        assert "event: rag_context" in raw
        assert "event: agent_update" in raw
        assert "event: final" in raw

    def test_query_stream_contains_all_agents(self, client: TestClient, auth_headers: dict) -> None:
        with client.stream(
            "POST", "/query",
            json={"question": "Which segment should I focus on?"},
            headers=auth_headers,
        ) as resp:
            raw = resp.read().decode()

        for agent in ["MarketAgent", "RiskAgent", "RevenueAgent", "StrategyAgent"]:
            assert agent in raw

    def test_query_empty_question_still_streams(self, client: TestClient, auth_headers: dict) -> None:
        with client.stream(
            "POST", "/query",
            json={"question": ""},
            headers=auth_headers,
        ) as resp:
            assert resp.status_code == 200


# ── Simulate endpoint ─────────────────────────────────────────────────────────

class TestSimulate:
    def test_simulate_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/simulate", json={"upload_id": "abc", "months_ahead": 12})
        assert resp.status_code == 401

    def test_simulate_base_scenario(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/simulate",
            json={"upload_id": "test-upload-id", "months_ahead": 12, "growth_scenario": "base"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["forecast"]) == 12
        assert data["simulation_runs"] == 10_000
        assert "runway_months" in data

    def test_simulate_forecast_has_correct_structure(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/simulate",
            json={"upload_id": "x", "months_ahead": 6, "growth_scenario": "bull"},
            headers=auth_headers,
        )
        data = resp.json()
        first = data["forecast"][0]
        assert "month" in first and "p10" in first and "p50" in first and "p90" in first
        # P10 < P50 < P90 always
        assert first["p10"] < first["p50"] < first["p90"]

    def test_simulate_months_capped_at_24(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/simulate",
            json={"upload_id": "x", "months_ahead": 99, "growth_scenario": "base"},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # Pydantic ge/le validation

    def test_simulate_bear_has_lower_revenue_than_bull(self, client: TestClient, auth_headers: dict) -> None:
        bear = client.post(
            "/simulate",
            json={"upload_id": "x", "months_ahead": 12, "growth_scenario": "bear"},
            headers=auth_headers,
        ).json()
        bull = client.post(
            "/simulate",
            json={"upload_id": "x", "months_ahead": 12, "growth_scenario": "bull"},
            headers=auth_headers,
        ).json()
        # Revenue P50 at last forecast month must be higher in bull vs bear
        assert bear["forecast"][-1]["p50"] < bull["forecast"][-1]["p50"]


# ── Charts endpoints ──────────────────────────────────────────────────────────

class TestCharts:
    def test_embed_token_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/charts/embed-token")
        assert resp.status_code == 401

    def test_embed_token_returns_token(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/charts/embed-token", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["expires_in"] > 0

    def test_dashboards_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/charts/dashboards")
        assert resp.status_code == 401

    def test_dashboards_returns_three_dashboards(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/charts/dashboards", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["dashboards"]) == 3
        titles = [d["title"] for d in data["dashboards"]]
        assert "Revenue Overview" in titles
        assert "Unit Economics" in titles
        assert "Growth Health" in titles


# ── CORS ──────────────────────────────────────────────────────────────────────

class TestCORS:
    def test_cors_preflight_allowed_origin(self, client: TestClient) -> None:
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code in (200, 204)
        assert "access-control-allow-origin" in resp.headers

    def test_cors_header_present_on_get(self, client: TestClient) -> None:
        resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" in resp.headers
