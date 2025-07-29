"""
API router for source management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ...core.database import get_db
from ...core.models import DataSourceORM, DataSource, SourceType
from ...config.default_sources import get_source_categories

router = APIRouter()
logger = logging.getLogger(__name__)

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
        return get_source_categories()
    except Exception as e:
        logger.error(f"Error fetching source categories: {e}")
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
