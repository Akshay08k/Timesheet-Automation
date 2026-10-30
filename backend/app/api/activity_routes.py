"""Activity API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.models.activity import ActivityItem
from backend.app.schemas.activity import (
    ActivityItemResponse,
    ActivitySyncRequest,
    ActivitySyncResponse,
)
from backend.app.services.activity.activity_service import ActivityService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("", response_model=List[ActivityItemResponse])
def get_activities(
    date_str: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    source_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves activities for the logged in user with optional date and type filters."""
    stmt = select(ActivityItem).where(ActivityItem.user_id == current_user.id)
    if date_str:
        stmt = stmt.where(ActivityItem.date_str == date_str)
    if source_type:
        stmt = stmt.where(ActivityItem.source_type == source_type)

    stmt = stmt.order_by(ActivityItem.occurred_at.desc())
    items = db.scalars(stmt).all()
    return items


@router.post("/sync", response_model=ActivitySyncResponse)
async def sync_activities(
    sync_req: ActivitySyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers synchronization from Client Azure DevOps for the given date range."""
    svc = ActivityService(db, current_user.id, current_user.timezone)
    try:
        result = await svc.sync_client_activities(sync_req.start_date, sync_req.end_date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}")


@router.patch("/{activity_id}/toggle-exclude", response_model=ActivityItemResponse)
def toggle_activity_exclusion(
    activity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggles whether an activity is excluded from AI summary generation."""
    item = db.scalars(
        select(ActivityItem).where(
            ActivityItem.id == activity_id,
            ActivityItem.user_id == current_user.id,
        )
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Activity not found.")

    item.is_excluded = not item.is_excluded
    db.commit()
    db.refresh(item)
    return item
