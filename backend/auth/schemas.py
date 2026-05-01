"""Pydantic schemas for all auth request and response bodies."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    company_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MFAVerifyRequest(BaseModel):
    factor_id: str = Field(description="Factor ID returned from /auth/mfa/enroll")
    challenge_id: str = Field(description="Challenge ID from enroll response")
    code: str = Field(min_length=6, max_length=6, description="6-digit TOTP code")


# ── Response schemas ──────────────────────────────────────────────────────────

class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class FounderProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    created_at: str
    updated_at: str


class AuthResponse(BaseModel):
    tokens: AuthTokens
    founder: FounderProfile


class MFAEnrollResponse(BaseModel):
    factor_id: str
    challenge_id: str
    totp_uri: str = Field(description="otpauth:// URI — render as QR code in frontend")
    qr_code_svg: Optional[str] = Field(
        default=None, description="Base64-encoded QR code SVG for display"
    )


class MessageResponse(BaseModel):
    message: str
