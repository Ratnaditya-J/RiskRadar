"""
API endpoints for system monitoring, health checks, and integration.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
import psutil
import platform

from ...core.database import get_db, check_database_health
from ...core.models import DataSourceORM, IncidentORM
from ...scrapers.manager import ScrapingManager
from ...analysis.sentiment import SentimentAnalyzer
from ...analysis.risk_assessor import RiskAssessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/health")
async def comprehensive_health_check(db: Session = Depends(get_db)):
    """
    Comprehensive system health check including all components.
    
    Returns:
        dict: Detailed health status of all system components
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Database health
        db_healthy = check_database_health()
        health_status["components"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection": "active" if db_healthy else "failed"
        }
        
        # Scraping engine health
        scraping_manager = ScrapingManager()
        scraping_status = scraping_manager.get_scraping_status()
        health_status["components"]["scraping_engine"] = {
            "status": "healthy",
            "is_running": scraping_status["is_running"],
            "total_scraped": scraping_status["stats"].get("total_scraped", 0)
        }
        
        # Analysis modules health
        try:
            sentiment_analyzer = SentimentAnalyzer()
            health_status["components"]["sentiment_analysis"] = {
                "status": "healthy",
                "module": "loaded"
            }
        except Exception as e:
            health_status["components"]["sentiment_analysis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        try:
            risk_assessor = RiskAssessor()
            health_status["components"]["risk_assessment"] = {
                "status": "healthy",
                "module": "loaded"
            }
        except Exception as e:
            health_status["components"]["risk_assessment"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # System resources
        health_status["components"]["system_resources"] = {
            "status": "healthy",
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        # Overall status
        unhealthy_components = [
            comp for comp, data in health_status["components"].items()
            if data["status"] != "healthy"
        ]
        
        if unhealthy_components:
            health_status["status"] = "degraded"
            health_status["unhealthy_components"] = unhealthy_components
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/metrics")
async def get_system_metrics(db: Session = Depends(get_db)):
    """
    Get comprehensive system metrics and statistics.
    
    Returns:
        dict: System performance and usage metrics
    """
    try:
        # Database metrics
        total_sources = db.query(DataSourceORM).count()
        enabled_sources = db.query(DataSourceORM).filter(DataSourceORM.enabled == True).count()
        total_incidents = db.query(IncidentORM).count()
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_incidents = db.query(IncidentORM).filter(
            IncidentORM.created_at >= yesterday
        ).count()
        
        # Threat status distribution
        confirmed_threats = db.query(IncidentORM).filter(
            IncidentORM.status == "confirmed"
        ).count()
        pending_threats = db.query(IncidentORM).filter(
            IncidentORM.status == "pending"
        ).count()
        dismissed_threats = db.query(IncidentORM).filter(
            IncidentORM.status == "dismissed"
        ).count()
        
        # Scraping metrics
        scraping_manager = ScrapingManager()
        scraping_stats = scraping_manager.get_scraping_status()["stats"]
        
        # System resource metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data_sources": {
                "total": total_sources,
                "enabled": enabled_sources,
                "disabled": total_sources - enabled_sources
            },
            "incidents": {
                "total": total_incidents,
                "recent_24h": recent_incidents,
                "confirmed": confirmed_threats,
                "pending": pending_threats,
                "dismissed": dismissed_threats
            },
            "scraping": {
                "total_scraped": scraping_stats.get("total_scraped", 0),
                "successful_scrapes": scraping_stats.get("successful_scrapes", 0),
                "failed_scrapes": scraping_stats.get("failed_scrapes", 0),
                "total_items": scraping_stats.get("total_items_scraped", 0)
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 2)
                },
                "platform": platform.system(),
                "python_version": platform.python_version()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info")
async def get_system_info():
    """
    Get basic system information and version details.
    
    Returns:
        dict: System information and version details
    """
    try:
        return {
            "application": {
                "name": "RiskRadar",
                "version": "1.0.0",
                "description": "Early warning system for emerging threats",
                "build_date": "2025-01-27"
            },
            "system": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": platform.node()
            },
            "features": {
                "web_scraping": True,
                "sentiment_analysis": True,
                "risk_assessment": True,
                "threat_triaging": True,
                "real_time_monitoring": True,
                "api_endpoints": True,
                "web_interface": True
            },
            "endpoints": {
                "api_docs": "/api/docs",
                "health_check": "/api/system/health",
                "metrics": "/api/system/metrics",
                "scraping": "/api/scraping/*",
                "threats": "/api/threats/*",
                "sources": "/api/sources/*"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-threat")
async def process_threat_pipeline(
    background_tasks: BackgroundTasks,
    content: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Process a single piece of content through the complete threat analysis pipeline.
    
    Args:
        content: Content to analyze (title, description, url, etc.)
        db: Database session
    
    Returns:
        dict: Analysis results and threat assessment
    """
    try:
        # Validate input
        if not content.get("title") or not content.get("description"):
            raise HTTPException(
                status_code=400,
                detail="Content must include title and description"
            )
        
        def analyze_content():
            """Background task to analyze content."""
            try:
                # Sentiment analysis
                sentiment_analyzer = SentimentAnalyzer()
                sentiment_result = sentiment_analyzer.analyze_text(
                    content.get("description", "")
                )
                
                # Risk assessment
                risk_assessor = RiskAssessor()
                risk_result = risk_assessor.assess_risk(content)
                
                # Store results if threat is confirmed
                if risk_result.get("is_threat", False):
                    # Create incident record
                    incident = IncidentORM(
                        title=content["title"],
                        description=content["description"],
                        url=content.get("url", ""),
                        source_name=content.get("source_name", "manual"),
                        risk_score=risk_result.get("risk_score", 0.5),
                        severity=risk_result.get("severity", "medium"),
                        status="pending",
                        keywords=content.get("keywords", []),
                        sentiment_score=sentiment_result.get("score", 0.0),
                        incident_metadata={
                            "sentiment": sentiment_result,
                            "risk_assessment": risk_result,
                            "processed_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    db.add(incident)
                    db.commit()
                    
                    logger.info(f"Threat processed and stored: {content['title']}")
                
            except Exception as e:
                logger.error(f"Failed to process threat: {e}")
        
        # Start background processing
        background_tasks.add_task(analyze_content)
        
        return {
            "status": "processing",
            "message": "Content submitted for threat analysis",
            "content_id": content.get("id", "unknown"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit content for processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def get_system_logs(
    lines: int = 100,
    level: str = "INFO"
):
    """
    Get recent system logs for monitoring and debugging.
    
    Args:
        lines: Number of log lines to return
        level: Log level filter (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        dict: Recent system logs
    """
    try:
        # This is a simplified implementation
        # In production, you'd read from actual log files
        
        return {
            "status": "success",
            "log_level": level,
            "lines_requested": lines,
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "System logs endpoint accessed",
                    "component": "system_api"
                }
            ],
            "note": "Log aggregation not fully implemented - this is a placeholder"
        }
        
    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
