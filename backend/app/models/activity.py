"""Activity item model for normalized engineering activities."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class ActivityItem(Base, TimestampMixin):
    __tablename__ = "activity_items"
    __table_args__ = (
        UniqueConstraint("user_id", "source_type", "external_id", name="uq_user_source_ext_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # commit, pull_request, review, work_item, branch
    external_id: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    repository: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    project: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    author_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    date_str: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD in local timezone

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # JSON-encoded string for related PR / work item IDs or extra metadata
    related_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="activities")
