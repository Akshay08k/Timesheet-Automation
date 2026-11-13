"""Timesheet orchestration service for drafts, Gemini AI summaries, and Rysun submission with MongoDB."""

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import json
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from backend.app.config.settings import get_settings
from backend.app.models.database import get_next_sequence_value
from backend.app.models.timesheet import DailyTimesheetDraft, SummaryVersion
from backend.app.models.activity import ActivityItem
from backend.app.models.manual_activity import ManualActivity
from backend.app.models.credential import AdoCredential
from backend.app.services.ai.gemini_service import GeminiSummaryService
from backend.app.services.azure_rysun.rysun_service import AzureRysunService


def format_readme_summary(overview: Optional[str], bullets: Optional[List[str]]) -> str:
    """Formats timesheet summary into standard README (Markdown) format:
    High-level summary paragraph followed by point-wise bullet items (- item).
    """
    summary_text = (overview or "").strip()
    cleaned_bullets = []
    if bullets:
        for b in bullets:
            if isinstance(b, str) and b.strip():
                clean_b = b.strip().lstrip("-*• \t").strip()
                if clean_b:
                    cleaned_bullets.append(clean_b)

    if not cleaned_bullets:
        return summary_text

    # Avoid duplicating if bullets are already present in summary_text
    first_core = cleaned_bullets[0][:25] if len(cleaned_bullets[0]) >= 25 else cleaned_bullets[0]
    if first_core and first_core in summary_text:
        return summary_text

    bullet_md = "\n".join(f"- {b}" for b in cleaned_bullets)
    if summary_text:
        return f"{summary_text}\n\n{bullet_md}"
    return bullet_md


class TimesheetService:
    def __init__(self, db: Database, user_id: int):
        self.db = db
        self.user_id = user_id
        self.settings = get_settings()
        self.gemini_service = GeminiSummaryService()

    def ensure_week_drafts(self, monday_date_str: str) -> List[DailyTimesheetDraft]:
        """Ensures 5 daily drafts exist in MongoDB for Monday through Friday using a fast single batch query."""
        start_date = datetime.strptime(monday_date_str, "%Y-%m-%d")
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        cur_date_strs = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]

        # Batch query all 5 dates in a single round trip
        existing_docs = list(
            self.db.daily_timesheet_drafts.find(
                {"user_id": self.user_id, "date_str": {"$in": cur_date_strs}}
            )
        )
        existing_by_date = {d["date_str"]: DailyTimesheetDraft.from_doc(d) for d in existing_docs}

        drafts: List[DailyTimesheetDraft] = []
        for i, cur_date_str in enumerate(cur_date_strs):
            if cur_date_str in existing_by_date:
                drafts.append(existing_by_date[cur_date_str])
            else:
                new_id = get_next_sequence_value(self.db, "daily_timesheet_drafts")
                draft = DailyTimesheetDraft(
                    id=new_id,
                    user_id=self.user_id,
                    date_str=cur_date_str,
                    day_of_week=day_names[i],
                    task_summary="",
                    detailed_bullets_json="[]",
                    client_name=self.settings.default_client_name,
                    project_name=self.settings.default_project_name,
                    area_path=self.settings.default_area_path,
                    iteration_path=self.settings.default_iteration,
                    hours=8.0,
                    ph=False,
                    leave=False,
                    half_day=False,
                    wfh=False,
                    submission_status="draft",
                    is_user_approved=False,
                )
                try:
                    self.db.daily_timesheet_drafts.insert_one(draft.to_dict())
                except Exception:
                    doc = self.db.daily_timesheet_drafts.find_one(
                        {"user_id": self.user_id, "date_str": cur_date_str}
                    )
                    if doc:
                        draft = DailyTimesheetDraft.from_doc(doc)
                drafts.append(draft)

        return drafts

    def generate_summary_for_date(
        self,
        date_str: str,
        custom_instruction: Optional[str] = None,
    ) -> DailyTimesheetDraft:
        """Collects activities for date, calls Gemini API, and records new summary version in MongoDB."""
        draft_doc = self.db.daily_timesheet_drafts.find_one(
            {"user_id": self.user_id, "date_str": date_str}
        )

        if not draft_doc:
            raise ValueError(f"No draft found for date {date_str}.")

        draft = DailyTimesheetDraft.from_doc(draft_doc)

        # Retrieve normalized activities
        act_docs = list(
            self.db.activity_items.find(
                {"user_id": self.user_id, "date_str": date_str, "is_excluded": False}
            )
        )

        commits = [d for d in act_docs if d.get("source_type") == "commit"]
        prs = [d for d in act_docs if d.get("source_type") == "pull_request"]
        work_items = [d for d in act_docs if d.get("source_type") == "work_item"]

        # Retrieve manual activities
        manual_docs = list(
            self.db.manual_activities.find(
                {"user_id": self.user_id, "date_str": date_str}
            )
        )

        # Call Gemini AI
        ai_output = self.gemini_service.generate_daily_summary(
            date_str=date_str,
            commits=commits,
            pull_requests=prs,
            work_items=work_items,
            manual_activities=manual_docs,
            custom_instructions=custom_instruction,
        )

        # Update draft fields with point-wise README format
        draft.task_summary = format_readme_summary(ai_output.task_summary, ai_output.detailed_bullets)
        draft.detailed_bullets_json = json.dumps(ai_output.detailed_bullets)
        if ai_output.suggested_project:
            proj_str = ai_output.suggested_project.strip()
            if "secondary" in proj_str.lower() or "rma" in proj_str.lower():
                draft.project_name = "VCC - RMA Modernization"
                draft.area_path = r"Rysun Project Management\VCC - RMA Modernization"
            else:
                draft.project_name = self.settings.default_project_name
                draft.area_path = self.settings.default_area_path

        # Count existing versions
        existing_count = self.db.summary_versions.count_documents({"draft_id": draft.id})
        next_version = existing_count + 1

        v_id = get_next_sequence_value(self.db, "summary_versions")
        version = SummaryVersion(
            id=v_id,
            draft_id=draft.id,
            version_number=next_version,
            source="gemini-ai" if self.gemini_service.api_key else "rule-fallback",
            summary_text=ai_output.task_summary,
            raw_ai_payload=ai_output.model_dump_json(),
        )
        self.db.summary_versions.insert_one(version.to_dict())

        # Persist draft updates in MongoDB
        self.db.daily_timesheet_drafts.update_one(
            {"id": draft.id},
            {
                "$set": {
                    "task_summary": draft.task_summary,
                    "detailed_bullets_json": draft.detailed_bullets_json,
                    "project_name": draft.project_name,
                    "area_path": draft.area_path,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return draft

    def generate_week_summaries(
        self,
        monday_date_str: str,
        custom_instruction: Optional[str] = None,
    ) -> List[DailyTimesheetDraft]:
        """Generates AI timesheet summaries for all 5 weekdays in parallel."""
        drafts = self.ensure_week_drafts(monday_date_str)
        
        def _process_draft(draft: DailyTimesheetDraft) -> DailyTimesheetDraft:
            return self.generate_summary_for_date(draft.date_str, custom_instruction)

        with ThreadPoolExecutor(max_workers=5) as executor:
            updated_drafts = list(executor.map(_process_draft, drafts))

        # Preserve Monday through Friday order
        updated_drafts.sort(key=lambda d: d.date_str)
        return updated_drafts

    async def submit_draft_to_rysun(
        self,
        draft_id: int,
        user_name: str,
        force_update_existing: bool = False,
    ) -> Dict[str, Any]:
        """Submits a single daily draft to Rysun Azure DevOps and tracks status in MongoDB."""
        draft_doc = self.db.daily_timesheet_drafts.find_one(
            {"id": draft_id, "user_id": self.user_id}
        )

        if not draft_doc:
            raise ValueError("Timesheet draft not found.")

        draft = DailyTimesheetDraft.from_doc(draft_doc)

        # Credential (supports both 'rysun' and 'mycompany' provider keys)
        cred_doc = self.db.ado_credentials.find_one(
            {
                "user_id": self.user_id,
                "provider": {"$in": ["rysun", "mycompany"]},
                "is_valid": True,
            }
        )

        if not cred_doc:
            raise ValueError("No valid Rysun Azure DevOps credential found.")

        cred = AdoCredential.from_doc(cred_doc)
        rysun_service = AzureRysunService(cred.org_url, cred.encrypted_pat)

        user_doc = self.db.users.find_one({"id": self.user_id}) or {}
        user_identity = cred.resolved_identity_name or user_name or user_doc.get("full_name") or user_doc.get("username")
        user_email = cred.resolved_identity_email or user_doc.get("email")

        # Check existing scoped strictly to this user
        existing = await rysun_service.search_existing_timesheet(
            date_str=draft.date_str,
            user_identity=user_identity,
            user_email=user_email,
        )

        # Prepare Task Summary in README (Markdown) format:
        # High-level overview paragraph followed by point-wise bullet items (- item)
        bullets = []
        if draft.detailed_bullets_json:
            try:
                bullets = json.loads(draft.detailed_bullets_json)
            except Exception:
                bullets = []

        summary_text = format_readme_summary(draft.task_summary, bullets)

        if not summary_text:
            return {
                "draft_id": draft.id,
                "date_str": draft.date_str,
                "status": "failed",
                "message": (
                    f"Submission stopped: 'Task Summary' is required by Azure DevOps for {draft.date_str} ({draft.day_of_week}). "
                    "Please write a task description or generate one with Gemini AI before submitting."
                ),
            }

        # Normalize project and area path with fallback to configured defaults
        project_val = draft.project_name or self.settings.default_project_name
        area_path_val = draft.area_path or self.settings.default_area_path

        preferred_name = user_name or cred.resolved_identity_name or user_doc.get("full_name") or user_doc.get("username")
        title = f"{preferred_name} - {draft.date_str}"
        fields_patch = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.AreaPath", "value": area_path_val},
            {"op": "add", "path": "/fields/System.IterationPath", "value": draft.iteration_path},
            {
                "op": "add",
                "path": "/fields/System.AssignedTo",
                "value": cred.resolved_identity_email or user_email or cred.resolved_identity_name or preferred_name,
            },
        ]

        # Custom fields standard mapping
        custom_fields = {
            "Client Name": draft.client_name,
            "Project": project_val,
            "Date": draft.date_str,
            "Day": draft.day_of_week,
            "PH": "Yes" if draft.ph else "No",
            "Leave": "Yes" if draft.leave else "No",
            "Half Day": "Yes" if draft.half_day else "No",
            "WFH": "Yes" if draft.wfh else "No",
            "Hours": draft.hours,
            "Task Summary": summary_text,
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
                workitem_id = updated.get("id")
                self.db.daily_timesheet_drafts.update_one(
                    {"id": draft.id},
                    {
                        "$set": {
                            "ry_workitem_id": workitem_id,
                            "mycompany_workitem_id": workitem_id,
                            "submission_status": "submitted",
                            "last_error": None,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
                return {
                    "draft_id": draft.id,
                    "date_str": draft.date_str,
                    "status": "updated",
                    "workitem_id": workitem_id,
                    "workitem_url": updated.get("_links", {}).get("html", {}).get("href"),
                    "message": f"Updated Resource Timesheet #{workitem_id} successfully.",
                }
            else:
                # Create new
                created = await rysun_service.create_resource_timesheet(title, fields_patch)
                workitem_id = created.get("id")
                self.db.daily_timesheet_drafts.update_one(
                    {"id": draft.id},
                    {
                        "$set": {
                            "ry_workitem_id": workitem_id,
                            "mycompany_workitem_id": workitem_id,
                            "submission_status": "submitted",
                            "last_error": None,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
                return {
                    "draft_id": draft.id,
                    "date_str": draft.date_str,
                    "status": "created",
                    "workitem_id": workitem_id,
                    "workitem_url": created.get("_links", {}).get("html", {}).get("href"),
                    "message": f"Created Resource Timesheet #{workitem_id} successfully.",
                }
        except Exception as e:
            self.db.daily_timesheet_drafts.update_one(
                {"id": draft.id},
                {
                    "$set": {
                        "submission_status": "failed",
                        "last_error": str(e),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            return {
                "draft_id": draft.id,
                "date_str": draft.date_str,
                "status": "failed",
                "message": f"Submission failed: {str(e)}",
            }

    # Compatibility alias
    submit_draft_to_mycompany = submit_draft_to_rysun
