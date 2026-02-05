# Phase 7 Plan 2: Schedule Schemas & Run Model Enhancement Summary

## One-liner
Pydantic schemas for schedule API (ScheduleInfo, ScheduleUpdate, ScheduleList) plus Run model enhanced with scheduled job tracking fields.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create schedule schemas | ea72b7e | app/schemas/schedule.py |
| 2 | Enhance Run model with scheduled tracking | 56f611e | app/models/run.py |
| 3 | Update RunRead schema with scheduled fields | c56e7b0 | app/schemas/run.py |

## Implementation Details

### Schedule Schemas (app/schemas/schedule.py)

Five Pydantic schemas define the schedule management API contract:

1. **ScheduleInfo** - Response model for schedule status
   - category, job_id, enabled, cron_expression
   - next_run_time, last_run_time, last_run_status

2. **ScheduleUpdate** - Request model for modifying schedules
   - hour (0-23), minute (0-59), cron_expression, enabled
   - Validators: ge=0, le=23 for hour; ge=0, le=59 for minute

3. **ScheduleList** - Response model for list of schedules
   - schedules: list[ScheduleInfo], timezone (default: America/Sao_Paulo)

4. **ManualTriggerResponse** - Response model for manual trigger requests
   - status, category, message

5. **ScheduleHealthResponse** - Response model for scheduler health check
   - scheduler_running, jobs_count, timezone, next_jobs

### Run Model Enhancements (app/models/run.py)

Three new nullable columns for scheduled job tracking:

- `scheduled_job_id` (String 100) - APScheduler job ID that triggered the run
- `scheduled_time` (DateTime) - Originally scheduled execution time
- `actual_start_delay_seconds` (Integer) - Delay from scheduled to actual start

Updated `__repr__` includes job ID when present for easier debugging.

### RunRead Schema Updates (app/schemas/run.py)

Added all missing fields to align with Run model:

**Phase 6 Delivery Tracking:**
- email_status, email_sent_at, email_recipients_count, email_error_message
- pdf_generated, pdf_size_bytes
- critical_alert_sent, critical_alert_sent_at, critical_insurers_count

**Phase 7 Scheduled Tracking:**
- scheduled_job_id, scheduled_time, actual_start_delay_seconds

## Key Patterns Applied

- Field descriptions for API documentation generation
- ConfigDict(from_attributes=True) for ORM compatibility
- Optional types with None defaults for nullable fields
- Validation constraints (ge/le) for hour/minute bounds

## Files Modified

| File | Lines | Purpose |
|------|-------|---------|
| app/schemas/schedule.py | 83 | New file - schedule API schemas |
| app/models/run.py | +7 | Scheduled tracking columns + __repr__ update |
| app/schemas/run.py | +16 | Delivery + scheduled tracking fields |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 07-03-PLAN (SchedulerService):
- Schedule schemas provide API contracts for scheduler endpoints
- Run model can track which scheduled job triggered each run
- RunRead schema returns complete run information including scheduled data
