"""Manual activities API routes using MongoDB (meetings, discussions, debugging, etc.)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database
from backend.app.models.database import get_db, get_next_sequence_value
from backend.app.models.user import User
from backend.app.models.manual_activity import ManualActivity
from backend.app.schemas.manual_activity import (
    ManualActivityCreate,
    ManualActivityUpdate,
    ManualActivityResponse,
)
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/manual-activities", tags=["manual-activities"])


@router.get("", response_model=List[ManualActivityResponse])
def get_manual_activities(
    date_str: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retrieves manual activities for user from MongoDB."""
    query = {"user_id": current_user.id}
    if date_str:
        query["date_str"] = date_str
    docs = db.manual_activities.find(query).sort("date_str", 1)
    return [ManualActivity.from_doc(d) for d in docs]


@router.post("", response_model=ManualActivityResponse, status_code=status.HTTP_201_CREATED)
def create_manual_activity(
    activity_in: ManualActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Adds a new manual non-code activity into MongoDB."""
    new_id = get_next_sequence_value(db, "manual_activities")
    activity = ManualActivity(
        id=new_id,
        user_id=current_user.id,
        date_str=activity_in.date_str,
        category=activity_in.category,
        description=activity_in.description,
        duration_hours=activity_in.duration_hours,
        project_name=activity_in.project_name,
        notes=activity_in.notes,
    )
    db.manual_activities.insert_one(activity.to_dict())
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manual_activity(
    activity_id: int,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Deletes a manual activity from MongoDB."""
    db.manual_activities.delete_one(
        {"id": activity_id, "user_id": current_user.id}
    )
    return None
