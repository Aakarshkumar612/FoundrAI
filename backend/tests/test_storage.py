"""Tests for Layer 8: Supabase client factory, GCS client, wired upload/simulate."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.storage.supabase_client import get_supabase_client, reset_client


# ── Supabase client factory tests ─────────────────────────────────────────────

class TestSupabaseClient:
    def setup_method(self):
        reset_client()

    def teardown_method(self):
        reset_client()

    def test_returns_none_when_url_missing(self):
        with patch("backend.storage.supabase_client.get_settings") as ms:
            ms.return_value.supabase_url = ""
            ms.return_value.supabase_service_role_key = "key"
            result = get_supabase_client()
        assert result is None

    def test_returns_none_when_key_missing(self):
        with patch("backend.storage.supabase_client.get_settings") as ms:
            ms.return_value.supabase_url = "https://x.supabase.co"
            ms.return_value.supabase_service_role_key = ""
            result = get_supabase_client()
        assert result is None

    def test_returns_client_when_configured(self):
        mock_client = MagicMock()
        with (
            patch("backend.storage.supabase_client.get_settings") as ms,
            patch("backend.storage.supabase_client.create_client", return_value=mock_client),
        ):
            ms.return_value.supabase_url = "https://x.supabase.co"
            ms.return_value.supabase_service_role_key = "service-key"
            result = get_supabase_client()
        assert result is mock_client

    def test_singleton_returns_same_instance(self):
        mock_client = MagicMock()
        with (
            patch("backend.storage.supabase_client.get_settings") as ms,
            patch("backend.storage.supabase_client.create_client", return_value=mock_client),
        ):
            ms.return_value.supabase_url = "https://x.supabase.co"
            ms.return_value.supabase_service_role_key = "service-key"
            c1 = get_supabase_client()
            c2 = get_supabase_client()
        assert c1 is c2

    def test_reset_causes_reinitialisation(self):
        mock_client = MagicMock()
        with (
            patch("backend.storage.supabase_client.get_settings") as ms,
            patch("backend.storage.supabase_client.create_client", return_value=mock_client) as mc,
        ):
            ms.return_value.supabase_url = "https://x.supabase.co"
            ms.return_value.supabase_service_role_key = "service-key"
            get_supabase_client()
            reset_client()
            get_supabase_client()
        assert mc.call_count == 2


# ── Upload endpoint wiring tests ──────────────────────────────────────────────

VALID_CSV = (
    b"month,revenue,burn_rate,headcount,cac,ltv\n"
    b"2026-01,85000,42000,12,450,2100\n"
    b"2026-02,92000,43000,13,455,2150\n"
)


class TestUploadWiring:
    def test_upload_succeeds_without_supabase(self):
        from backend.main import app
        from backend.auth.middleware import verify_jwt
        app.dependency_overrides[verify_jwt] = lambda: {"sub": "test-id", "role": "founder"}
        client = TestClient(app)

        with (
            patch("backend.routers.upload.get_supabase_client", return_value=None),
            patch("backend.rag.indexer.get_encoder") as me,
        ):
            import numpy as np
            me.return_value.encode.return_value = np.ones((1, 384), dtype="float32")
            resp = client.post(
                "/upload/financials",
                files={"file": ("fin.csv", VALID_CSV, "text/csv")},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 201
        data = resp.json()
        assert data["row_count"] == 2
        assert "upload_id" in data
        assert data["is_financial"] is True

    def test_upload_persists_metrics_to_supabase(self):
        from backend.main import app
        from backend.auth.middleware import verify_jwt

        sb = MagicMock()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        sb.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
        sb.rpc.return_value.execute.return_value = MagicMock(data=[])

        app.dependency_overrides[verify_jwt] = lambda: {"sub": "test-id", "role": "founder"}
        client = TestClient(app)

        with (
            patch("backend.routers.upload.get_supabase_client", return_value=sb),
            patch("backend.rag.indexer.get_encoder") as me,
        ):
            import numpy as np
            me.return_value.encode.return_value = np.ones((1, 384), dtype="float32")
            resp = client.post(
                "/upload/financials",
                files={"file": ("fin.csv", VALID_CSV, "text/csv")},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 201
        # Verify insert was called with initial_metrics key
        insert_call_kwargs = sb.table.return_value.insert.call_args[0][0]
        assert "initial_metrics" in insert_call_kwargs
        assert insert_call_kwargs["initial_metrics"]["revenue"] == 92_000.0


# ── Simulate wiring tests ─────────────────────────────────────────────────────

class TestSimulateWiring:
    def test_simulate_falls_back_to_defaults_when_no_supabase(self):
        from backend.main import app
        from backend.auth.middleware import verify_jwt
        app.dependency_overrides[verify_jwt] = lambda: {"sub": "test-id", "role": "founder"}
        client = TestClient(app)

        with patch("backend.routers.simulate.get_supabase_client", return_value=None):
            resp = client.post("/simulate", json={
                "upload_id": "no-such-id",
                "months_ahead": 6,
                "growth_scenario": "base",
            })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["forecast"]) == 6
        assert data["simulation_runs"] == 10_000

    def test_simulate_uses_metrics_from_supabase(self):
        from backend.main import app
        from backend.auth.middleware import verify_jwt
        app.dependency_overrides[verify_jwt] = lambda: {"sub": "test-id", "role": "founder"}
        client = TestClient(app)

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value\
            .single.return_value.execute.return_value = MagicMock(
                data={"initial_metrics": {"revenue": 200_000.0, "burn_rate": 80_000.0}}
            )

        with patch("backend.routers.simulate.get_supabase_client", return_value=sb):
            resp = client.post("/simulate", json={
                "upload_id": "real-upload-id",
                "months_ahead": 6,
                "growth_scenario": "base",
            })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        # Revenue=200k seed → month 1 P50 much higher than default 85k
        assert resp.json()["forecast"][0]["p50"] > 85_000

    def test_simulate_persists_result_when_supabase_available(self):
        from backend.main import app
        from backend.auth.middleware import verify_jwt
        app.dependency_overrides[verify_jwt] = lambda: {"sub": "test-id", "role": "founder"}
        client = TestClient(app)

        sb = MagicMock()
        # _fetch_metrics call chain
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value\
            .single.return_value.execute.return_value = MagicMock(data={})
        # _persist_result insert chain
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock()

        with patch("backend.routers.simulate.get_supabase_client", return_value=sb):
            resp = client.post("/simulate", json={
                "upload_id": "upload-abc",
                "months_ahead": 3,
                "growth_scenario": "base",
            })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["simulation_id"] is not None
        # Verify insert was called with correct table
        sb.table.assert_any_call("simulation_results")

    def test_simulate_returns_none_simulation_id_without_supabase(self):
        from backend.main import app
        from backend.auth.middleware import verify_jwt
        app.dependency_overrides[verify_jwt] = lambda: {"sub": "test-id", "role": "founder"}
        client = TestClient(app)

        with patch("backend.routers.simulate.get_supabase_client", return_value=None):
            resp = client.post("/simulate", json={
                "upload_id": "no-id",
                "months_ahead": 3,
                "growth_scenario": "bull",
            })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["simulation_id"] is None


# ── Founders router tests ─────────────────────────────────────────────────────

class TestFoundersRouter:
    def _make_client(self, sb=None):
        from backend.main import app
        from backend.auth.middleware import verify_jwt
        app.dependency_overrides[verify_jwt] = lambda: {"sub": "founder-001", "email": "test@example.com", "role": "founder"}
        return TestClient(app), app

    def test_get_profile_returns_id_when_no_supabase(self):
        client, app = self._make_client()
        with patch("backend.routers.founders.get_supabase_client", return_value=None):
            resp = client.get("/founders/profile")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["id"] == "founder-001"

    def test_get_profile_returns_db_data(self):
        client, app = self._make_client()
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value\
            .maybe_single.return_value.execute.return_value = MagicMock(
                data={"id": "founder-001", "email": "test@example.com",
                      "full_name": "Ada Lovelace", "company_name": "ByteCo",
                      "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"}
            )
        with patch("backend.routers.founders.get_supabase_client", return_value=sb):
            resp = client.get("/founders/profile")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Ada Lovelace"
        assert data["company_name"] == "ByteCo"

    def test_patch_profile_no_supabase(self):
        client, app = self._make_client()
        with patch("backend.routers.founders.get_supabase_client", return_value=None):
            resp = client.patch("/founders/profile", json={"company_name": "StartupX"})
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "StartupX"

    def test_patch_profile_calls_upsert(self):
        client, app = self._make_client()
        sb = MagicMock()
        sb.table.return_value.upsert.return_value.execute.return_value = MagicMock(
            data=[{"id": "founder-001", "email": "test@example.com",
                   "full_name": None, "company_name": "StartupX",
                   "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"}]
        )
        with patch("backend.routers.founders.get_supabase_client", return_value=sb):
            resp = client.patch("/founders/profile", json={"company_name": "StartupX"})
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        upsert_payload = sb.table.return_value.upsert.call_args[0][0]
        assert upsert_payload["company_name"] == "StartupX"
        assert upsert_payload["id"] == "founder-001"

    def test_list_uploads_returns_empty_without_supabase(self):
        client, app = self._make_client()
        with patch("backend.routers.founders.get_supabase_client", return_value=None):
            resp = client.get("/founders/uploads")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["uploads"] == []
        assert data["total"] == 0
        assert data["has_next"] is False

    def test_list_uploads_returns_paginated_results(self):
        client, app = self._make_client()
        sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "uid-1", "filename": "fin.csv", "file_type": "financial",
             "row_count": 24, "columns": ["month", "revenue"], "upload_status": "indexed",
             "created_at": "2026-01-01T00:00:00Z"},
        ]
        mock_result.count = 1
        (sb.table.return_value.select.return_value.eq.return_value
         .neq.return_value.order.return_value.range.return_value.execute
         .return_value) = mock_result
        with patch("backend.routers.founders.get_supabase_client", return_value=sb):
            resp = client.get("/founders/uploads?page=1&page_size=20")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploads"]) == 1
        assert data["uploads"][0]["filename"] == "fin.csv"
        assert data["total"] == 1

    def test_get_upload_404_when_not_found(self):
        client, app = self._make_client()
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value\
            .single.return_value.execute.side_effect = Exception("not found")
        with patch("backend.routers.founders.get_supabase_client", return_value=sb):
            resp = client.get("/founders/uploads/nonexistent-id")
        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_delete_upload_503_without_supabase(self):
        client, app = self._make_client()
        with patch("backend.routers.founders.get_supabase_client", return_value=None):
            resp = client.delete("/founders/uploads/some-id")
        app.dependency_overrides.clear()
        assert resp.status_code == 503

    def test_delete_upload_calls_hard_delete(self):
        client, app = self._make_client()
        sb = MagicMock()
        # Mock fetch result for single()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"filename": "test.csv", "storage_path": "path"})
        
        with patch("backend.routers.founders.get_supabase_client", return_value=sb):
            resp = client.delete("/founders/uploads/uid-1")
        app.dependency_overrides.clear()
        assert resp.status_code == 204
        
        # Verify document_embeddings delete was called
        sb.table.assert_any_call("document_embeddings")
        # Verify uploads delete was called
        sb.table.assert_any_call("uploads")
        # Verify storage remove was called
        sb.storage.from_.return_value.remove.assert_called_once_with(["path"])
