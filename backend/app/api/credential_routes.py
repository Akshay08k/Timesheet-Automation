"""Azure DevOps Credentials API routes."""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.models.credential import AdoCredential
from backend.app.schemas.credential import (
    CredentialCreate,
    CredentialResponse,
    ValidateConnectionResponse,
)
from backend.app.security.crypto import encrypt_pat
from backend.app.services.azure_client.client_service import AzureClientService
from backend.app.services.azure_rysun.rysun_service import AzureRysunService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


@router.get("", response_model=List[CredentialResponse])
def list_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists connection status for current user (never returns PAT values)."""
    creds = db.scalars(
        select(AdoCredential).where(AdoCredential.user_id == current_user.id)
    ).all()
    return creds


@router.post("", response_model=CredentialResponse)
async def save_credential(
    cred_in: CredentialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Encrypts and saves PAT at rest after validating connection with Azure DevOps."""
    encrypted = encrypt_pat(cred_in.pat)

    # Validate against Azure DevOps
    resolved_id = None
    resolved_name = None
    resolved_email = None
    is_valid = False
    last_error = None

    try:
        if cred_in.provider == "client":
            svc = AzureClientService(cred_in.org_url, encrypted)
            info = await svc.validate_connection()
            resolved_id = info.get("id")
            resolved_name = info.get("name")
            resolved_email = info.get("email")
            is_valid = True
        elif cred_in.provider == "rysun":
            svc = AzureRysunService(cred_in.org_url, encrypted)
            info = await svc.validate_connection()
            resolved_id = info.get("id")
            resolved_name = info.get("name")
            resolved_email = info.get("email")
            is_valid = True
    except Exception as e:
        is_valid = False
        last_error = str(e)

    # Upsert credential
    cred = db.scalars(
        select(AdoCredential).where(
            AdoCredential.user_id == current_user.id,
            AdoCredential.provider == cred_in.provider,
        )
    ).first()

    now = datetime.now(timezone.utc)
    if not cred:
        cred = AdoCredential(
            user_id=current_user.id,
            provider=cred_in.provider,
            org_url=cred_in.org_url,
            encrypted_pat=encrypted,
            resolved_identity_id=resolved_id,
            resolved_identity_name=resolved_name,
            resolved_identity_email=resolved_email,
            is_valid=is_valid,
            last_verified_at=now,
            last_error=last_error,
        )
        db.add(cred)
    else:
        cred.org_url = cred_in.org_url
        cred.encrypted_pat = encrypted
        cred.resolved_identity_id = resolved_id
        cred.resolved_identity_name = resolved_name
        cred.resolved_identity_email = resolved_email
        cred.is_valid = is_valid
        cred.last_verified_at = now
        cred.last_error = last_error

    db.commit()
    db.refresh(cred)

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Connection validation failed: {last_error}",
        )

    return cred


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revokes / deletes stored credentials for a provider."""
    cred = db.scalars(
        select(AdoCredential).where(
            AdoCredential.user_id == current_user.id,
            AdoCredential.provider == provider,
        )
    ).first()
    if cred:
        db.delete(cred)
        db.commit()
    return None
