"""AI Daily summary generation routes using Google Gemini API."""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.models.timesheet import DailyTimesheetDraft, SummaryVersion
from backend.app.schemas.summary import (
    GenerateSummaryRequest,
    DailySummaryResponse,
    SummaryVersionResponse,
)
from backend.app.services.timesheet.timesheet_service import TimesheetService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.post("/generate", response_model=DailySummaryResponse)
def generate_daily_summary(
    req: GenerateSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers Google Gemini API to analyze commits and activities for a day and generate a timesheet draft."""
    svc = TimesheetService(db, current_user.id)
    # Ensure draft exists
    svc.ensure_week_drafts(req.date_str)

    try:
        draft = svc.generate_summary_for_date(req.date_str, req.custom_instruction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

    bullets = []
    if draft.detailed_bullets_json:
        try:
            bullets = json.loads(draft.detailed_bullets_json)
        except Exception:
            bullets = []

    versions = db.scalars(
        select(SummaryVersion).where(SummaryVersion.draft_id == draft.id).order_by(SummaryVersion.version_number.desc())
    ).all()

    return DailySummaryResponse(
        date_str=draft.date_str,
        day_of_week=draft.day_of_week,
        task_summary=draft.task_summary,
        detailed_bullets=bullets,
        suggested_project=draft.project_name,
        versions=[SummaryVersionResponse.model_validate(v) for v in versions],
        hours=draft.hours,
        ph=draft.ph,
        leave=draft.leave,
        half_day=draft.half_day,
        wfh=draft.wfh,
    )


@router.get("/{date_str}/versions", response_model=List[SummaryVersionResponse])
def get_summary_versions(
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves revision history of summaries generated or edited for this date."""
    draft = db.scalars(
        select(DailyTimesheetDraft).where(
            DailyTimesheetDraft.user_id == current_user.id,
            DailyTimesheetDraft.date_str == date_str,
        )
    ).first()

    if not draft:
        return []

    versions = db.scalars(
        select(SummaryVersion).where(SummaryVersion.draft_id == draft.id).order_by(SummaryVersion.version_number.desc())
    ).all()
    return versions
