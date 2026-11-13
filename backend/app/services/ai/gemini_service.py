"""Google Gemini API service for generating timesheet summaries from commit history."""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from backend.app.config.settings import get_settings
from backend.app.schemas.summary import GeminiDailySummaryOutput

logger = logging.getLogger("devtimesheet.gemini")


class GeminiSummaryService:
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = settings.gemini_model  # default: gemini-3.8-flash
        self.fallback_model = settings.gemini_fallback_model  # gemini-3.5-flash
        self._client: Optional[genai.Client] = None

        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")

    def generate_daily_summary(
        self,
        date_str: str,
        commits: List[Dict[str, Any]],
        pull_requests: List[Dict[str, Any]],
        work_items: List[Dict[str, Any]],
        manual_activities: List[Dict[str, Any]],
        custom_instructions: Optional[str] = None,
    ) -> GeminiDailySummaryOutput:
        """Generates a structured daily timesheet summary from Git commits and engineering activity."""
        print(
            f"\n[Gemini AI] Processing {date_str} | Commits: {len(commits)}, PRs: {len(pull_requests)}, WorkItems: {len(work_items)}, Manual: {len(manual_activities)}"
        )

        if not commits and not pull_requests and not work_items and not manual_activities and not custom_instructions:
            print(
                f"[Notice] 0 activities recorded in DB for {date_str}. Returning immediate default summary."
            )
            return GeminiDailySummaryOutput(
                task_summary=f"No development activity recorded for {date_str}.",
                detailed_bullets=[],
                referenced_commit_shas=[],
                referenced_pr_ids=[],
                suggested_project="VCC - VCQMS Enhancements and InspectionDB",
                ambiguities_or_notes="No activities recorded for this date. Click 'Sync Activities from Azure DevOps' to fetch commits/PRs.",
            )

        # Check if client is initialized
        if not self._client or not self.api_key:
            print("[Gemini AI] Gemini API key not configured. Using rule-based summary.")
            return self._generate_rule_based_summary(
                date_str,
                commits,
                pull_requests,
                work_items,
                manual_activities,
                note="Gemini API key not configured. Generated via rule-based summary.",
            )

        # Build prompt payload
        prompt = self._build_prompt_payload(
            date_str=date_str,
            commits=commits,
            pull_requests=pull_requests,
            work_items=work_items,
            manual_activities=manual_activities,
            custom_instructions=custom_instructions,
        )

        system_instruction = (
            "You are an enterprise timesheet assistant. "
            "Summarize the provided Git commits, Pull Requests, and activities into a factual timesheet entry. "
            "Output a concise 1-2 sentence high-level summary and distinct, actionable bullet points in clean README format. "
            "Never estimate hours. Only describe what is explicitly evidenced in the provided items."
        )

        # Try primary model first, then fallback model
        models_to_try = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models_to_try.append(self.fallback_model)

        last_error = None
        for m in models_to_try:
            try:
                print(f"[Gemini AI] Requesting analysis from model '{m}'...")
                response = self._client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=GeminiDailySummaryOutput,
                        max_output_tokens=700,
                    ),
                )

                if response.text:
                    result_data = json.loads(response.text)
                    if "referenced_pr_ids" in result_data and isinstance(result_data["referenced_pr_ids"], list):
                        result_data["referenced_pr_ids"] = [
                            re.sub(r"(?i)\bpr\b|#", "", str(p)).strip() for p in result_data["referenced_pr_ids"] if p
                        ]
                    print(
                        f"[Gemini AI] Summary generated successfully via '{m}': {result_data.get('task_summary', '')[:80]}..."
                    )
                    return GeminiDailySummaryOutput(**result_data)
                else:
                    raise ValueError(f"Empty response text from {m}")

            except Exception as e:
                last_error = e
                print(f"[Gemini AI Warning] Model '{m}' returned error: {e}")
                logger.warning(f"Model '{m}' failed: {e}")

        # If all Gemini models fail, fall back to rule-based summary
        print(f"[Gemini AI] Falling back to deterministic rule-based summary: {last_error}")
        return self._generate_rule_based_summary(
            date_str,
            commits,
            pull_requests,
            work_items,
            manual_activities,
            note=f"Gemini API fallback ({str(last_error)}).",
        )

    def _build_prompt_payload(
        self,
        date_str: str,
        commits: List[Dict[str, Any]],
        pull_requests: List[Dict[str, Any]],
        work_items: List[Dict[str, Any]],
        manual_activities: List[Dict[str, Any]],
        custom_instructions: Optional[str] = None,
    ) -> str:
        """Constructs an ultra-lightweight, high-signal prompt payload containing ONLY title, type, linked items & related info."""
        sections = [f"Date: {date_str}"]

        if custom_instructions:
            sections.append(f"User Special Instructions: {custom_instructions.strip()}")

        activity_lines = ["\n### Verified Activities:"]

        # Commits: Title, Type, Short Ref, Repo (skip pure merge commit duplicates)
        for c in commits:
            title = (c.get("title") or c.get("comment") or "").split("\n")[0].strip()
            t_low = title.lower()
            if t_low.startswith("merge branch ") or t_low.startswith("merge pull request "):
                continue
            sha = (c.get("external_id") or c.get("commitId") or "")[:8]
            repo = c.get("repository") or "VCQMS"
            activity_lines.append(f"- [Type: Commit] Title: {title} | Ref: {sha} | Repo: {repo}")

        # Pull Requests: Title, Type, PR ID, linked Work Item, Repo
        for pr in pull_requests:
            pr_id = str(pr.get("external_id") or pr.get("pullRequestId") or "").lstrip("#")
            title = (pr.get("title") or "").split("\n")[0].strip()
            status = pr.get("status") or "active"
            repo = pr.get("repository") or "VCQMS"
            related = pr.get("related_ids") or ""
            linked_info = f" | Linked: {related}" if related else ""
            activity_lines.append(f"- [Type: Pull Request] Title: {title} | Ref: PR #{pr_id} ({status}){linked_info} | Repo: {repo}")

        # Work Items: Title, Type, WorkItem ID, linked PR, Repo
        for wi in work_items:
            wi_id = str(wi.get("external_id") or wi.get("id") or "")
            title = (wi.get("title") or "").split("\n")[0].strip()
            repo = wi.get("repository") or "VCQMS"
            related = wi.get("related_ids") or ""
            linked_info = f" | Linked: {related}" if related else ""
            activity_lines.append(f"- [Type: Work Item] Title: {title} | Ref: WorkItem #{wi_id}{linked_info} | Repo: {repo}")

        # Manual Activities: Title, Category, Duration
        for ma in manual_activities:
            cat = ma.get("category") or "Activity"
            desc = (ma.get("description") or "").split("\n")[0].strip()
            dur = ma.get("duration_hours") or ""
            activity_lines.append(f"- [Type: Manual Activity ({cat})] Title: {desc} ({dur}h)")

        sections.append("\n".join(activity_lines))
        prompt = "\n".join(sections)

        total_items = len(commits) + len(pull_requests) + len(work_items) + len(manual_activities)
        print(f"[Gemini AI Payload] Lightweight Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens) for {total_items} item(s)")

        return prompt

    def _generate_rule_based_summary(
        self,
        date_str: str,
        commits: List[Dict[str, Any]],
        pull_requests: List[Dict[str, Any]],
        work_items: List[Dict[str, Any]],
        manual_activities: List[Dict[str, Any]],
        note: Optional[str] = None,
    ) -> GeminiDailySummaryOutput:
        """Deterministic rule-based summary fallback when Gemini API is unavailable or offline."""
        bullets = []
        commit_shas = []
        pr_ids = []
        suggested_project = "VCC - VCQMS Enhancements and InspectionDB"

        for c in commits:
            sha = c.get("external_id") or c.get("commitId") or ""
            msg = c.get("title") or c.get("comment", "")
            clean_msg = msg.split("\n")[0].strip()
            # Clean conventional commit prefixes
            for prefix in ["feat:", "fix:", "chore:", "refactor:", "docs:", "style:", "test:"]:
                if clean_msg.lower().startswith(prefix):
                    clean_msg = clean_msg[len(prefix):].strip()
            if clean_msg:
                bullets.append(f"Work on: {clean_msg}")
            if sha:
                commit_shas.append(sha[:8])
            repo = c.get("repository", "").lower()
            if "secondary" in repo or "rma" in repo:
                suggested_project = "VCC - RMA Modernization"
            else:
                suggested_project = "VCC - VCQMS Enhancements and InspectionDB"

        for pr in pull_requests:
            pr_id = str(pr.get("external_id") or pr.get("pullRequestId") or "")
            title = pr.get("title", "")
            bullets.append(f"Pull Request #{pr_id}: {title}")
            if pr_id:
                pr_ids.append(pr_id)

        for wi in work_items:
            wi_id = str(wi.get("external_id") or wi.get("id") or "")
            wi_title = wi.get("title", "").strip().split("\n")[0]
            bullets.append(f"WorkItem #{wi_id}: {wi_title}")

        for ma in manual_activities:
            cat = ma.get("category", "Activity")
            desc = ma.get("description", "")
            bullets.append(f"{cat}: {desc}")

        if not bullets:
            summary = f"No development activity recorded for {date_str}."
        else:
            summary = "; ".join(bullets[:3])
            if len(summary) > 200:
                summary = summary[:197] + "..."

        return GeminiDailySummaryOutput(
            task_summary=summary,
            detailed_bullets=bullets,
            referenced_commit_shas=commit_shas,
            referenced_pr_ids=pr_ids,
            suggested_project=suggested_project or "VCC - VCQMS Enhancements and InspectionDB",
            ambiguities_or_notes=note,
        )
