"""Azure DevOps Credentials API routes using MongoDB and AES-256-GCM encryption."""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from backend.app.models.database import get_db, get_next_sequence_value
from backend.app.models.user import User
from backend.app.models.credential import AdoCredential
from backend.app.schemas.credential import (
    CredentialCreate,
    CredentialResponse,
    ValidateConnectionResponse,
)
from backend.app.security.crypto import encrypt_pat
from backend.app.services.azure_client.client_service import AzureClientService
from backend.app.services.azure_rysun.rysun_service import AzureRysunService, AzureMyCompanyService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


@router.get("", response_model=List[CredentialResponse])
def list_credentials(
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists connection status for current user from MongoDB (never returns PAT values)."""
    docs = db.ado_credentials.find({"user_id": current_user.id})
    return [AdoCredential.from_doc(d) for d in docs]


@router.post("", response_model=CredentialResponse)
async def save_credential(
    cred_in: CredentialCreate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Encrypts and saves PAT at rest in MongoDB after validating connection with Azure DevOps."""
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
        elif cred_in.provider in ("rysun", "mycompany"):
            svc = AzureRysunService(cred_in.org_url, encrypted)
            info = await svc.validate_connection()
            resolved_id = info.get("id")
            resolved_name = info.get("name")
            resolved_email = info.get("email")
            is_valid = True
    except Exception as e:
        is_valid = False
        last_error = str(e)

    now = datetime.now(timezone.utc)

    # Upsert credential in MongoDB
    existing = db.ado_credentials.find_one(
        {"user_id": current_user.id, "provider": cred_in.provider}
    )

    if not existing:
        new_id = get_next_sequence_value(db, "ado_credentials")
        cred = AdoCredential(
            id=new_id,
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
            created_at=now,
            updated_at=now,
        )
        db.ado_credentials.insert_one(cred.to_dict())
    else:
        update_data = {
            "org_url": cred_in.org_url,
            "encrypted_pat": encrypted,
            "resolved_identity_id": resolved_id,
            "resolved_identity_name": resolved_name,
            "resolved_identity_email": resolved_email,
            "is_valid": is_valid,
            "last_verified_at": now,
            "last_error": last_error,
            "updated_at": now,
        }
        db.ado_credentials.update_one(
            {"id": existing["id"]},
            {"$set": update_data},
        )
        existing.update(update_data)
        cred = AdoCredential.from_doc(existing)

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
    db: Database = Depends(get_db),
):
    """Revokes / deletes stored credentials for a provider from MongoDB."""
    db.ado_credentials.delete_one(
        {"user_id": current_user.id, "provider": provider}
    )
    return None
