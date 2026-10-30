"""Timesheet review, editing, and submission API routes."""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.models.timesheet import DailyTimesheetDraft, SummaryVersion
from backend.app.models.credential import AdoCredential
from backend.app.schemas.timesheet import (
    TimesheetDraftUpdate,
    TimesheetEntryView,
    WeeklyReviewResponse,
    SubmitSingleDayRequest,
    SubmitWeekRequest,
    SubmissionResult,
)
from backend.app.services.timesheet.timesheet_service import TimesheetService
from backend.app.services.azure_rysun.rysun_service import AzureRysunService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/timesheets", tags=["timesheets"])


@router.get("/week/{monday_date_str}", response_model=WeeklyReviewResponse)
async def get_weekly_review(
    monday_date_str: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves or prepares the 5 Monday-Friday timesheet entries for a selected week."""
    svc = TimesheetService(db, current_user.id)
    drafts = svc.ensure_week_drafts(monday_date_str)

    # Check Rysun credential
    cred = db.scalars(
        select(AdoCredential).where(
            AdoCredential.user_id == current_user.id,
            AdoCredential.provider == "rysun",
            AdoCredential.is_valid.is_(True),
        )
    ).first()

    rysun_service = None
    if cred:
        try:
            rysun_service = AzureRysunService(cred.org_url, cred.encrypted_pat)
        except Exception:
            pass

    entries: List[TimesheetEntryView] = []
    total_hours = 0.0
    approved_count = 0
    submitted_count = 0

    for d in drafts:
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

        # Existing record check if rysun connected
        existing_info = None
        if rysun_service and d.submission_status != "submitted":
            try:
                existing_info = await rysun_service.search_existing_timesheet(
                    date_str=d.date_str,
                    user_identity=cred.resolved_identity_name or current_user.full_name,
                )
            except Exception:
                pass

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
                existing_rysun_item=existing_info,
            )
        )

    week_end = drafts[-1].date_str if drafts else monday_date_str

    return WeeklyReviewResponse(
        week_start=monday_date_str,
        week_end=week_end,
        total_hours=total_hours,
        approved_count=approved_count,
        submitted_count=submitted_count,
        entries=entries,
    )


@router.patch("/drafts/{draft_id}", response_model=TimesheetEntryView)
def update_timesheet_draft(
    draft_id: int,
    patch_in: TimesheetDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates timesheet draft with user edits."""
    draft = db.scalars(
        select(DailyTimesheetDraft).where(
            DailyTimesheetDraft.id == draft_id,
            DailyTimesheetDraft.user_id == current_user.id,
        )
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Timesheet draft not found.")

    if patch_in.task_summary is not None and patch_in.task_summary != draft.task_summary:
        draft.task_summary = patch_in.task_summary
        # Record manual edit version
        existing_versions = db.scalars(
            select(SummaryVersion).where(SummaryVersion.draft_id == draft.id)
        ).all()
        version = SummaryVersion(
            draft_id=draft.id,
            version_number=len(existing_versions) + 1,
            source="manual-edit",
            summary_text=patch_in.task_summary,
        )
        db.add(version)

    if patch_in.detailed_bullets is not None:
        draft.detailed_bullets_json = json.dumps(patch_in.detailed_bullets)
    if patch_in.project_name is not None:
        draft.project_name = patch_in.project_name
    if patch_in.area_path is not None:
        draft.area_path = patch_in.area_path
    if patch_in.iteration_path is not None:
        draft.iteration_path = patch_in.iteration_path
    if patch_in.hours is not None:
        draft.hours = patch_in.hours
    if patch_in.ph is not None:
        draft.ph = patch_in.ph
    if patch_in.leave is not None:
        draft.leave = patch_in.leave
    if patch_in.half_day is not None:
        draft.half_day = patch_in.half_day
    if patch_in.wfh is not None:
        draft.wfh = patch_in.wfh
    if patch_in.is_user_approved is not None:
        draft.is_user_approved = patch_in.is_user_approved

    db.commit()
    db.refresh(draft)

    bullets = []
    if draft.detailed_bullets_json:
        try:
            bullets = json.loads(draft.detailed_bullets_json)
        except Exception:
            pass

    return TimesheetEntryView(
        id=draft.id,
        date_str=draft.date_str,
        day_of_week=draft.day_of_week,
        client_name=draft.client_name,
        project_name=draft.project_name,
        area_path=draft.area_path,
        iteration_path=draft.iteration_path,
        hours=draft.hours,
        ph=draft.ph,
        leave=draft.leave,
        half_day=draft.half_day,
        wfh=draft.wfh,
        task_summary=draft.task_summary,
        detailed_bullets=bullets,
        is_user_approved=draft.is_user_approved,
        submission_status=draft.submission_status,
        ry_workitem_id=draft.ry_workitem_id,
        last_error=draft.last_error,
    )


@router.post("/submit-day", response_model=SubmissionResult)
async def submit_single_day(
    req: SubmitSingleDayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits a single day timesheet to Rysun Azure DevOps."""
    svc = TimesheetService(db, current_user.id)
    result = await svc.submit_draft_to_rysun(
        draft_id=req.draft_id,
        user_name=current_user.full_name,
        force_update_existing=req.force_update_existing,
    )
    return SubmissionResult(**result)


@router.post("/submit-week", response_model=List[SubmissionResult])
async def submit_week(
    req: SubmitWeekRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits approved timesheet drafts for the week."""
    svc = TimesheetService(db, current_user.id)
    results = []
    for draft_id in req.draft_ids:
        res = await svc.submit_draft_to_rysun(
            draft_id=draft_id,
            user_name=current_user.full_name,
            force_update_existing=req.force_update_existing,
        )
        results.append(SubmissionResult(**res))
    return results
