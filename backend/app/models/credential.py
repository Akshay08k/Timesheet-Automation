"""Azure DevOps Credentials model for storing encrypted PATs per user in MongoDB."""

from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.models.base import BaseDoc, utc_now


class AdoCredential(BaseDoc):
    """Credential document stored in MongoDB 'ado_credentials' collection.
    PAT is always stored encrypted at rest using AES-256-GCM.
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        provider: str,
        org_url: str,
        encrypted_pat: str,
        resolved_identity_id: Optional[str] = None,
        resolved_identity_name: Optional[str] = None,
        resolved_identity_email: Optional[str] = None,
        is_valid: bool = False,
        last_verified_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs,
    ):
        self.id = int(id)
        self.user_id = int(user_id)
        self.provider = provider
        self.org_url = org_url
        self.encrypted_pat = encrypted_pat
        self.resolved_identity_id = resolved_identity_id
        self.resolved_identity_name = resolved_identity_name
        self.resolved_identity_email = resolved_identity_email
        self.is_valid = bool(is_valid)
        self.last_verified_at = last_verified_at
        self.last_error = last_error
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional["AdoCredential"]:
        if not doc:
            return None
        data = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**data)
