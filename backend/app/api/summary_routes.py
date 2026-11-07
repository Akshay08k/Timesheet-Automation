"""AI Daily and Weekly summary generation routes using Google Gemini API and MongoDB."""

from datetime import datetime, timedelta
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.models.timesheet import DailyTimesheetDraft, SummaryVersion
from backend.app.schemas.summary import (
    GenerateSummaryRequest,
    GenerateWeekSummaryRequest,
    DailySummaryResponse,
    SummaryVersionResponse,
)
from backend.app.schemas.timesheet import WeeklyReviewResponse, TimesheetEntryView
from backend.app.services.timesheet.timesheet_service import TimesheetService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.post("/generate", response_model=DailySummaryResponse)
def generate_daily_summary(
    req: GenerateSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Triggers Google Gemini API to analyze commits and activities for a single day and generate a timesheet draft."""
    svc = TimesheetService(db, current_user.id)
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

    version_docs = list(
        db.summary_versions.find({"draft_id": draft.id}).sort("version_number", -1)
    )

    return DailySummaryResponse(
        date_str=draft.date_str,
        day_of_week=draft.day_of_week,
        task_summary=draft.task_summary,
        detailed_bullets=bullets,
        suggested_project=draft.project_name,
        versions=[
            SummaryVersionResponse.model_validate(SummaryVersion.from_doc(v))
            for v in version_docs
        ],
        hours=draft.hours,
        ph=draft.ph,
        leave=draft.leave,
        half_day=draft.half_day,
        wfh=draft.wfh,
    )


@router.post("/generate-week", response_model=WeeklyReviewResponse)
async def generate_week_summaries(
    req: GenerateWeekSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Generates Gemini AI summaries for all 5 days of the week in a single request and returns the full weekly review."""
    svc = TimesheetService(db, current_user.id)
    svc.ensure_week_drafts(req.monday_date_str)

    # Check if there are any activities in MongoDB for this week
    m_date = datetime.strptime(req.monday_date_str, "%Y-%m-%d").date()
    week_dates = [(m_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    activity_count = db.activity_items.count_documents({
        "user_id": current_user.id,
        "date_str": {"$in": week_dates},
    })

    # Auto-sync from Client Azure DevOps (strictly VCQMS scope) if no activities recorded yet
    if activity_count == 0:
        cred = db.ado_credentials.find_one({"user_id": current_user.id, "provider": "client", "is_valid": True})
        if cred:
            try:
                from backend.app.services.activity.activity_service import ActivityService
                act_svc = ActivityService(db, current_user.id, current_user.timezone)
                await act_svc.sync_client_activities(week_dates[0], week_dates[-1])
            except Exception:
                pass

    try:
        updated_drafts = svc.generate_week_summaries(req.monday_date_str, req.custom_instruction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weekly summary generation failed: {str(e)}")

    entries: List[TimesheetEntryView] = []
    total_hours = 0.0
    approved_count = 0
    submitted_count = 0

    for d in updated_drafts:
        total_hours += d.hours
        if d.is_user_approved:
            approved_count += 1
        if d.submission_status == "submitted":
            submitted_count += 1

        bullets = []
        if d.detailed_bullets_json:
            try:
                bullets = json.loads(d.detailed_bullets_json)
            except Exception:
                bullets = []

        entries.append(
            TimesheetEntryView(
                id=d.id,
                date_str=d.date_str,
                day_of_week=d.day_of_week,
                client_name=d.client_name,
                project_name=d.project_name,
                area_path=d.area_path,
                iteration_path=d.iteration_path,
                hours=d.hours,
                ph=d.ph,
                leave=d.leave,
                half_day=d.half_day,
                wfh=d.wfh,
                task_summary=d.task_summary,
                detailed_bullets=bullets,
                is_user_approved=d.is_user_approved,
                submission_status=d.submission_status,
                ry_workitem_id=d.ry_workitem_id,
                last_error=d.last_error,
                existing_rysun_item=None,
            )
        )

    return WeeklyReviewResponse(
        week_start=req.monday_date_str,
        week_end=week_dates[-1],
        total_hours=total_hours,
        approved_count=approved_count,
        submitted_count=submitted_count,
        entries=entries,
    )


@router.get("/{date_str}/versions", response_model=List[SummaryVersionResponse])
def get_summary_versions(
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retrieves revision history of summaries generated or edited for this date from MongoDB."""
    draft_doc = db.daily_timesheet_drafts.find_one(
        {
            "user_id": current_user.id,
            "date_str": date_str,
        }
    )

    if not draft_doc:
        return []

    version_docs = list(
        db.summary_versions.find({"draft_id": draft_doc["id"]}).sort("version_number", -1)
    )
    return [
        SummaryVersionResponse.model_validate(SummaryVersion.from_doc(v))
        for v in version_docs
    ]
