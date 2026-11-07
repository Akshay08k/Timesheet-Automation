"""Activity schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ActivityItemResponse(BaseModel):
    id: int
    source_type: str
    external_id: str
    repository: Optional[str] = None
    project: Optional[str] = None
    branch: Optional[str] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    occurred_at: datetime
    date_str: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    related_ids: Optional[str] = None
    is_excluded: bool

    model_config = ConfigDict(from_attributes=True)


class ActivitySyncRequest(BaseModel):
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # Monday YYYY-MM-DD
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")    # Friday YYYY-MM-DD
    project: Optional[str] = None
    force_refresh: bool = False


class ActivitySyncResponse(BaseModel):
    total_found: int
    new_added: int
    commits: int
    pull_requests: int
    work_items: int
    reviews: int
    branches: int
    date_range: str
    last_synced_at: datetime


class ClientVcqmsContextResponse(BaseModel):
    status: str = 'success'
    scope: str = 'VCQMS only'
    target_organization: str
    authenticated_user: str
    date_range: str
    repositories: List[dict]
    commits: List[dict]
    pull_requests: List[dict]
    work_items: List[dict]
    stats: dict
    raw_logs_file: str = 'fetchClientLogs.txt'
    last_synced_at: datetime
