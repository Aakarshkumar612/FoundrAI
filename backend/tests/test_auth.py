"""Tests for the auth layer: middleware, register/login/me flows, token validation.

Covers:
- JWT decode success and failure paths (expired, malformed, missing)
- /auth/register and /auth/login with mocked Supabase responses
- /auth/me with valid and invalid tokens
- /auth/logout (best-effort, always succeeds)
- MFA enroll flow (Supabase mocked)
"""

import time
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from backend.auth.router import router as auth_router
from backend.config import Settings, get_settings

# ── Constants ─────────────────────────────────────────────────────────────────

TEST_JWT_SECRET = "test-secret-32-chars-long-padded!!"
TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
TEST_EMAIL = "founder@example.com"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_token(
    sub: str = TEST_USER_ID,
    secret: str = TEST_JWT_SECRET,
    role: str = "authenticated",
    exp_offset: int = 3600,
) -> str:
    """Create a signed HS256 JWT for testing."""
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "role": role, "iat": now, "exp": now + exp_offset},
        secret,
        algorithm="HS256",
    )


def _mock_settings() -> Settings:
    """Settings with test JWT secret and empty Supabase URLs (skips live DB lookup)."""
    return Settings(
        supabase_url="",
        supabase_key="test-key",
        supabase_service_role_key="test-service-key",
        supabase_jwt_secret=TEST_JWT_SECRET,
        environment="development",
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(auth_router)
    # Override settings so middleware uses TEST_JWT_SECRET
    application.dependency_overrides[get_settings] = _mock_settings
    return application


@pytest.fixture
def client(app: FastAPI) -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": f"Bearer {_make_token()}"}


# ── Middleware / verify_jwt tests ──────────────────────────────────────────────

class TestVerifyJWT:
    def test_missing_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/auth/me")
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "API_AUTH_001"

    def test_malformed_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "API_AUTH_001"

    def test_expired_token_returns_401(self, client: TestClient) -> None:
        token = _make_token(exp_offset=-10)  # expired 10 seconds ago
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "API_AUTH_001"

    def test_wrong_secret_returns_401(self, client: TestClient) -> None:
        token = _make_token(secret="completely-wrong-secret-value-here")
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_valid_token_passes_and_returns_profile(self, client: TestClient) -> None:
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {_make_token()}"})
        # With empty supabase_url, middleware returns minimal profile from JWT sub
        assert resp.status_code == 200
        assert resp.json()["id"] == TEST_USER_ID


# ── /auth/register tests ───────────────────────────────────────────────────────

class TestRegister:
    def _mock_sb(self) -> MagicMock:
        mock_user = MagicMock()
        mock_user.id = TEST_USER_ID

        mock_session = MagicMock()
        mock_session.access_token = "access-token-abc"
        mock_session.refresh_token = "refresh-token-abc"
        mock_session.expires_in = 3600

        auth_resp = MagicMock()
        auth_resp.user = mock_user
        auth_resp.session = mock_session

        founder_row = {
            "id": TEST_USER_ID,
            "email": TEST_EMAIL,
            "full_name": "Test Founder",
            "company_name": "TestCo",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }

        mock_client = MagicMock()
        mock_client.auth.sign_up.return_value = auth_resp
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[founder_row]
        )
        return mock_client

    def test_register_success(self, client: TestClient) -> None:
        with patch("backend.auth.router.create_client", return_value=self._mock_sb()):
            resp = client.post(
                "/auth/register",
                json={"email": TEST_EMAIL, "password": "password123",
                      "full_name": "Test Founder", "company_name": "TestCo"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tokens"]["access_token"] == "access-token-abc"
        assert data["founder"]["email"] == TEST_EMAIL

    def test_register_short_password_rejected(self, client: TestClient) -> None:
        resp = client.post("/auth/register", json={"email": TEST_EMAIL, "password": "short"})
        assert resp.status_code == 422

    def test_register_invalid_email_rejected(self, client: TestClient) -> None:
        resp = client.post("/auth/register", json={"email": "not-an-email", "password": "password123"})
        assert resp.status_code == 422

    def test_register_supabase_failure_returns_400(self, client: TestClient) -> None:
        mock_client = MagicMock()
        mock_client.auth.sign_up.side_effect = Exception("email already registered")
        with patch("backend.auth.router.create_client", return_value=mock_client):
            resp = client.post(
                "/auth/register",
                json={"email": TEST_EMAIL, "password": "password123"},
            )
        assert resp.status_code == 400


# ── /auth/login tests ──────────────────────────────────────────────────────────

class TestLogin:
    def _mock_sb(self) -> MagicMock:
        mock_user = MagicMock()
        mock_user.id = TEST_USER_ID

        mock_session = MagicMock()
        mock_session.access_token = "login-access-token"
        mock_session.refresh_token = "login-refresh-token"
        mock_session.expires_in = 3600

        auth_resp = MagicMock()
        auth_resp.user = mock_user
        auth_resp.session = mock_session

        founder_row = {
            "id": TEST_USER_ID, "email": TEST_EMAIL,
            "full_name": "Test Founder", "company_name": "TestCo",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }

        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = auth_resp
        (mock_client.table.return_value.select.return_value.eq.return_value
         .single.return_value.execute.return_value) = MagicMock(data=founder_row)
        return mock_client

    def test_login_success(self, client: TestClient) -> None:
        with patch("backend.auth.router.create_client", return_value=self._mock_sb()):
            resp = client.post("/auth/login", json={"email": TEST_EMAIL, "password": "password123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tokens"]["access_token"] == "login-access-token"
        assert data["founder"]["id"] == TEST_USER_ID

    def test_login_wrong_credentials_returns_401(self, client: TestClient) -> None:
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")
        with patch("backend.auth.router.create_client", return_value=mock_client):
            resp = client.post("/auth/login", json={"email": TEST_EMAIL, "password": "wrong"})
        assert resp.status_code == 401

    def test_login_no_session_returns_401(self, client: TestClient) -> None:
        auth_resp = MagicMock()
        auth_resp.session = None
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = auth_resp
        with patch("backend.auth.router.create_client", return_value=mock_client):
            resp = client.post("/auth/login", json={"email": TEST_EMAIL, "password": "password123"})
        assert resp.status_code == 401


# ── /auth/logout tests ─────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_always_succeeds_even_on_error(self, client: TestClient) -> None:
        mock_client = MagicMock()
        mock_client.auth.sign_out.side_effect = Exception("session already gone")
        with patch("backend.auth.router.create_client", return_value=mock_client):
            resp = client.post("/auth/logout", json={"refresh_token": "any-token"})
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()


# ── /auth/mfa/enroll tests ─────────────────────────────────────────────────────

class TestMFAEnroll:
    def test_mfa_enroll_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/auth/mfa/enroll")
        assert resp.status_code == 401

    def test_mfa_enroll_returns_totp_uri(self, client: TestClient) -> None:
        mock_totp = MagicMock()
        mock_totp.uri = "otpauth://totp/FoundrAI:founder@example.com?secret=BASE32&issuer=FoundrAI"

        mock_enroll_resp = MagicMock()
        mock_enroll_resp.id = "factor-uuid-1234"
        mock_enroll_resp.totp = mock_totp

        mock_challenge = MagicMock()
        mock_challenge.id = "challenge-uuid-5678"

        mock_client = MagicMock()
        mock_client.auth.mfa.enroll.return_value = mock_enroll_resp
        mock_client.auth.mfa.challenge.return_value = mock_challenge

        with patch("backend.auth.router.create_client", return_value=mock_client):
            resp = client.post(
                "/auth/mfa/enroll",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["factor_id"] == "factor-uuid-1234"
        assert data["totp_uri"].startswith("otpauth://")
