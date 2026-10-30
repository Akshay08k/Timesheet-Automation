"""Manual activity schemas."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ManualActivityCreate(BaseModel):
    date_str: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    category: str = Field(..., min_length=2, max_length=50)  # Meeting, Discussion, Debugging, etc.
    description: str = Field(..., min_length=3)
    duration_hours: float = Field(default=1.0, ge=0.25, le=24.0)
    project_name: Optional[str] = None
    notes: Optional[str] = None


class ManualActivityUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    duration_hours: Optional[float] = None
    project_name: Optional[str] = None
    notes: Optional[str] = None


class ManualActivityResponse(BaseModel):
    id: int
    date_str: str
    category: str
    description: str
    duration_hours: float
    project_name: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
