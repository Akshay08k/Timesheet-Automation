"""Google Gemini API service for generating timesheet summaries from commit history."""

import json
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from backend.app.config.settings import get_settings
from backend.app.schemas.summary import GeminiDailySummaryOutput

logger = logging.getLogger(__name__)


class GeminiSummaryService:
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = settings.gemini_model  # default: gemini-2.5-flash
        self.fallback_model = settings.gemini_fallback_model  # gemini-1.5-flash
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
        # Check if client is initialized
        if not self._client or not self.api_key:
            logger.warning("Gemini API key is not configured. Falling back to rule-based summary.")
            return self._generate_rule_based_summary(
                date_str, commits, pull_requests, work_items, manual_activities, note="Gemini API key not configured. Generated via rule-based summary."
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
            "You are an assistant for professional enterprise timesheet generation. "
            "Your job is to examine the developer's Git commits, Pull Requests, work items, and manual activities "
            "for a given working day and produce an accurate, factual timesheet entry.\n\n"
            "STRICT RULES:\n"
            "1. Grounding: You must strictly summarize only what is explicitly evidenced in the provided commit messages and activities. "
            "Never invent tasks or claim features were implemented if not mentioned.\n"
            "2. No Hours: Never estimate, guess, or assign working hours.\n"
            "3. Formatting: Produce a concise 1-3 sentence high-level summary suitable for client review, along with actionable bullet points.\n"
            "4. References: List all commit SHAs and PR IDs that support your summary.\n"
            "5. Ambiguity: If commit messages are vague (e.g., 'wip', 'fix', 'changes'), note this in ambiguities_or_notes."
        )

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=GeminiDailySummaryOutput,
                ),
            )

            if response.text:
                result_data = json.loads(response.text)
                return GeminiDailySummaryOutput(**result_data)
            else:
                raise ValueError("Empty response text from Gemini API")

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}. Falling back to rule-based summary.")
            return self._generate_rule_based_summary(
                date_str, commits, pull_requests, work_items, manual_activities, note=f"Gemini API error ({str(e)}). Fallback generated."
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
        """Constructs an information-dense prompt without sending source code or secrets."""
        sections = [f"Date: {date_str}"]

        if custom_instructions:
            sections.append(f"User Special Instructions: {custom_instructions}")

        # Git Commits
        if commits:
            commit_lines = ["\n### Git Commits:"]
            for c in commits:
                sha = c.get("external_id") or c.get("commitId") or ""
                repo = c.get("repository", "")
                msg = c.get("title") or c.get("comment", "")
                commit_lines.append(f"- [{repo}] {sha[:8]}: {msg.strip()}")
            sections.append("\n".join(commit_lines))
        else:
            sections.append("\n### Git Commits: None")

        # Pull Requests
        if pull_requests:
            pr_lines = ["\n### Pull Requests:"]
            for pr in pull_requests:
                pr_id = pr.get("external_id") or pr.get("pullRequestId") or ""
                title = pr.get("title", "")
                status = pr.get("status", "")
                repo = pr.get("repository", "")
                pr_lines.append(f"- [{repo}] PR #{pr_id} ({status}): {title.strip()}")
            sections.append("\n".join(pr_lines))

        # Work Items
        if work_items:
            wi_lines = ["\n### Azure DevOps Work Items:"]
            for wi in work_items:
                wi_id = wi.get("external_id") or wi.get("id") or ""
                title = wi.get("title", "")
                wi_lines.append(f"- WorkItem #{wi_id}: {title.strip()}")
            sections.append("\n".join(wi_lines))

        # Manual Activities (Meetings, Discussions, Debugging)
        if manual_activities:
            ma_lines = ["\n### Developer Non-Code Activities:"]
            for ma in manual_activities:
                cat = ma.get("category", "Activity")
                desc = ma.get("description", "")
                dur = ma.get("duration_hours", "")
                ma_lines.append(f"- [{cat}] ({dur}h): {desc.strip()}")
            sections.append("\n".join(ma_lines))

        return "\n".join(sections)

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
        suggested_project = None

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
            if "vcqms" in repo:
                suggested_project = "VCC - VCQMS Enhancements and InspectionDB"
            elif "rma" in repo:
                suggested_project = "VCC - RMA Modernization"

        for pr in pull_requests:
            pr_id = str(pr.get("external_id") or pr.get("pullRequestId") or "")
            title = pr.get("title", "")
            bullets.append(f"Pull Request #{pr_id}: {title}")
            if pr_id:
                pr_ids.append(pr_id)

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
