"""Timesheet schemas for review, mapping, and submission."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TimesheetDraftUpdate(BaseModel):
    task_summary: Optional[str] = None
    detailed_bullets: Optional[List[str]] = None
    project_name: Optional[str] = None
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    hours: Optional[float] = Field(None, ge=0.0, le=24.0)
    ph: Optional[bool] = None
    leave: Optional[bool] = None
    half_day: Optional[bool] = None
    wfh: Optional[bool] = None
    is_user_approved: Optional[bool] = None


class TimesheetEntryView(BaseModel):
    id: int
    date_str: str
    day_of_week: str
    client_name: str
    project_name: str
    area_path: str
    iteration_path: str
    hours: float
    ph: bool
    leave: bool
    half_day: bool
    wfh: bool
    task_summary: str
    detailed_bullets: List[str]
    is_user_approved: bool
    submission_status: str
    mycompany_workitem_id: Optional[int] = None
    ry_workitem_id: Optional[int] = None
    last_error: Optional[str] = None
    existing_mycompany_item: Optional[dict] = None
    existing_rysun_item: Optional[dict] = None  # Existing Rysun work item if detected


class WeeklyReviewResponse(BaseModel):
    week_start: str
    week_end: str
    total_hours: float
    approved_count: int
    submitted_count: int
    entries: List[TimesheetEntryView]


class SubmitSingleDayRequest(BaseModel):
    draft_id: int
    force_update_existing: bool = False


class SubmitWeekRequest(BaseModel):
    draft_ids: List[int]
    force_update_existing: bool = False


class SubmissionResult(BaseModel):
    draft_id: int
    date_str: str
    status: str  # "created", "updated", "already_submitted", "failed"
    workitem_id: Optional[int] = None
    workitem_url: Optional[str] = None
    message: str
