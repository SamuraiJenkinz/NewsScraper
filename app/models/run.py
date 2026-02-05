"""
Run ORM model for BrasilIntel.

Tracks individual scraping and classification runs.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Run(Base):
    """
    ORM model for scraping/classification runs.

    Tracks execution history with status, timing, and item counts.
    Each run represents a single execution of the news scraping pipeline
    for a specific category (Health, Dental, or Group Life).
    """
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)  # Health, Dental, Group Life
    trigger_type = Column(String(20), nullable=False)  # scheduled, manual
    status = Column(String(20), default="pending")  # pending, running, completed, failed

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    insurers_processed = Column(Integer, default=0)
    items_found = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Email delivery tracking (Phase 6)
    email_status = Column(String(20), nullable=True)  # pending, sent, failed, skipped
    email_sent_at = Column(DateTime, nullable=True)
    email_recipients_count = Column(Integer, default=0)
    email_error_message = Column(Text, nullable=True)

    # PDF tracking
    pdf_generated = Column(Boolean, default=False)
    pdf_size_bytes = Column(Integer, nullable=True)

    # Critical alert tracking
    critical_alert_sent = Column(Boolean, default=False)
    critical_alert_sent_at = Column(DateTime, nullable=True)
    critical_insurers_count = Column(Integer, default=0)

    # Scheduled job tracking (Phase 7)
    scheduled_job_id = Column(String(100), nullable=True)  # APScheduler job ID that triggered this run
    scheduled_time = Column(DateTime, nullable=True)  # Originally scheduled time
    actual_start_delay_seconds = Column(Integer, nullable=True)  # Delay from scheduled to actual start

    # Relationships
    news_items = relationship("NewsItem", back_populates="run")

    def __repr__(self) -> str:
        email_info = f", email='{self.email_status}'" if self.email_status else ""
        sched_info = f", job='{self.scheduled_job_id}'" if self.scheduled_job_id else ""
        return f"<Run(id={self.id}, category='{self.category}', status='{self.status}'{email_info}{sched_info})>"
