"""Azure DevOps Credential schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, ConfigDict


class CredentialCreate(BaseModel):
    provider: str = Field(..., pattern="^(client|rysun)$")
    org_url: str = Field(..., min_length=10)
    pat: str = Field(..., min_length=10)


class CredentialResponse(BaseModel):
    id: int
    provider: str
    org_url: str
    is_valid: bool
    has_pat: bool = True
    resolved_identity_id: Optional[str] = None
    resolved_identity_name: Optional[str] = None
    resolved_identity_email: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    last_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ValidateConnectionResponse(BaseModel):
    success: bool
    provider: str
    org_url: str
    identity_id: Optional[str] = None
    identity_name: Optional[str] = None
    identity_email: Optional[str] = None
    message: str
