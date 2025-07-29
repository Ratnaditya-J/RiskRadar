"""
API endpoints for web scraping operations.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ...scrapers.manager import ScrapingManager
from ...core.database import get_db
from ...core.models import DataSourceORM, SourceType
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scraping", tags=["scraping"])

# Global scraping manager instance
scraping_manager = ScrapingManager(max_workers=5)

@router.post("/start")
async def start_scraping(
    background_tasks: BackgroundTasks,
    source_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """
    Start scraping operation for enabled sources or specific source IDs.
    
    Args:
        source_ids: Optional list of specific source IDs to scrape
        db: Database session
    
    Returns:
        dict: Scraping operation status and details
    """
    try:
        # Get sources to scrape
        if source_ids:
            sources_query = db.query(DataSourceORM).filter(DataSourceORM.id.in_(source_ids))
        else:
            sources_query = db.query(DataSourceORM).filter(DataSourceORM.enabled == True)
        
        sources = sources_query.all()
        
        if not sources:
            raise HTTPException(
                status_code=404, 
                detail="No sources found to scrape"
            )
        
        # Convert to source configs
        source_configs = []
        for source in sources:
            config = {
                "id": source.id,
                "name": source.name,
                "source_type": source.source_type,
                "url_pattern": source.url_pattern,
                "keywords": source.keywords or [],
                "scraping_config": source.scraping_config or {},
                "enabled": source.enabled,
                "reliability_score": source.reliability_score
            }
            source_configs.append(config)
        
        # Start scraping in background
        def run_scraping():
            try:
                results = scraping_manager.start_scraping(source_configs)
                logger.info(f"Background scraping completed: {results}")
                
                # Store results in database
                # TODO: Implement threat storage after analysis
                
            except Exception as e:
                logger.error(f"Background scraping failed: {e}")
        
        background_tasks.add_task(run_scraping)
        
        return {
            "status": "started",
            "message": f"Scraping started for {len(source_configs)} sources",
            "sources": [s["name"] for s in source_configs],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_scraping():
    """
    Stop any ongoing scraping operations.
    
    Returns:
        dict: Stop operation status
    """
    try:
        result = scraping_manager.stop_scraping()
        
        return {
            "status": "stopped",
            "message": "Scraping operations stopped",
            "was_running": result.get("was_running", False),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_scraping_status():
    """
    Get current scraping operation status and statistics.
    
    Returns:
        dict: Current scraping status and stats
    """
    try:
        status = scraping_manager.get_scraping_status()
        
        return {
            "status": status["status"],
            "is_running": status["is_running"],
            "stats": status["stats"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get scraping status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/{source_id}")
async def test_single_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    """
    Test scraping a single source by ID.
    
    Args:
        source_id: ID of the source to test
        db: Database session
    
    Returns:
        dict: Test scraping results
    """
    try:
        # Get source from database
        source = db.query(DataSourceORM).filter(DataSourceORM.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Convert to source config
        source_config = {
            "id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "url_pattern": source.url_pattern,
            "keywords": source.keywords or [],
            "scraping_config": source.scraping_config or {},
            "enabled": source.enabled,
            "reliability_score": source.reliability_score
        }
        
        # Test scraping
        results = scraping_manager.scrape_single_source(source_config)
        
        return {
            "status": "success",
            "source": source.name,
            "items_scraped": len(results),
            "results": results[:5],  # Return first 5 items
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to test source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
async def validate_source_config(source_config: Dict[str, Any]):
    """
    Validate a source configuration for scraping.
    
    Args:
        source_config: Source configuration to validate
    
    Returns:
        dict: Validation results
    """
    try:
        validation = scraping_manager.validate_source_config(source_config)
        
        return {
            "is_valid": validation["is_valid"],
            "errors": validation["errors"],
            "warnings": validation.get("warnings", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to validate source config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/types")
async def get_source_types():
    """
    Get available source types for scraping.
    
    Returns:
        dict: Available source types and their descriptions
    """
    try:
        return {
            "source_types": {
                "news": {
                    "label": "News Sources",
                    "description": "News websites and publications",
                    "scraper_class": "NewsScraper"
                },
                "government": {
                    "label": "Government Sources",
                    "description": "Government security advisories and alerts",
                    "scraper_class": "GovernmentScraper"
                },
                "social_media": {
                    "label": "Social Media",
                    "description": "Social media platforms and forums",
                    "scraper_class": "SocialScraper"
                },
                "blog": {
                    "label": "Security Blogs",
                    "description": "Security research and analysis blogs",
                    "scraper_class": "BlogScraper"
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get source types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_scraping_statistics():
    """
    Get detailed scraping statistics and metrics.
    
    Returns:
        dict: Comprehensive scraping statistics
    """
    try:
        status = scraping_manager.get_scraping_status()
        stats = status["stats"]
        
        # Calculate additional metrics
        success_rate = 0
        if stats.get("total_scraped", 0) > 0:
            success_rate = (stats.get("successful_scrapes", 0) / stats["total_scraped"]) * 100
        
        return {
            "overview": {
                "total_sources_scraped": stats.get("total_scraped", 0),
                "successful_scrapes": stats.get("successful_scrapes", 0),
                "failed_scrapes": stats.get("failed_scrapes", 0),
                "success_rate_percent": round(success_rate, 2),
                "total_items_scraped": stats.get("total_items_scraped", 0)
            },
            "by_source_type": {
                "news": stats.get("news_scraped", 0),
                "government": stats.get("government_scraped", 0),
                "social_media": stats.get("social_media_scraped", 0),
                "blog": stats.get("blog_scraped", 0)
            },
            "current_status": {
                "is_running": status["is_running"],
                "status": status["status"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get scraping statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
