"""
Scheduler service for automated category runs.

Manages APScheduler with Sao Paulo timezone, SQLite job persistence,
and methods for job management (start, stop, pause, resume, reschedule).
"""
import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Singleton scheduler service for managing automated category runs.

    Uses APScheduler with:
    - AsyncIO scheduler for FastAPI compatibility
    - SQLite job store for persistence across restarts
    - Sao Paulo timezone for Brazilian business hours
    """

    # Singleton instance
    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[AsyncIOScheduler] = None
    _initialized: bool = False

    # Constants
    SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
    CATEGORIES = ["Health", "Dental", "Group Life"]

    def __new__(cls) -> "SchedulerService":
        """Singleton pattern - return existing instance if available."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize scheduler with SQLite job store and Sao Paulo timezone."""
        # Only initialize once
        if SchedulerService._initialized:
            return

        settings = get_settings()

        # Configure SQLite job store for persistence
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=settings.database_url,
                tablename="apscheduler_jobs"
            )
        }

        # Job defaults from settings
        job_defaults = {
            "coalesce": settings.scheduler_coalesce,
            "max_instances": settings.scheduler_max_instances,
            "misfire_grace_time": settings.scheduler_misfire_grace_time,
        }

        # Create scheduler with Sao Paulo timezone
        SchedulerService._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone=self.SAO_PAULO_TZ,
        )

        # Add event listeners for logging
        SchedulerService._scheduler.add_listener(
            self._job_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

        SchedulerService._initialized = True
        logger.info("SchedulerService initialized with Sao Paulo timezone")

    @staticmethod
    def get_job_id(category: str) -> str:
        """
        Convert category name to job ID.

        Args:
            category: Category name (e.g., "Health", "Group Life")

        Returns:
            Job ID string (e.g., "category_run_health", "category_run_group_life")
        """
        slug = category.lower().replace(" ", "_")
        return f"category_run_{slug}"

    def _job_listener(self, event) -> None:
        """Log job execution events."""
        job_id = event.job_id

        if hasattr(event, "exception") and event.exception:
            logger.error(
                f"Scheduled job {job_id} failed with exception: {event.exception}"
            )
        elif hasattr(event, "retval"):
            logger.info(f"Scheduled job {job_id} executed successfully")
        else:
            # Missed job
            logger.warning(f"Scheduled job {job_id} was missed")

    async def start(self) -> None:
        """
        Start the scheduler and ensure default jobs are configured.

        Should be called during application startup.
        """
        settings = get_settings()

        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled in settings, not starting")
            return

        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

            # Ensure default jobs exist
            await self._ensure_default_jobs()

    def shutdown(self, wait: bool = False) -> None:
        """
        Gracefully shutdown the scheduler.

        Args:
            wait: If True, wait for running jobs to complete
        """
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown complete")

    async def _ensure_default_jobs(self) -> None:
        """Create default jobs for all categories if they don't exist."""
        settings = get_settings()

        for category in self.CATEGORIES:
            job_id = self.get_job_id(category)
            existing_job = self._scheduler.get_job(job_id)

            if existing_job:
                logger.debug(f"Job {job_id} already exists, skipping creation")
                continue

            config = settings.get_schedule_config(category)

            if not config["enabled"]:
                logger.info(f"Schedule for {category} is disabled, skipping job creation")
                continue

            # Parse cron expression and create trigger
            try:
                trigger = CronTrigger.from_crontab(
                    config["cron"],
                    timezone=self.SAO_PAULO_TZ
                )

                # Add job with replace_existing for safety
                self._scheduler.add_job(
                    self._execute_category_run,
                    trigger=trigger,
                    id=job_id,
                    name=f"Scheduled run for {category}",
                    args=[category],
                    replace_existing=True,
                )

                logger.info(
                    f"Created scheduled job for {category} with cron '{config['cron']}'"
                )
            except Exception as e:
                logger.error(f"Failed to create job for {category}: {e}")

    async def _execute_category_run(self, category: str) -> None:
        """
        Trigger category run via internal HTTP call.

        Args:
            category: Category to run (Health, Dental, or Group Life)
        """
        logger.info(f"Scheduled run starting for category: {category}")

        settings = get_settings()
        base_url = f"http://localhost:{settings.port}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/api/runs/execute/category",
                    json={
                        "category": category,
                        "send_email": True,
                        "enabled_only": True
                    },
                    timeout=1800.0  # 30 minute timeout
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    f"Scheduled run completed for {category}: "
                    f"run_id={result.get('run_id')}"
                )
        except httpx.TimeoutException:
            logger.error(f"Scheduled run timed out for {category} after 30 minutes")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Scheduled run HTTP error for {category}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Scheduled run failed for {category}: {e}")
            raise

    def get_schedule(self, category: str) -> Optional[dict]:
        """
        Get schedule information for a category.

        Args:
            category: Category name

        Returns:
            Dictionary with job info, or None if job doesn't exist
        """
        if not self._scheduler:
            return None

        job_id = self.get_job_id(category)
        job = self._scheduler.get_job(job_id)

        if not job:
            return None

        return {
            "job_id": job.id,
            "name": job.name,
            "category": category,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "paused": job.next_run_time is None,
            "trigger": str(job.trigger),
        }

    def get_all_schedules(self) -> list[dict]:
        """
        Get schedule information for all categories.

        Returns:
            List of schedule dictionaries for each category
        """
        schedules = []
        for category in self.CATEGORIES:
            schedule = self.get_schedule(category)
            if schedule:
                schedules.append(schedule)
            else:
                # Return info about missing job
                schedules.append({
                    "job_id": self.get_job_id(category),
                    "name": f"Scheduled run for {category}",
                    "category": category,
                    "next_run_time": None,
                    "paused": True,
                    "trigger": None,
                    "exists": False,
                })
        return schedules

    def update_schedule(
        self,
        category: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        cron_expression: Optional[str] = None,
    ) -> dict:
        """
        Update the schedule for a category.

        Args:
            category: Category name
            hour: New hour (0-23), used with minute
            minute: New minute (0-59), used with hour
            cron_expression: Full cron expression (overrides hour/minute)

        Returns:
            Updated schedule information

        Raises:
            ValueError: If job doesn't exist or invalid parameters
        """
        if not self._scheduler:
            raise ValueError("Scheduler not initialized")

        job_id = self.get_job_id(category)
        job = self._scheduler.get_job(job_id)

        if not job:
            raise ValueError(f"No job exists for category: {category}")

        # Build new trigger
        if cron_expression:
            trigger = CronTrigger.from_crontab(
                cron_expression,
                timezone=self.SAO_PAULO_TZ
            )
        elif hour is not None and minute is not None:
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.SAO_PAULO_TZ
            )
        else:
            raise ValueError("Must provide either cron_expression or both hour and minute")

        # Reschedule job
        self._scheduler.reschedule_job(job_id, trigger=trigger)
        logger.info(f"Rescheduled job {job_id} with new trigger: {trigger}")

        return self.get_schedule(category)

    def pause_job(self, category: str) -> dict:
        """
        Pause the scheduled job for a category.

        Args:
            category: Category name

        Returns:
            Updated schedule information

        Raises:
            ValueError: If job doesn't exist
        """
        if not self._scheduler:
            raise ValueError("Scheduler not initialized")

        job_id = self.get_job_id(category)
        job = self._scheduler.get_job(job_id)

        if not job:
            raise ValueError(f"No job exists for category: {category}")

        self._scheduler.pause_job(job_id)
        logger.info(f"Paused job {job_id}")

        return self.get_schedule(category)

    def resume_job(self, category: str) -> dict:
        """
        Resume a paused job for a category.

        Args:
            category: Category name

        Returns:
            Updated schedule information

        Raises:
            ValueError: If job doesn't exist
        """
        if not self._scheduler:
            raise ValueError("Scheduler not initialized")

        job_id = self.get_job_id(category)
        job = self._scheduler.get_job(job_id)

        if not job:
            raise ValueError(f"No job exists for category: {category}")

        self._scheduler.resume_job(job_id)
        logger.info(f"Resumed job {job_id}")

        return self.get_schedule(category)

    async def trigger_now(self, category: str) -> None:
        """
        Trigger immediate execution for a category.

        Args:
            category: Category name

        Note: This runs the job immediately outside of the normal schedule.
        """
        logger.info(f"Manually triggering immediate run for {category}")
        await self._execute_category_run(category)

    @property
    def is_running(self) -> bool:
        """Check if scheduler is currently running."""
        return self._scheduler is not None and self._scheduler.running

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance.

        Primarily for testing purposes to allow fresh initialization.
        """
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown(wait=False)
        cls._instance = None
        cls._scheduler = None
        cls._initialized = False
