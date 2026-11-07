"""Activity API routes using MongoDB."""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.models.activity import ActivityItem
from backend.app.schemas.activity import (
    ActivityItemResponse,
    ActivitySyncRequest,
    ActivitySyncResponse,
    ClientVcqmsContextResponse,
)
from backend.app.services.activity.activity_service import ActivityService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("", response_model=List[ActivityItemResponse])
def get_activities(
    date_str: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    source_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retrieves activities from MongoDB for the logged in user with optional date and type filters."""
    query = {"user_id": current_user.id}
    if date_str:
        query["date_str"] = date_str
    if source_type:
        query["source_type"] = source_type

    docs = db.activity_items.find(query).sort("occurred_at", -1)
    return [ActivityItem.from_doc(d) for d in docs]


@router.get("/client-context")
@router.get("/vcqms-context")
async def get_client_vcqms_context(
    start_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    sync_to_db: bool = Query(True, description="Whether to also store/update fetched events in MongoDB"),
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """GET endpoint to retrieve all context from Client Azure DevOps strictly scoped to VCQMS repository & PR-linked Work Items.
    Defaults to current work week (Monday to Friday) if dates are not specified.
    """
    if not start_date or not end_date:
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)
        start_date = start_date or monday.strftime("%Y-%m-%d")
        end_date = end_date or friday.strftime("%Y-%m-%d")

    svc = ActivityService(db, current_user.id, current_user.timezone)
    try:
        context = await svc.get_vcqms_context(start_date, end_date, sync_to_db=sync_to_db)
        return context
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve VCQMS context: {str(e)}")


@router.post("/sync", response_model=ActivitySyncResponse)
async def sync_activities(
    sync_req: ActivitySyncRequest,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Triggers synchronization from Client Azure DevOps for the given date range into MongoDB."""
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
    db: Database = Depends(get_db),
):
    """Toggles whether an activity is excluded from AI summary generation in MongoDB."""
    item_doc = db.activity_items.find_one(
        {"id": activity_id, "user_id": current_user.id}
    )

    if not item_doc:
        raise HTTPException(status_code=404, detail="Activity not found.")

    new_val = not item_doc.get("is_excluded", False)
    db.activity_items.update_one(
        {"id": activity_id},
        {"$set": {"is_excluded": new_val}},
    )
    item_doc["is_excluded"] = new_val
    return ActivityItem.from_doc(item_doc)
