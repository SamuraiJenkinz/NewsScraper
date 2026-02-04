"""
Pydantic schemas for Run model.

Defines request/response schemas for scraping run tracking.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class RunStatus(str, Enum):
    """Status values for scraping runs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(str, Enum):
    """How the run was initiated."""
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class RunBase(BaseModel):
    """Base schema with common fields."""
    category: str
    trigger_type: TriggerType = TriggerType.MANUAL


class RunCreate(RunBase):
    """Schema for creating a new run."""
    pass


class RunRead(RunBase):
    """Schema for reading run data from database."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: RunStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    insurers_processed: int
    items_found: int
    error_message: Optional[str] = None
