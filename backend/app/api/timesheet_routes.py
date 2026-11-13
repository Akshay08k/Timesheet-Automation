"""Timesheet review, editing, and submission API routes using MongoDB."""

import asyncio
from datetime import datetime, timezone
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from backend.app.models.database import get_db, get_next_sequence_value
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
from backend.app.services.azure_rysun.rysun_service import AzureRysunService, AzureMyCompanyService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/timesheets", tags=["timesheets"])


@router.get("/week/{monday_date_str}", response_model=WeeklyReviewResponse)
async def get_weekly_review(
    monday_date_str: str,
    check_remote: bool = Query(False, description="Whether to query Azure DevOps for existing remote timesheets (default false for fast loading)"),
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retrieves or prepares the 5 Monday-Friday timesheet entries for a selected week from MongoDB."""
    svc = TimesheetService(db, current_user.id)
    drafts = svc.ensure_week_drafts(monday_date_str)

    # Check Rysun credential (supports both 'rysun' and 'mycompany' provider keys)
    cred_doc = db.ado_credentials.find_one(
        {
            "user_id": current_user.id,
            "provider": {"$in": ["rysun", "mycompany"]},
            "is_valid": True,
        }
    )

    rysun_service = None
    cred = None
    if cred_doc:
        cred = AdoCredential.from_doc(cred_doc)
        try:
            rysun_service = AzureRysunService(cred.org_url, cred.encrypted_pat)
        except Exception:
            pass

    # Check existing records in Rysun ONLY if explicitly requested, run in PARALLEL
    existing_map = {}
    if check_remote and rysun_service and cred:
        async def check_day(d_date: str):
            try:
                res = await rysun_service.search_existing_timesheet(
                    date_str=d_date,
                    user_identity=cred.resolved_identity_name or current_user.full_name,
                )
                return d_date, res
            except Exception:
                return d_date, None

        dates_to_check = [d.date_str for d in drafts if d.submission_status != "submitted"]
        if dates_to_check:
            try:
                results = await asyncio.gather(*[check_day(ds) for ds in dates_to_check])
                existing_map = dict(results)
            except Exception:
                existing_map = {}

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

        existing_info = existing_map.get(d.date_str)

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
                mycompany_workitem_id=d.mycompany_workitem_id or d.ry_workitem_id,
                ry_workitem_id=d.mycompany_workitem_id or d.ry_workitem_id,
                last_error=d.last_error,
                existing_mycompany_item=existing_info,
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
    db: Database = Depends(get_db),
):
    """Updates timesheet draft with user edits in MongoDB."""
    draft_doc = db.daily_timesheet_drafts.find_one(
        {
            "id": draft_id,
            "user_id": current_user.id,
        }
    )

    if not draft_doc:
        raise HTTPException(status_code=404, detail="Timesheet draft not found.")

    draft = DailyTimesheetDraft.from_doc(draft_doc)
    update_fields = {}

    if patch_in.task_summary is not None and patch_in.task_summary != draft.task_summary:
        update_fields["task_summary"] = patch_in.task_summary
        draft.task_summary = patch_in.task_summary

        # Record or update manual edit version without spamming versions
        last_version = db.summary_versions.find_one(
            {"draft_id": draft.id},
            sort=[("version_number", -1)]
        )
        if last_version and last_version.get("source") == "manual-edit":
            db.summary_versions.update_one(
                {"id": last_version["id"]},
                {"$set": {"summary_text": patch_in.task_summary}}
            )
        else:
            version_count = db.summary_versions.count_documents({"draft_id": draft.id})
            v_id = get_next_sequence_value(db, "summary_versions")
            version = SummaryVersion(
                id=v_id,
                draft_id=draft.id,
                version_number=version_count + 1,
                source="manual-edit",
                summary_text=patch_in.task_summary,
            )
            db.summary_versions.insert_one(version.to_dict())

    if patch_in.detailed_bullets is not None:
        update_fields["detailed_bullets_json"] = json.dumps(patch_in.detailed_bullets)
        draft.detailed_bullets_json = update_fields["detailed_bullets_json"]
    if patch_in.project_name is not None:
        update_fields["project_name"] = patch_in.project_name
        draft.project_name = patch_in.project_name
    if patch_in.area_path is not None:
        update_fields["area_path"] = patch_in.area_path
        draft.area_path = patch_in.area_path
    if patch_in.iteration_path is not None:
        update_fields["iteration_path"] = patch_in.iteration_path
        draft.iteration_path = patch_in.iteration_path
    if patch_in.hours is not None:
        update_fields["hours"] = patch_in.hours
        draft.hours = patch_in.hours
    if patch_in.ph is not None:
        update_fields["ph"] = patch_in.ph
        draft.ph = patch_in.ph
    if patch_in.leave is not None:
        update_fields["leave"] = patch_in.leave
        draft.leave = patch_in.leave
    if patch_in.half_day is not None:
        update_fields["half_day"] = patch_in.half_day
        draft.half_day = patch_in.half_day
    if patch_in.wfh is not None:
        update_fields["wfh"] = patch_in.wfh
        draft.wfh = patch_in.wfh
    if patch_in.is_user_approved is not None:
        update_fields["is_user_approved"] = patch_in.is_user_approved
        draft.is_user_approved = patch_in.is_user_approved

    if update_fields:
        update_fields["updated_at"] = datetime.now(timezone.utc)
        db.daily_timesheet_drafts.update_one(
            {"id": draft.id},
            {"$set": update_fields},
        )

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
        mycompany_workitem_id=draft.mycompany_workitem_id or draft.ry_workitem_id,
        ry_workitem_id=draft.mycompany_workitem_id or draft.ry_workitem_id,
        last_error=draft.last_error,
    )


@router.post("/submit-day", response_model=SubmissionResult)
async def submit_single_day(
    req: SubmitSingleDayRequest,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
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
    db: Database = Depends(get_db),
):
    """Submits approved timesheet drafts for the week to Rysun Azure DevOps."""
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
