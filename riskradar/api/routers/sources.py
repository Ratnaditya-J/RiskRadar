"""
API router for source management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from ...core.database import get_db
from ...core.models import DataSourceORM, DataSource, SourceType
from ...config.default_sources import get_source_categories as get_default_source_categories

router = APIRouter()
logger = logging.getLogger(__name__)

class CreateSourceRequest(BaseModel):
    """Request model for creating a new source."""
    name: str = Field(..., min_length=1, max_length=100, description="Source name")
    source_type: str = Field(..., description="Source type (news, blog, social_media, government, forum)")
    url_pattern: str = Field(..., min_length=1, description="URL pattern for scraping")
    keywords: Optional[List[str]] = Field(default=[], description="Keywords to filter content")
    rate_limit: Optional[int] = Field(default=60, ge=1, le=3600, description="Rate limit in seconds")
    reliability_score: Optional[float] = Field(default=0.8, ge=0.0, le=1.0, description="Reliability score")
    enabled: Optional[bool] = Field(default=True, description="Whether source is enabled")

@router.get("/", response_model=List[DataSource])
async def get_sources(
    enabled_only: bool = Query(False, description="Return only enabled sources"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    db: Session = Depends(get_db)
):
    """Get all configured sources."""
    try:
        query = db.query(DataSourceORM)
        
        if enabled_only:
            query = query.filter(DataSourceORM.enabled == True)
        
        if source_type:
            query = query.filter(DataSourceORM.source_type == source_type)
        
        sources = query.all()
        
        return [DataSource.from_orm(source) for source in sources]
        
    except Exception as e:
        logger.error(f"Error fetching sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories")
async def get_source_categories():
    """Get source categories for UI organization."""
    try:
        return get_default_source_categories()
    except Exception as e:
        logger.error(f"Error fetching source categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_source_types():
    """Get available source types for UI dropdown."""
    try:
        return {
            "types": [
                {
                    "value": st.value,
                    "label": st.value.replace('_', ' ').title(),
                    "description": {
                        "news": "News websites and publications",
                        "blog": "Security blogs and expert commentary",
                        "social_media": "Social media platforms (Twitter, Reddit, etc.)",
                        "government": "Government security advisories and alerts",
                        "forum": "Security forums and discussion boards"
                    }.get(st.value, "Custom source type")
                }
                for st in SourceType
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching source types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/summary")
async def get_source_stats(db: Session = Depends(get_db)):
    """Get source statistics summary."""
    try:
        total_sources = db.query(DataSourceORM).count()
        enabled_sources = db.query(DataSourceORM).filter(DataSourceORM.enabled == True).count()
        
        # Count by source type
        type_counts = {}
        for source_type in SourceType:
            count = db.query(DataSourceORM).filter(
                DataSourceORM.source_type == source_type.value
            ).count()
            type_counts[source_type.value] = count
        
        return {
            "total_sources": total_sources,
            "enabled_sources": enabled_sources,
            "disabled_sources": total_sources - enabled_sources,
            "by_type": type_counts,
            "enabled_percentage": round((enabled_sources / max(1, total_sources)) * 100, 1)
        }
        
    except Exception as e:
        logger.error(f"Error fetching source stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{source_id}", response_model=DataSource)
async def get_source(source_id: int, db: Session = Depends(get_db)):
    """Get a specific source by ID."""
    try:
        source = db.query(DataSourceORM).filter(DataSourceORM.id == source_id).first()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        return DataSource.from_orm(source)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{source_id}/toggle")
async def toggle_source(source_id: int, db: Session = Depends(get_db)):
    """Toggle source enabled/disabled status."""
    try:
        source = db.query(DataSourceORM).filter(DataSourceORM.id == source_id).first()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.enabled = not source.enabled
        db.commit()
        
        logger.info(f"Source '{source.name}' {'enabled' if source.enabled else 'disabled'}")
        
        return {
            "id": source.id,
            "name": source.name,
            "enabled": source.enabled,
            "message": f"Source {'enabled' if source.enabled else 'disabled'} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling source {source_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{source_id}")
async def update_source(
    source_id: int, 
    source_update: dict,
    db: Session = Depends(get_db)
):
    """Update source configuration."""
    try:
        source = db.query(DataSourceORM).filter(DataSourceORM.id == source_id).first()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update allowed fields
        allowed_fields = ['name', 'url_pattern', 'keywords', 'rate_limit', 'enabled']
        
        for field, value in source_update.items():
            if field in allowed_fields and hasattr(source, field):
                setattr(source, field, value)
        
        db.commit()
        
        logger.info(f"Source '{source.name}' updated successfully")
        
        return DataSource.from_orm(source)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-toggle")
async def bulk_toggle_sources(
    source_ids: List[int],
    enabled: bool,
    db: Session = Depends(get_db)
):
    """Bulk enable/disable multiple sources."""
    try:
        sources = db.query(DataSourceORM).filter(DataSourceORM.id.in_(source_ids)).all()
        
        if not sources:
            raise HTTPException(status_code=404, detail="No sources found")
        
        updated_count = 0
        for source in sources:
            source.enabled = enabled
            updated_count += 1
        
        db.commit()
        
        action = "enabled" if enabled else "disabled"
        logger.info(f"Bulk {action} {updated_count} sources")
        
        return {
            "updated_count": updated_count,
            "action": action,
            "message": f"Successfully {action} {updated_count} sources"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk toggling sources: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=DataSource)
async def create_source(
    source_data: CreateSourceRequest,
    db: Session = Depends(get_db)
):
    """Create a new source."""
    try:
        # Validate source type
        valid_types = [st.value for st in SourceType]
        if source_data.source_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid source type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Check if source name already exists
        existing_source = db.query(DataSourceORM).filter(
            DataSourceORM.name == source_data.name
        ).first()
        
        if existing_source:
            raise HTTPException(
                status_code=400, 
                detail=f"Source with name '{source_data.name}' already exists"
            )
        
        # Create new source
        new_source = DataSourceORM(
            name=source_data.name,
            source_type=source_data.source_type,
            url_pattern=source_data.url_pattern,
            keywords=source_data.keywords or [],
            rate_limit=source_data.rate_limit,
            enabled=source_data.enabled
        )
        
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        logger.info(f"Created new source: {new_source.name} ({new_source.source_type})")
        
        return DataSource.from_orm(new_source)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating source: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
