"""
Pydantic models for Azure OpenAI structured output classification.

These models define the expected response format for the classification
service, ensuring consistent and validated JSON responses from the LLM.
"""
from pydantic import BaseModel, Field
from typing import Literal


class NewsClassification(BaseModel):
    """
    Classification result for a single news item.

    Used with Azure OpenAI structured outputs to guarantee
    schema conformance in the API response.
    """

    status: Literal["Critical", "Watch", "Monitor", "Stable"] = Field(
        description="Insurer status based on news content impact"
    )
    summary_bullets: list[str] = Field(
        description="3-5 bullet points summarizing the news impact in Portuguese",
        min_length=1,
        max_length=5,
    )
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the news"
    )
    reasoning: str = Field(
        description="Brief explanation (1-2 sentences) of why this status was assigned"
    )


class InsurerClassification(BaseModel):
    """
    Aggregated classification for an insurer based on all their news.

    Used when classifying multiple news items together to determine
    overall insurer status.
    """

    overall_status: Literal["Critical", "Watch", "Monitor", "Stable"] = Field(
        description="Overall insurer status based on all news items"
    )
    key_findings: list[str] = Field(
        description="Top 3-5 key findings across all news in Portuguese",
        min_length=1,
        max_length=5,
    )
    risk_factors: list[str] = Field(
        description="Identified risk factors (may be empty for Stable)",
        default_factory=list,
    )
    sentiment_breakdown: dict[str, int] = Field(
        description="Count of positive, negative, neutral items",
        default_factory=lambda: {"positive": 0, "negative": 0, "neutral": 0},
    )
    reasoning: str = Field(
        description="Explanation of overall status determination in Portuguese"
    )
