"""
Core data models for RiskRadar incident response system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class SeverityLevel(str, Enum):
    """Risk severity levels for incidents."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):
    """Status of incident processing."""
    DETECTED = "detected"
    ANALYZING = "analyzing"
    TRIAGED = "triaged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SourceType(str, Enum):
    """Types of data sources."""
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    FORUM = "forum"
    GOVERNMENT = "government"
    BLOG = "blog"
    OTHER = "other"


class Incident(BaseModel):
    """Pydantic model for incident data."""
    model_config = {"from_attributes": True}
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., description="Incident title or headline")
    description: str = Field(..., description="Detailed description of the incident")
    keywords: List[str] = Field(default=[], description="Keywords that triggered detection")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM)
    status: IncidentStatus = Field(default=IncidentStatus.DETECTED)
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in incident validity")
    risk_score: float = Field(ge=0.0, le=10.0, description="Overall risk score")
    sentiment_score: float = Field(ge=-1.0, le=1.0, description="Sentiment analysis score")
    source_urls: List[str] = Field(default=[], description="URLs of source content")
    entities: Dict[str, List[str]] = Field(default={}, description="Extracted entities")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    incident_metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")

    @validator('risk_score')
    def validate_risk_score(cls, v):
        return max(0.0, min(10.0, v))

    @validator('sentiment_score')
    def validate_sentiment_score(cls, v):
        return max(-1.0, min(1.0, v))


class RiskAssessment(BaseModel):
    """Risk assessment for an incident."""
    incident_id: str
    business_impact: float = Field(ge=0.0, le=10.0, description="Potential business impact")
    urgency: float = Field(ge=0.0, le=10.0, description="Urgency of response needed")
    likelihood: float = Field(ge=0.0, le=1.0, description="Likelihood of impact")
    trend_direction: str = Field(description="escalating, stable, or declining")
    social_volume: int = Field(ge=0, description="Volume of social media mentions")
    news_coverage: int = Field(ge=0, description="Number of news articles")
    geographic_scope: List[str] = Field(default=[], description="Affected regions")
    industry_relevance: Dict[str, float] = Field(default={}, description="Relevance by industry")
    recommended_actions: List[str] = Field(default=[], description="Suggested response actions")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Alert(BaseModel):
    """Alert generated from incident analysis."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    alert_type: str = Field(description="Type of alert (email, slack, webhook, etc.)")
    severity: SeverityLevel
    title: str
    message: str
    recipients: List[str] = Field(default=[], description="Alert recipients")
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DataSource(BaseModel):
    """Configuration for data sources."""
    model_config = {"from_attributes": True}
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    source_type: SourceType
    url_pattern: str = Field(description="URL pattern or API endpoint")
    keywords: List[str] = Field(default=[], description="Keywords to monitor")
    scraping_config: Dict[str, Any] = Field(default={}, description="Scraping configuration")
    rate_limit: int = Field(default=60, description="Requests per minute")
    enabled: bool = Field(default=True)
    last_scraped: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# SQLAlchemy ORM Models
class IncidentORM(Base):
    """SQLAlchemy model for incidents."""
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    keywords = Column(JSON, default=[])
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    source_urls = Column(JSON, default=[])
    entities = Column(JSON, default={})
    incident_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiskAssessmentORM(Base):
    """SQLAlchemy model for risk assessments."""
    __tablename__ = "risk_assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False)
    business_impact = Column(Float, nullable=False)
    urgency = Column(Float, nullable=False)
    likelihood = Column(Float, nullable=False)
    trend_direction = Column(String, nullable=False)
    social_volume = Column(Integer, default=0)
    news_coverage = Column(Integer, default=0)
    geographic_scope = Column(JSON, default=[])
    industry_relevance = Column(JSON, default={})
    recommended_actions = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertORM(Base):
    """SQLAlchemy model for alerts."""
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    recipients = Column(JSON, default=[])
    sent_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class DataSourceORM(Base):
    """SQLAlchemy model for data sources."""
    __tablename__ = "data_sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    url_pattern = Column(String, nullable=False)
    keywords = Column(JSON, default=[])
    scraping_config = Column(JSON, default={})
    rate_limit = Column(Integer, default=60)
    enabled = Column(Boolean, default=True)
    last_scraped = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
