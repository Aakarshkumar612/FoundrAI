"""Auth router: register, login, refresh, logout, MFA enroll/verify, /me."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from backend.auth.middleware import verify_jwt
from backend.auth.schemas import (
    AuthResponse,
    AuthTokens,
    FounderProfile,
    LoginRequest,
    LogoutRequest,
    MFAEnrollResponse,
    MFAVerifyRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
)
from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_supabase(settings: Settings) -> Client:
    """Create a Supabase client using the anon key (for auth operations)."""
    return create_client(settings.supabase_url, settings.supabase_key)


def _get_supabase_admin(settings: Settings) -> Client:
    """Create a Supabase client using the service role key (for admin DB writes)."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _build_auth_response(session: Any, founder_row: Dict) -> AuthResponse:
    """Convert Supabase session + DB row into AuthResponse schema."""
    return AuthResponse(
        tokens=AuthTokens(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in or 3600,
        ),
        founder=FounderProfile(
            id=founder_row["id"],
            email=founder_row["email"],
            full_name=founder_row.get("full_name"),
            company_name=founder_row.get("company_name"),
            created_at=str(founder_row["created_at"]),
            updated_at=str(founder_row["updated_at"]),
        ),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, settings: Settings = Depends(get_settings)) -> AuthResponse:
    """Create a new Supabase auth user and insert a founder profile row.

    Args:
        body: Email, password, optional full_name and company_name.
        settings: App settings with Supabase credentials.

    Returns:
        AuthResponse with JWT tokens and founder profile.
    """
    sb = _get_supabase(settings)
    sb_admin = _get_supabase_admin(settings)

    try:
        auth_resp = sb.auth.sign_up({"email": body.email, "password": body.password})
    except Exception as exc:
        logger.error("Supabase sign_up failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUTH_LOGIN_001", "message": "Registration failed"},
        )

    if auth_resp.user is None or auth_resp.session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUTH_LOGIN_001", "message": "Registration failed — check email/password"},
        )

    user_id = auth_resp.user.id

    # Insert founder profile (service role bypasses RLS so we can write immediately)
    founder_data = {
        "id": user_id,
        "email": body.email,
        "full_name": body.full_name,
        "company_name": body.company_name,
    }
    try:
        result = sb_admin.table("founders").insert(founder_data).execute()
    except Exception as exc:
        logger.error("Failed to insert founder profile for %s: %s", user_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AUTH_LOGIN_001", "message": "Account created but profile setup failed"},
        )

    return _build_auth_response(auth_resp.session, result.data[0])


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)) -> AuthResponse:
    """Authenticate founder with email and password.

    Args:
        body: Email and password credentials.
        settings: App settings.

    Returns:
        AuthResponse with JWT tokens and founder profile.
    """
    sb = _get_supabase(settings)
    sb_admin = _get_supabase_admin(settings)

    try:
        auth_resp = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
    except Exception as exc:
        logger.warning("Login failed for %s: %s", body.email, str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_LOGIN_001", "message": "Invalid credentials"},
        )

    if auth_resp.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_LOGIN_001", "message": "Invalid credentials"},
        )

    user_id = auth_resp.user.id
    try:
        result = (
            sb_admin.table("founders")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except Exception as exc:
        logger.error("Founder profile fetch failed for %s: %s", user_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_LOGIN_001", "message": "Founder profile not found"},
        )

    return _build_auth_response(auth_resp.session, result.data)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(body: RefreshRequest, settings: Settings = Depends(get_settings)) -> AuthResponse:
    """Exchange a refresh token for a new access token.

    Args:
        body: Valid refresh token from a prior login or refresh.
        settings: App settings.

    Returns:
        AuthResponse with new JWT tokens.
    """
    sb = _get_supabase(settings)
    sb_admin = _get_supabase_admin(settings)

    try:
        auth_resp = sb.auth.refresh_session(body.refresh_token)
    except Exception as exc:
        logger.warning("Token refresh failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_TOKEN_001", "message": "Refresh token invalid or expired"},
        )

    if auth_resp.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_TOKEN_001", "message": "Refresh token invalid or expired"},
        )

    user_id = auth_resp.user.id
    result = sb_admin.table("founders").select("*").eq("id", user_id).single().execute()
    return _build_auth_response(auth_resp.session, result.data)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: LogoutRequest, settings: Settings = Depends(get_settings)) -> MessageResponse:
    """Invalidate the current session in Supabase.

    Args:
        body: Refresh token to invalidate.
        settings: App settings.

    Returns:
        Confirmation message.
    """
    sb = _get_supabase(settings)
    try:
        # Set the session so sign_out targets the right session
        sb.auth.set_session(access_token="", refresh_token=body.refresh_token)
        sb.auth.sign_out()
    except Exception as exc:
        # Logout is best-effort — log but don't fail the client
        logger.warning("Logout error (non-fatal): %s", str(exc))

    return MessageResponse(message="Logged out successfully")


@router.post("/mfa/enroll", response_model=MFAEnrollResponse)
async def mfa_enroll(
    founder: dict = Depends(verify_jwt),
    settings: Settings = Depends(get_settings),
) -> MFAEnrollResponse:
    """Initiate TOTP MFA enrollment. Returns a QR code URI.

    Args:
        founder: Verified JWT claims (injected by middleware).
        settings: App settings.

    Returns:
        MFAEnrollResponse with TOTP URI for QR code rendering and factor/challenge IDs.
    """
    sb = _get_supabase(settings)
    try:
        enroll_resp = sb.auth.mfa.enroll({"factor_type": "totp", "friendly_name": "FoundrAI"})
    except Exception as exc:
        logger.error("MFA enroll failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUTH_TOKEN_002", "message": "MFA enrollment failed"},
        )

    factor = enroll_resp.totp
    challenge = sb.auth.mfa.challenge({"factor_id": enroll_resp.id})

    return MFAEnrollResponse(
        factor_id=enroll_resp.id,
        challenge_id=challenge.id,
        totp_uri=factor.uri,
    )


@router.post("/mfa/verify", response_model=MessageResponse)
async def mfa_verify(
    body: MFAVerifyRequest,
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Verify a TOTP code and upgrade the session to AAL2 (MFA-verified).

    Args:
        body: factor_id, challenge_id, and 6-digit TOTP code.
        settings: App settings.

    Returns:
        Confirmation message on successful verification.
    """
    sb = _get_supabase(settings)
    try:
        sb.auth.mfa.verify({
            "factor_id": body.factor_id,
            "challenge_id": body.challenge_id,
            "code": body.code,
        })
    except Exception as exc:
        logger.warning("MFA verify failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_TOKEN_002", "message": "Invalid TOTP code"},
        )

    return MessageResponse(message="MFA verified — session upgraded to AAL2")


@router.get("/me", response_model=FounderProfile)
async def get_me(founder: dict = Depends(verify_jwt)) -> FounderProfile:
    """Return the current founder's profile.

    Args:
        founder: Verified JWT claims with attached founder_profile.

    Returns:
        FounderProfile from the founders table.
    """
    profile = founder.get("founder_profile", {})
    return FounderProfile(
        id=profile["id"],
        email=profile.get("email", ""),
        full_name=profile.get("full_name"),
        company_name=profile.get("company_name"),
        created_at=str(profile.get("created_at", "")),
        updated_at=str(profile.get("updated_at", "")),
    )
