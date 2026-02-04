"""
NewsItem ORM model for BrasilIntel.

Stores scraped news items with classification results.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class NewsItem(Base):
    """
    ORM model for news items found during scraping runs.

    Each NewsItem is associated with:
    - A Run (when it was discovered)
    - An Insurer (which company it's about)

    Classification fields (status, sentiment, summary) are populated
    by Azure OpenAI after initial scraping.
    """
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    insurer_id = Column(Integer, ForeignKey("insurers.id"), nullable=False)

    # News content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Classification results (populated by Azure OpenAI)
    status = Column(String(50), nullable=True)  # Critical, Watch, Monitor, Stable
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    summary = Column(Text, nullable=True)  # Bullet-point summary
    category_indicators = Column(String(500), nullable=True)  # Comma-separated list

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    insurer = relationship("Insurer", back_populates="news_items")
    run = relationship("Run", back_populates="news_items")

    def __repr__(self) -> str:
        return f"<NewsItem(id={self.id}, insurer_id={self.insurer_id}, title='{self.title[:50]}...')>"
