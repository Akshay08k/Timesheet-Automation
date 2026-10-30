"""User model for multi-user isolation."""

from typing import List, Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)

    # Relationships
    credentials: Mapped[List["AdoCredential"]] = relationship(
        "AdoCredential", back_populates="user", cascade="all, delete-orphan"
    )
    activities: Mapped[List["ActivityItem"]] = relationship(
        "ActivityItem", back_populates="user", cascade="all, delete-orphan"
    )
    manual_activities: Mapped[List["ManualActivity"]] = relationship(
        "ManualActivity", back_populates="user", cascade="all, delete-orphan"
    )
    timesheet_drafts: Mapped[List["DailyTimesheetDraft"]] = relationship(
        "DailyTimesheetDraft", back_populates="user", cascade="all, delete-orphan"
    )
