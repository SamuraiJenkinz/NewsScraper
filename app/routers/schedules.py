"""
Schedule management router for BrasilIntel.

Provides endpoints to view, modify, and control scheduled category runs.
All times are in Sao Paulo timezone (America/Sao_Paulo).
"""
import logging
from fastapi import APIRouter, HTTPException

from app.services.scheduler_service import SchedulerService
from app.schemas.schedule import (
    ScheduleInfo,
    ScheduleUpdate,
    ScheduleList,
    ManualTriggerResponse,
    ScheduleHealthResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["Schedules"])

VALID_CATEGORIES = ["Health", "Dental", "Group Life"]


def _validate_category(category: str) -> str:
    """Validate and normalize category name."""
    # Try exact match first
    if category in VALID_CATEGORIES:
        return category
    # Try case-insensitive match
    lower_map = {c.lower(): c for c in VALID_CATEGORIES}
    if category.lower() in lower_map:
        return lower_map[category.lower()]
    raise HTTPException(
        status_code=400,
        detail=f"Invalid category: {category}. Valid options: {VALID_CATEGORIES}"
    )


def _schedule_dict_to_info(schedule_dict: dict) -> dict:
    """
    Convert scheduler service dict to ScheduleInfo-compatible dict.

    Maps fields from SchedulerService.get_schedule() to ScheduleInfo schema:
    - paused -> enabled (inverted)
    - trigger -> cron_expression
    """
    return {
        "category": schedule_dict.get("category"),
        "job_id": schedule_dict.get("job_id"),
        "enabled": not schedule_dict.get("paused", True),
        "next_run_time": schedule_dict.get("next_run_time"),
        "cron_expression": schedule_dict.get("trigger") or "",
        "last_run_time": schedule_dict.get("last_run_time"),
        "last_run_status": schedule_dict.get("last_run_status"),
    }


@router.get("", response_model=ScheduleList)
def list_schedules() -> ScheduleList:
    """
    List all scheduled category jobs.

    Returns schedule information for Health, Dental, and Group Life
    including next run time, enabled status, and cron expression.
    """
    scheduler = SchedulerService()
    schedules = scheduler.get_all_schedules()
    return ScheduleList(
        schedules=[ScheduleInfo(**_schedule_dict_to_info(s)) for s in schedules],
        timezone="America/Sao_Paulo"
    )


@router.get("/health", response_model=ScheduleHealthResponse)
def scheduler_health() -> ScheduleHealthResponse:
    """
    Check scheduler health status.

    Returns whether scheduler is running, job count, and next scheduled jobs.
    """
    scheduler = SchedulerService()
    health = scheduler.get_health_status()
    return ScheduleHealthResponse(**health)


@router.get("/{category}", response_model=ScheduleInfo)
def get_schedule(category: str) -> ScheduleInfo:
    """
    Get schedule for a specific category.

    Args:
        category: One of Health, Dental, or Group Life
    """
    category = _validate_category(category)
    scheduler = SchedulerService()
    schedule = scheduler.get_schedule(category)

    if not schedule:
        raise HTTPException(
            status_code=404,
            detail=f"No schedule found for category: {category}"
        )

    return ScheduleInfo(**_schedule_dict_to_info(schedule))


@router.put("/{category}", response_model=ScheduleInfo)
def update_schedule(category: str, update: ScheduleUpdate) -> ScheduleInfo:
    """
    Update schedule configuration for a category.

    Can modify:
    - hour/minute: Set specific daily run time
    - cron_expression: Full cron for custom schedules
    - enabled: Enable or disable the scheduled job

    All times are in Sao Paulo timezone.
    """
    category = _validate_category(category)
    scheduler = SchedulerService()

    try:
        # Handle enable/disable
        if update.enabled is not None:
            if update.enabled:
                scheduler.resume_job(category)
                logger.info(f"Enabled schedule for {category}")
            else:
                scheduler.pause_job(category)
                logger.info(f"Disabled schedule for {category}")

        # Handle time/cron changes
        if update.cron_expression or update.hour is not None or update.minute is not None:
            scheduler.update_schedule(
                category=category,
                hour=update.hour,
                minute=update.minute,
                cron_expression=update.cron_expression
            )
            logger.info(f"Updated schedule for {category}")

        schedule = scheduler.get_schedule(category)
        return ScheduleInfo(**_schedule_dict_to_info(schedule))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update schedule for {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{category}/trigger", response_model=ManualTriggerResponse)
async def trigger_manual_run(category: str) -> ManualTriggerResponse:
    """
    Trigger an immediate run for a category.

    This bypasses the schedule and starts processing immediately.
    The run will be tracked with trigger_type='manual'.
    """
    category = _validate_category(category)
    scheduler = SchedulerService()

    try:
        await scheduler.trigger_now(category)
        return ManualTriggerResponse(
            status="triggered",
            category=category,
            message=f"Manual run triggered for {category}. Check /api/runs for status."
        )
    except Exception as e:
        logger.error(f"Failed to trigger manual run for {category}: {e}")
        return ManualTriggerResponse(
            status="error",
            category=category,
            message=str(e)
        )


@router.post("/{category}/pause", response_model=ScheduleInfo)
def pause_schedule(category: str) -> ScheduleInfo:
    """
    Pause scheduled runs for a category.

    The job remains registered but will not execute until resumed.
    """
    category = _validate_category(category)
    scheduler = SchedulerService()

    try:
        schedule = scheduler.pause_job(category)
        logger.info(f"Paused schedule for {category}")
        return ScheduleInfo(**_schedule_dict_to_info(schedule))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{category}/resume", response_model=ScheduleInfo)
def resume_schedule(category: str) -> ScheduleInfo:
    """
    Resume a paused schedule for a category.
    """
    category = _validate_category(category)
    scheduler = SchedulerService()

    try:
        schedule = scheduler.resume_job(category)
        logger.info(f"Resumed schedule for {category}")
        return ScheduleInfo(**_schedule_dict_to_info(schedule))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
