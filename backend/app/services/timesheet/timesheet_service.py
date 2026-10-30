"""Timesheet orchestration service for drafts, Gemini AI summaries, and Rysun submission."""

from datetime import datetime, timedelta
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.timesheet import DailyTimesheetDraft, SummaryVersion
from backend.app.models.activity import ActivityItem
from backend.app.models.manual_activity import ManualActivity
from backend.app.models.credential import AdoCredential
from backend.app.services.ai.gemini_service import GeminiSummaryService
from backend.app.services.azure_rysun.rysun_service import AzureRysunService


class TimesheetService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.gemini_service = GeminiSummaryService()

    def ensure_week_drafts(self, monday_date_str: str) -> List[DailyTimesheetDraft]:
        """Ensures 5 daily drafts exist for Monday through Friday."""
        start_date = datetime.strptime(monday_date_str, "%Y-%m-%d")
        drafts = []

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

        for i in range(5):
            current_dt = start_date + timedelta(days=i)
            cur_date_str = current_dt.strftime("%Y-%m-%d")
            day_name = day_names[i]

            draft = self.db.scalars(
                select(DailyTimesheetDraft).where(
                    DailyTimesheetDraft.user_id == self.user_id,
                    DailyTimesheetDraft.date_str == cur_date_str,
                )
            ).first()

            if not draft:
                draft = DailyTimesheetDraft(
                    user_id=self.user_id,
                    date_str=cur_date_str,
                    day_of_week=day_name,
                    task_summary="",
                    detailed_bullets_json="[]",
                    client_name="Visual Comfort and Co",
                    project_name="VCC - VCQMS Enhancements and InspectionDB",
                    area_path=r"Rysun Project Management\VC - VCQMS",
                    iteration_path="Rysun Project Management",
                    hours=8.0,
                    ph=False,
                    leave=False,
                    half_day=False,
                    wfh=False,
                    submission_status="draft",
                    is_user_approved=False,
                )
                self.db.add(draft)
                self.db.flush()

            drafts.append(draft)

        self.db.commit()
        return drafts

    def generate_summary_for_date(
        self,
        date_str: str,
        custom_instruction: Optional[str] = None,
    ) -> DailyTimesheetDraft:
        """Collects activities for date, calls Gemini API, and records new summary version."""
        draft = self.db.scalars(
            select(DailyTimesheetDraft).where(
                DailyTimesheetDraft.user_id == self.user_id,
                DailyTimesheetDraft.date_str == date_str,
            )
        ).first()

        if not draft:
            raise ValueError(f"No draft found for date {date_str}.")

        # Retrieve normalized activities
        activities = self.db.scalars(
            select(ActivityItem).where(
                ActivityItem.user_id == self.user_id,
                ActivityItem.date_str == date_str,
                ActivityItem.is_excluded.is_(False),
            )
        ).all()

        commits = [a.__dict__ for a in activities if a.source_type == "commit"]
        prs = [a.__dict__ for a in activities if a.source_type == "pull_request"]
        work_items = [a.__dict__ for a in activities if a.source_type == "work_item"]

        # Retrieve manual activities
        manual = self.db.scalars(
            select(ManualActivity).where(
                ManualActivity.user_id == self.user_id,
                ManualActivity.date_str == date_str,
            )
        ).all()
        manual_dicts = [m.__dict__ for m in manual]

        # Call Gemini AI
        ai_output = self.gemini_service.generate_daily_summary(
            date_str=date_str,
            commits=commits,
            pull_requests=prs,
            work_items=work_items,
            manual_activities=manual_dicts,
            custom_instructions=custom_instruction,
        )

        # Update draft
        draft.task_summary = ai_output.task_summary
        draft.detailed_bullets_json = json.dumps(ai_output.detailed_bullets)
        if ai_output.suggested_project:
            draft.project_name = ai_output.suggested_project
            if "VCQMS" in ai_output.suggested_project:
                draft.area_path = r"Rysun Project Management\VC - VCQMS"
            elif "RMA" in ai_output.suggested_project:
                draft.area_path = r"Rysun Project Management\VCC - RMA Modernization"

        # Count existing versions
        existing_versions = self.db.scalars(
            select(SummaryVersion).where(SummaryVersion.draft_id == draft.id)
        ).all()
        next_version = len(existing_versions) + 1

        version = SummaryVersion(
            draft_id=draft.id,
            version_number=next_version,
            source="gemini-ai" if self.gemini_service.api_key else "rule-fallback",
            summary_text=ai_output.task_summary,
            raw_ai_payload=ai_output.model_dump_json(),
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    async def submit_draft_to_rysun(
        self,
        draft_id: int,
        user_name: str,
        force_update_existing: bool = False,
    ) -> Dict[str, Any]:
        """Submits a single daily draft to Rysun Azure DevOps."""
        draft = self.db.scalars(
            select(DailyTimesheetDraft).where(
                DailyTimesheetDraft.id == draft_id,
                DailyTimesheetDraft.user_id == self.user_id,
            )
        ).first()

        if not draft:
            raise ValueError("Timesheet draft not found.")

        # Credential
        cred = self.db.scalars(
            select(AdoCredential).where(
                AdoCredential.user_id == self.user_id,
                AdoCredential.provider == "rysun",
                AdoCredential.is_valid.is_(True),
            )
        ).first()

        if not cred:
            raise ValueError("No valid Rysun Azure DevOps credential found.")

        rysun_service = AzureRysunService(cred.org_url, cred.encrypted_pat)

        # Check existing
        existing = await rysun_service.search_existing_timesheet(
            date_str=draft.date_str,
            user_identity=cred.resolved_identity_name or user_name,
        )

        title = f"{user_name} - {draft.date_str}"
        fields_patch = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.AreaPath", "value": draft.area_path},
            {"op": "add", "path": "/fields/System.IterationPath", "value": draft.iteration_path},
            {"op": "add", "path": "/fields/System.AssignedTo", "value": cred.resolved_identity_email or cred.resolved_identity_name or user_name},
        ]

        # Custom fields standard mapping
        custom_fields = {
            "Client Name": draft.client_name,
            "Project": draft.project_name,
            "Date": draft.date_str,
            "Day": draft.day_of_week,
            "PH": "Yes" if draft.ph else "No",
            "Leave": "Yes" if draft.leave else "No",
            "Half Day": "Yes" if draft.half_day else "No",
            "WFH": "Yes" if draft.wfh else "No",
            "Hours": draft.hours,
            "Task Summary": draft.task_summary,
        }
        for k, v in custom_fields.items():
            fields_patch.append({
                "op": "add",
                "path": f"/fields/Custom.{k.replace(' ', '')}",
                "value": v,
            })

        try:
            if existing and not force_update_existing:
                return {
                    "draft_id": draft.id,
                    "date_str": draft.date_str,
                    "status": "already_submitted",
                    "workitem_id": existing.get("id"),
                    "message": f"Resource Timesheet #{existing.get('id')} already exists for {draft.date_str}. Explicit update approval required.",
                }
            elif existing and force_update_existing:
                # Update existing
                updated = await rysun_service.update_resource_timesheet(existing["id"], fields_patch)
                draft.ry_workitem_id = updated.get("id")
                draft.submission_status = "submitted"
                draft.last_error = None
                self.db.commit()
                return {
                    "draft_id": draft.id,
                    "date_str": draft.date_str,
                    "status": "updated",
                    "workitem_id": updated.get("id"),
                    "workitem_url": updated.get("_links", {}).get("html", {}).get("href"),
                    "message": f"Updated Resource Timesheet #{updated.get('id')} successfully.",
                }
            else:
                # Create new
                created = await rysun_service.create_resource_timesheet(title, fields_patch)
                draft.ry_workitem_id = created.get("id")
                draft.submission_status = "submitted"
                draft.last_error = None
                self.db.commit()
                return {
                    "draft_id": draft.id,
                    "date_str": draft.date_str,
                    "status": "created",
                    "workitem_id": created.get("id"),
                    "workitem_url": created.get("_links", {}).get("html", {}).get("href"),
                    "message": f"Created Resource Timesheet #{created.get('id')} successfully.",
                }
        except Exception as e:
            draft.submission_status = "failed"
            draft.last_error = str(e)
            self.db.commit()
            return {
                "draft_id": draft.id,
                "date_str": draft.date_str,
                "status": "failed",
                "message": f"Submission failed: {str(e)}",
            }
