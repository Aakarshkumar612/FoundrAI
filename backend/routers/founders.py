"""Founders router: profile management and uploads CRUD."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.auth.middleware import verify_jwt
from backend.storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/founders", tags=["founders"])


class FounderProfile(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None


class UploadSummary(BaseModel):
    id: str
    filename: str
    file_type: str
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    upload_status: str
    created_at: str


class UploadListResponse(BaseModel):
    uploads: List[UploadSummary]
    total: int
    page: int
    page_size: int
    has_next: bool


@router.get("/profile", response_model=FounderProfile)
async def get_profile(founder: dict = Depends(verify_jwt)) -> FounderProfile:
    """Return the authenticated founder's profile row."""
    founder_id: str = founder["sub"]
    sb = get_supabase_client()
    if sb is None:
        return FounderProfile(id=founder_id)
    try:
        row = sb.table("founders").select("*").eq("id", founder_id).maybe_single().execute()
        if row.data:
            d = row.data
            return FounderProfile(
                id=str(d.get("id", founder_id)),
                email=d.get("email"),
                full_name=d.get("full_name"),
                company_name=d.get("company_name"),
                created_at=str(d["created_at"]) if d.get("created_at") else None,
                updated_at=str(d["updated_at"]) if d.get("updated_at") else None,
            )
        return FounderProfile(id=founder_id)
    except Exception as exc:
        logger.error("Profile fetch failed founder=%s: %s", founder_id, exc)
        return FounderProfile(id=founder_id)


@router.patch("/profile", response_model=FounderProfile)
async def upsert_profile(
    body: ProfileUpdateRequest,
    founder: dict = Depends(verify_jwt),
) -> FounderProfile:
    """Create or update the founder's profile (upsert on id)."""
    founder_id: str = founder["sub"]
    sb = get_supabase_client()
    if sb is None:
        return FounderProfile(id=founder_id, **body.model_dump(exclude_none=True))

    payload: dict = {"id": founder_id}
    if body.full_name is not None:
        payload["full_name"] = body.full_name
    if body.company_name is not None:
        payload["company_name"] = body.company_name
    # email: use body value or fall back to JWT claim (Supabase includes it)
    email = body.email or founder.get("email", "")
    if email:
        payload["email"] = email

    try:
        result = sb.table("founders").upsert(payload, on_conflict="id").execute()
        if result.data:
            d = result.data[0]
            return FounderProfile(
                id=str(d.get("id", founder_id)),
                email=d.get("email"),
                full_name=d.get("full_name"),
                company_name=d.get("company_name"),
                created_at=str(d["created_at"]) if d.get("created_at") else None,
                updated_at=str(d["updated_at"]) if d.get("updated_at") else None,
            )
        return FounderProfile(id=founder_id, **body.model_dump(exclude_none=True))
    except Exception as exc:
        logger.error("Profile upsert failed founder=%s: %s", founder_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DB_QUERY_001", "message": "Profile update failed"},
        )


@router.get("/uploads", response_model=UploadListResponse)
async def list_uploads(
    founder: dict = Depends(verify_jwt),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> UploadListResponse:
    """List the founder's uploads, newest first (paginated, excludes soft-deleted)."""
    founder_id: str = founder["sub"]
    sb = get_supabase_client()
    if sb is None:
        return UploadListResponse(uploads=[], total=0, page=page, page_size=page_size, has_next=False)

    offset = (page - 1) * page_size
    try:
        result = (
            sb.table("uploads")
            .select(
                "id,filename,file_type,row_count,columns,upload_status,created_at",
                count="exact",
            )
            .eq("founder_id", founder_id)
            .neq("upload_status", "deleted")
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        total = result.count or 0
        uploads = [UploadSummary(**row) for row in (result.data or [])]
        return UploadListResponse(
            uploads=uploads,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        )
    except Exception as exc:
        logger.error("Upload list failed founder=%s: %s", founder_id, exc)
        return UploadListResponse(uploads=[], total=0, page=page, page_size=page_size, has_next=False)


@router.get("/uploads/{upload_id}", response_model=UploadSummary)
async def get_upload(
    upload_id: str,
    founder: dict = Depends(verify_jwt),
) -> UploadSummary:
    """Get a single upload owned by the authenticated founder."""
    founder_id: str = founder["sub"]
    sb = get_supabase_client()
    if sb is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_CONN_001", "message": "Storage unavailable"},
        )
    try:
        result = (
            sb.table("uploads")
            .select("id,filename,file_type,row_count,columns,upload_status,created_at")
            .eq("id", upload_id)
            .eq("founder_id", founder_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "DB_QUERY_001", "message": "Upload not found"},
            )
        return UploadSummary(**result.data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upload fetch failed upload_id=%s: %s", upload_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DB_QUERY_001", "message": "Upload not found"},
        )


@router.delete("/uploads/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    upload_id: str,
    founder: dict = Depends(verify_jwt),
) -> None:
    """Soft-delete an upload by setting its status to 'deleted'."""
    founder_id: str = founder["sub"]
    sb = get_supabase_client()
    if sb is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_CONN_001", "message": "Storage unavailable"},
        )
    try:
        result = (
            sb.table("uploads")
            .update({"upload_status": "deleted"})
            .eq("id", upload_id)
            .eq("founder_id", founder_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "DB_QUERY_001", "message": "Upload not found"},
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upload delete failed upload_id=%s: %s", upload_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DB_QUERY_001", "message": "Delete failed"},
        )
