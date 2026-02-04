"""
Pydantic schemas for NewsItem model.

Defines request/response schemas for news items and classification.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class InsurerStatus(str, Enum):
    """Classification status for news items (populated by Azure OpenAI)."""
    CRITICAL = "Critical"
    WATCH = "Watch"
    MONITOR = "Monitor"
    STABLE = "Stable"


class Sentiment(str, Enum):
    """Sentiment classification (populated by Azure OpenAI)."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class NewsItemBase(BaseModel):
    """Base schema with common news content fields."""
    title: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    published_at: Optional[datetime] = None


class NewsItemCreate(NewsItemBase):
    """Schema for creating a new news item."""
    run_id: int
    insurer_id: int


class NewsItemRead(NewsItemBase):
    """Schema for reading news item from database (without classification)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    insurer_id: int
    created_at: datetime


class NewsItemWithClassification(NewsItemRead):
    """Schema for news item with Azure OpenAI classification results."""
    status: Optional[InsurerStatus] = None
    sentiment: Optional[Sentiment] = None
    summary: Optional[str] = None
