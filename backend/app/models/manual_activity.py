"""Manual activities model for MongoDB 'manual_activities' collection."""

from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.models.base import BaseDoc, utc_now


class ManualActivity(BaseDoc):
    """Manual activity stored in MongoDB."""

    def __init__(
        self,
        id: int,
        user_id: int,
        date_str: str,
        category: str,
        description: str,
        duration_hours: Optional[float] = 1.0,
        project_name: Optional[str] = None,
        notes: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs,
    ):
        self.id = int(id)
        self.user_id = int(user_id)
        self.date_str = date_str
        self.category = category
        self.description = description
        self.duration_hours = float(duration_hours) if duration_hours is not None else 1.0
        self.project_name = project_name
        self.notes = notes
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional["ManualActivity"]:
        if not doc:
            return None
        data = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**data)
