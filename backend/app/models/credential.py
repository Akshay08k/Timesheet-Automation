"""Azure DevOps Credentials model for storing encrypted PATs per user."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class AdoCredential(Base, TimestampMixin):
    __tablename__ = "ado_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # "client" or "rysun"
    org_url: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_pat: Mapped[str] = mapped_column(String(512), nullable=False)

    # Validated identity information
    resolved_identity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolved_identity_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolved_identity_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="credentials")
