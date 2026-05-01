"""GCS client wrapper — upload/download with graceful fallback when unconfigured."""

import base64
import json
import logging
import tempfile
import os
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)

_gcs_client = None


def _get_client():
    """Lazy-init GCS client from base64-encoded service account JSON or ADC."""
    global _gcs_client
    if _gcs_client is not None:
        return _gcs_client

    settings = get_settings()
    try:
        from google.cloud import storage
        if settings.gcp_service_account_json_b64:
            sa_json = base64.b64decode(settings.gcp_service_account_json_b64).decode()
            info = json.loads(sa_json)
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_info(info)
            _gcs_client = storage.Client(credentials=creds, project=settings.gcp_project_id)
        else:
            # Fall back to Application Default Credentials (local dev with gcloud auth)
            _gcs_client = storage.Client(project=settings.gcp_project_id or None)
        logger.info("GCS client initialised (bucket=%s)", settings.gcs_bucket_name)
        return _gcs_client
    except Exception as exc:
        logger.warning("GCS client init failed — uploads will be DB-only: %s", exc)
        return None


def upload_bytes(data: bytes, gcs_path: str) -> Optional[str]:
    """Upload bytes to GCS and return the gs:// URI, or None on failure.

    Args:
        data: File content bytes.
        gcs_path: Path within the bucket (e.g. founders/{id}/financials/{uid}/file.csv).

    Returns:
        GCS URI string like gs://bucket/path, or None if GCS unavailable.
    """
    settings = get_settings()
    client = _get_client()
    if client is None:
        return None
    try:
        bucket = client.bucket(settings.gcs_bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(data, content_type="text/csv")
        uri = f"gs://{settings.gcs_bucket_name}/{gcs_path}"
        logger.info("GCS upload ok: %s (%d bytes)", uri, len(data))
        return uri
    except Exception as exc:
        logger.error("GCS upload failed for %s: %s", gcs_path, exc)
        return None


def download_bytes(gcs_path: str) -> Optional[bytes]:
    """Download bytes from GCS path, or None on failure.

    Args:
        gcs_path: Path within the bucket.

    Returns:
        Raw bytes, or None if unavailable.
    """
    settings = get_settings()
    client = _get_client()
    if client is None:
        return None
    try:
        bucket = client.bucket(settings.gcs_bucket_name)
        blob = bucket.blob(gcs_path)
        data = blob.download_as_bytes()
        logger.info("GCS download ok: %s (%d bytes)", gcs_path, len(data))
        return data
    except Exception as exc:
        logger.error("GCS download failed for %s: %s", gcs_path, exc)
        return None


def reset_client() -> None:
    """Clear the GCS singleton — used in tests."""
    global _gcs_client
    _gcs_client = None
