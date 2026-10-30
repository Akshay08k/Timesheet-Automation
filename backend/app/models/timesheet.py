"""Daily timesheet draft and AI summary versioning models."""

from typing import List, Optional
from sqlalchemy import String, Float, Boolean, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class DailyTimesheetDraft(Base, TimestampMixin):
    __tablename__ = "daily_timesheet_drafts"
    __table_args__ = (
        UniqueConstraint("user_id", "date_str", name="uq_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    date_str: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    day_of_week: Mapped[str] = mapped_column(String(15), nullable=False)  # Monday, Tuesday, ...

    # Summary fields
    task_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detailed_bullets_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Project and area mapping
    client_name: Mapped[str] = mapped_column(String(100), default="Visual Comfort and Co", nullable=False)
    project_name: Mapped[str] = mapped_column(String(150), nullable=False, default="VCC - VCQMS Enhancements and InspectionDB")
    area_path: Mapped[str] = mapped_column(String(200), nullable=False, default=r"Rysun Project Management\VC - VCQMS")
    iteration_path: Mapped[str] = mapped_column(String(200), nullable=False, default="Rysun Project Management")

    # Time and special-day flags
    hours: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)
    ph: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Public Holiday
    leave: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    half_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wfh: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Rysun submission tracking
    ry_workitem_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    submission_status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False
    )  # draft, pending_review, submitted, failed
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_user_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="timesheet_drafts")
    summary_versions: Mapped[List["SummaryVersion"]] = relationship(
        "SummaryVersion", back_populates="draft", cascade="all, delete-orphan", order_by="SummaryVersion.version_number"
    )


class SummaryVersion(Base, TimestampMixin):
    __tablename__ = "summary_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("daily_timesheet_drafts.id", ondelete="CASCADE"), nullable=False, index=True)

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # "gemini-ai", "manual-edit", "rule-fallback"
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_ai_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON structured output

    draft: Mapped["DailyTimesheetDraft"] = relationship("DailyTimesheetDraft", back_populates="summary_versions")
