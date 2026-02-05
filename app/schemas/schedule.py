"""
Pydantic schemas for schedule management API.

Defines request/response schemas for viewing and modifying scheduled jobs.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ScheduleInfo(BaseModel):
    """Response model for schedule information."""
    model_config = ConfigDict(from_attributes=True)

    category: str = Field(description="Product category: Health, Dental, or Group Life")
    job_id: str = Field(description="APScheduler job ID")
    enabled: bool = Field(description="Whether the scheduled job is active")
    next_run_time: Optional[datetime] = Field(
        None,
        description="Next scheduled execution time (Sao Paulo timezone)"
    )
    cron_expression: str = Field(
        description="Cron expression for the schedule"
    )
    last_run_time: Optional[datetime] = Field(
        None,
        description="Last execution time"
    )
    last_run_status: Optional[str] = Field(
        None,
        description="Status of last run: completed, failed"
    )


class ScheduleUpdate(BaseModel):
    """Request model for updating a schedule."""
    hour: Optional[int] = Field(
        None,
        ge=0,
        le=23,
        description="Hour to run (0-23, Sao Paulo time)"
    )
    minute: Optional[int] = Field(
        None,
        ge=0,
        le=59,
        description="Minute to run (0-59)"
    )
    cron_expression: Optional[str] = Field(
        None,
        description="Full cron expression (overrides hour/minute if provided)"
    )
    enabled: Optional[bool] = Field(
        None,
        description="Enable or disable the scheduled job"
    )


class ScheduleList(BaseModel):
    """Response model for list of all schedules."""
    schedules: list[ScheduleInfo]
    timezone: str = Field(
        default="America/Sao_Paulo",
        description="Timezone used for all schedule times"
    )


class ManualTriggerResponse(BaseModel):
    """Response model for manual trigger request."""
    status: str = Field(description="triggered or error")
    category: str = Field(description="Category that was triggered")
    message: str = Field(description="Status message")


class ScheduleHealthResponse(BaseModel):
    """Response model for scheduler health check."""
    scheduler_running: bool = Field(description="Whether scheduler is active")
    jobs_count: int = Field(description="Number of registered jobs")
    timezone: str = Field(description="Configured timezone")
    next_jobs: list[dict] = Field(
        default_factory=list,
        description="Next scheduled jobs with times"
    )
