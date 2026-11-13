"""Schemas for AI daily summary generation using Google Gemini API."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class GeminiDailySummaryOutput(BaseModel):
    """Structured response schema returned by Google Gemini API."""
    task_summary: str = Field(
        description="A concise timesheet summary formatted in README format for the Rysun Task Summary field."
    )
    detailed_bullets: List[str] = Field(
        default_factory=list,
        description="Bullet points describing specific engineering tasks completed based on commits and PRs."
    )
    referenced_commit_shas: List[str] = Field(
        default_factory=list,
        description="List of commit SHAs directly supporting this summary."
    )
    referenced_pr_ids: List[str] = Field(
        default_factory=list,
        description="List of Pull Request IDs referenced."
    )
    suggested_project: Optional[str] = Field(
        default="VCC - VCQMS Enhancements and InspectionDB",
        description="Must be strictly either 'VCC - VCQMS Enhancements and InspectionDB' or 'VCC - RMA Modernization'."
    )
    ambiguities_or_notes: Optional[str] = Field(
        default=None,
        description="Flags if commit messages were vague or require clarification."
    )


class GenerateSummaryRequest(BaseModel):
    date_str: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    regenerate: bool = False
    custom_instruction: Optional[str] = None


class GenerateWeekSummaryRequest(BaseModel):
    monday_date_str: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    custom_instruction: Optional[str] = None


class SummaryVersionResponse(BaseModel):
    id: int
    version_number: int
    source: str
    summary_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailySummaryResponse(BaseModel):
    date_str: str
    day_of_week: str
    task_summary: str
    detailed_bullets: List[str]
    suggested_project: Optional[str] = None
    ambiguities_or_notes: Optional[str] = None
    versions: List[SummaryVersionResponse]
    hours: float
    ph: bool
    leave: bool
    half_day: bool
    wfh: bool
