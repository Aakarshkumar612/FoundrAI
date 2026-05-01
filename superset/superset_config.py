"""Superset configuration for FoundrAI embedded dashboards."""

import os

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_32CHARS!")
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = ["superset.views.core.log"]

# Enable CORS for the API and embedding
ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": ["http://localhost:5173", "http://localhost:3000"]
}

# ── Embedded dashboard support ────────────────────────────────────────────────
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "EMBEDDABLE_CHARTS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Allow the FoundrAI frontend origin to embed dashboards
TALISMAN_CONFIG = {
    "content_security_policy": {
        "frame-ancestors": [
            "http://localhost:5173",   # Vite dev
            "http://localhost:3000",
            os.environ.get("FRONTEND_URL", "https://app.foundrai.com"),
        ]
    },
    "force_https": False,
}

# ── Database ──────────────────────────────────────────────────────────────────
# Superset meta DB (separate from app Supabase DB)
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_DB_URI",
    "postgresql+psycopg2://superset:superset@superset-db:5432/superset",
)

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
}

DATA_CACHE_CONFIG = CACHE_CONFIG

# ── Guest token ───────────────────────────────────────────────────────────────
GUEST_TOKEN_JWT_SECRET = os.environ.get("SUPERSET_GUEST_TOKEN_JWT_SECRET", SECRET_KEY)
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_HEADER_NAME = "X-GuestToken"
GUEST_TOKEN_JWT_EXP_SECONDS = 300  # 5 minutes

# ── General ───────────────────────────────────────────────────────────────────
ROW_LIMIT = 10_000
SUPERSET_WEBSERVER_TIMEOUT = 60
