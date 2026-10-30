"""Manual activities model for non-code work (meetings, reviews, design, debugging)."""

from typing import Optional
from sqlalchemy import String, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class ManualActivity(Base, TimestampMixin):
    __tablename__ = "manual_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    date_str: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # Meeting, Discussion, Debugging, Documentation, etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_hours: Mapped[Optional[float]] = mapped_column(Float, default=1.0, nullable=True)
    project_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="manual_activities")
