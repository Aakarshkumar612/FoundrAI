"""Supabase Storage client — upload/download files using the project's free bucket."""

import logging
from pathlib import Path
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)

BUCKET = "founder-uploads"


def upload_file(
    content: bytes,
    storage_path: str,
    content_type: str = "application/octet-stream",
    supabase_client=None,
) -> Optional[str]:
    """Upload bytes to Supabase Storage and return the storage path on success.

    Args:
        content: Raw file bytes.
        storage_path: Path within the bucket, e.g. founders/{id}/{upload_id}/file.pdf
        content_type: MIME type of the file.
        supabase_client: Initialised Supabase client. None = skip.

    Returns:
        The storage_path string on success, None on failure.
    """
    if supabase_client is None:
        return None
    try:
        supabase_client.storage.from_(BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        logger.info("Supabase Storage upload ok: %s (%d bytes)", storage_path, len(content))
        return storage_path
    except Exception as exc:
        logger.error("Supabase Storage upload failed for %s: %s", storage_path, exc)
        return None


def download_file(storage_path: str, supabase_client=None) -> Optional[bytes]:
    """Download bytes from Supabase Storage.

    Args:
        storage_path: Path within the bucket.
        supabase_client: Initialised Supabase client. None = skip.

    Returns:
        Raw bytes on success, None on failure.
    """
    if supabase_client is None:
        return None
    try:
        data = supabase_client.storage.from_(BUCKET).download(storage_path)
        logger.info("Supabase Storage download ok: %s (%d bytes)", storage_path, len(data))
        return data
    except Exception as exc:
        logger.error("Supabase Storage download failed for %s: %s", storage_path, exc)
        return None


def get_mime_type(filename: str) -> str:
    """Return MIME type based on file extension."""
    ext = Path(filename).suffix.lower()
    return {
        ".csv":  "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls":  "application/vnd.ms-excel",
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".txt":  "text/plain",
    }.get(ext, "application/octet-stream")
