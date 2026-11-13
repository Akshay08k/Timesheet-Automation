"""Daily timesheet draft and AI summary versioning models for MongoDB."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.app.models.base import BaseDoc, utc_now


class DailyTimesheetDraft(BaseDoc):
    """Daily timesheet draft document stored in MongoDB 'daily_timesheet_drafts' collection."""

    def __init__(
        self,
        id: int,
        user_id: int,
        date_str: str,
        day_of_week: str,
        task_summary: str = "",
        detailed_bullets_json: Optional[str] = "[]",
        client_name: str = "Visual Comfort and Co",
        project_name: str = "VCC - VCQMS Enhancements and InspectionDB",
        area_path: str = r"Rysun Project Management\VC - VCQMS",
        iteration_path: str = "Rysun Project Management",
        hours: float = 8.0,
        ph: bool = False,
        leave: bool = False,
        half_day: bool = False,
        wfh: bool = False,
        mycompany_workitem_id: Optional[int] = None,
        ry_workitem_id: Optional[int] = None,
        submission_status: str = "draft",
        last_error: Optional[str] = None,
        is_user_approved: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs,
    ):
        self.id = int(id)
        self.user_id = int(user_id)
        self.date_str = date_str
        self.day_of_week = day_of_week
        self.task_summary = task_summary
        self.detailed_bullets_json = detailed_bullets_json
        self.client_name = client_name
        self.project_name = project_name
        self.area_path = area_path
        self.iteration_path = iteration_path
        self.hours = float(hours)
        self.ph = bool(ph)
        self.leave = bool(leave)
        self.half_day = bool(half_day)
        self.wfh = bool(wfh)
        resolved_wi = mycompany_workitem_id or ry_workitem_id or kwargs.get("workitem_id")
        self.mycompany_workitem_id = resolved_wi
        self.ry_workitem_id = resolved_wi
        self.submission_status = submission_status
        self.last_error = last_error
        self.is_user_approved = bool(is_user_approved)
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional["DailyTimesheetDraft"]:
        if not doc:
            return None
        data = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**data)


class SummaryVersion(BaseDoc):
    """AI summary version revision stored in MongoDB 'summary_versions' collection."""

    def __init__(
        self,
        id: int,
        draft_id: int,
        version_number: int,
        source: str,
        summary_text: str,
        raw_ai_payload: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs,
    ):
        self.id = int(id)
        self.draft_id = int(draft_id)
        self.version_number = int(version_number)
        self.source = source
        self.summary_text = summary_text
        self.raw_ai_payload = raw_ai_payload
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional["SummaryVersion"]:
        if not doc:
            return None
        data = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**data)
