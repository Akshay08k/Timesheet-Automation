"""Activity item model for MongoDB 'activity_items' collection."""

from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.models.base import BaseDoc, utc_now


class ActivityItem(BaseDoc):
    """Normalized engineering activity stored in MongoDB."""

    def __init__(
        self,
        id: int,
        user_id: int,
        source_type: str,
        external_id: str,
        occurred_at: datetime,
        date_str: str,
        title: str,
        repository: Optional[str] = None,
        project: Optional[str] = None,
        branch: Optional[str] = None,
        author_id: Optional[str] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        related_ids: Optional[str] = None,
        is_excluded: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs,
    ):
        self.id = int(id)
        self.user_id = int(user_id)
        self.source_type = source_type
        self.external_id = external_id
        self.occurred_at = occurred_at
        self.date_str = date_str
        self.title = title
        self.repository = repository
        self.project = project
        self.branch = branch
        self.author_id = author_id
        self.author_name = author_name
        self.author_email = author_email
        self.description = description
        self.url = url
        self.related_ids = related_ids
        self.is_excluded = bool(is_excluded)
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional["ActivityItem"]:
        if not doc:
            return None
        data = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**data)
