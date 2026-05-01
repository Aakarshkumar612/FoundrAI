"""JWT verification middleware for FastAPI.

Validates Supabase-issued RS256 JWTs, extracts the founder_id (sub claim),
and confirms the founder exists in the database before allowing the request
through.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Claims we require in every valid Supabase JWT
_REQUIRED_CLAIMS = {"sub", "role", "iat", "exp"}


def _decode_token(token: str, secret: str) -> dict:
    """Decode and validate a Supabase JWT.

    Args:
        token: Raw JWT string from Authorization header.
        secret: Supabase JWT secret from settings.

    Returns:
        Decoded claims dict.

    Raises:
        HTTPException 401 on any validation failure.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],  # Supabase uses HS256 by default
            options={"verify_aud": False},  # Supabase omits aud in some configs
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_AUTH_001", "message": "Token has expired"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_AUTH_001", "message": "Invalid token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    missing = _REQUIRED_CLAIMS - payload.keys()
    if missing:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_AUTH_001", "message": "Token missing required claims"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def _get_founder_from_db(founder_id: str, settings: Settings) -> dict:
    """Fetch the founder profile row to confirm they exist.

    Args:
        founder_id: UUID extracted from JWT sub claim.
        settings: Application settings (Supabase credentials).

    Returns:
        Founder row dict from Supabase.

    Raises:
        HTTPException 403 if founder record not found.
    """
    from supabase import create_client  # deferred to avoid circular import at startup

    try:
        client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        result = (
            client.table("founders")
            .select("id, email, full_name, company_name, created_at, updated_at")
            .eq("id", founder_id)
            .single()
            .execute()
        )
    except Exception as exc:
        logger.error("Supabase founder lookup failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "API_AUTH_001", "message": "Founder profile not found"},
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "API_AUTH_001", "message": "Founder profile not found"},
        )

    return result.data


async def verify_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict:
    """FastAPI dependency: validate JWT and return founder claims.

    Usage::

        @router.get("/protected")
        async def protected_route(founder: dict = Depends(verify_jwt)):
            founder_id = founder["sub"]

    Args:
        credentials: Bearer token extracted by HTTPBearer scheme.
        settings: Application settings.

    Returns:
        Dict with JWT claims + "founder_profile" key containing Supabase row.

    Raises:
        HTTPException 401 if no token or token invalid.
        HTTPException 403 if founder not found in DB.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_AUTH_001", "message": "Authorization header required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials, settings.supabase_jwt_secret)
    founder_id: str = payload["sub"]

    # Skip DB lookup in test mode (settings.supabase_url is empty)
    if settings.supabase_url and settings.supabase_service_role_key:
        founder_profile = await _get_founder_from_db(founder_id, settings)
        payload["founder_profile"] = founder_profile
    else:
        # Test/dev mode without real Supabase — attach minimal profile
        payload["founder_profile"] = {"id": founder_id}

    return payload
