"""Supabase client factory — service-role singleton for backend operations."""

import logging
from typing import Optional

from backend.config import get_settings

try:
    from supabase import create_client
except ImportError:
    create_client = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_client = None


def get_supabase_client():
    """Return a Supabase client using the service-role key, or None if unconfigured.

    Uses module-level singleton — client is created once and reused.
    Service-role key bypasses RLS, safe for server-side use only.
    """
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.warning("Supabase not configured — running in offline mode")
        return None

    try:
        if create_client is None:
            logger.error("supabase package not installed")
            return None
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("Supabase client initialised")
        return _client
    except Exception as exc:
        logger.error("Supabase client init failed: %s", exc)
        return None


def reset_client() -> None:
    """Clear the singleton — used in tests to inject a fresh mock."""
    global _client
    _client = None
