"""User model for MongoDB."""

from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.models.base import BaseDoc, utc_now


class User(BaseDoc):
    """User document stored in MongoDB 'users' collection."""

    def __init__(
        self,
        id: int,
        username: str,
        email: str,
        full_name: str,
        hashed_password: str,
        is_admin: bool = False,
        is_active: bool = True,
        timezone: str = "Asia/Kolkata",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs,
    ):
        self.id = int(id)
        self.username = username
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.is_admin = bool(is_admin)
        self.is_active = bool(is_active)
        self.timezone = timezone
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional["User"]:
        if not doc:
            return None
        data = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**data)
