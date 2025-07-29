"""
FastAPI main application for RiskRadar admin interface.
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging
from pathlib import Path

from ..core.database import get_db, init_database, check_database_health
from .routers import sources, threats, dashboard, scraping, system, topic_analysis
from ..core.models import DataSourceORM, IncidentORM

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RiskRadar Admin Interface",
    description="Early warning system for emerging threats",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Setup templates and static files
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Create directories if they don't exist
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API routers
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(threats.router, prefix="/api/threats", tags=["threats"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(scraping.router, tags=["scraping"])
app.include_router(system.router, tags=["system"])
app.include_router(topic_analysis.router, tags=["topic-analysis"])

@app.on_event("startup")
async def startup_event():
    """Initialize database and perform startup checks."""
    logger.info("Starting RiskRadar application...")
    
    try:
        # Initialize database
        init_database()
        
        # Check database health
        if not check_database_health():
            logger.error("Database health check failed!")
            raise Exception("Database not accessible")
        
        logger.info("RiskRadar startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down RiskRadar...")

# Web Interface Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page."""
    try:
        # Get dashboard statistics
        total_sources = db.query(DataSourceORM).count()
        active_sources = db.query(DataSourceORM).filter(DataSourceORM.enabled == True).count()
        total_incidents = db.query(IncidentORM).count()
        confirmed_threats = db.query(IncidentORM).filter(IncidentORM.status == "confirmed").count()
        
        stats = {
            "total_sources": total_sources,
            "active_sources": active_sources,
            "total_incidents": total_incidents,
            "confirmed_threats": confirmed_threats,
            "threat_rate": round((confirmed_threats / max(1, total_incidents)) * 100, 1)
        }
        
        return templates.TemplateResponse(
            "dashboard.html", 
            {"request": request, "stats": stats}
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "error": str(e)}
        )

@app.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request):
    """Source configuration page."""
    return templates.TemplateResponse("sources.html", {"request": request})

@app.get("/threats", response_class=HTMLResponse)
async def threats_page(request: Request):
    """Threat exploration page."""
    return templates.TemplateResponse("threats.html", {"request": request})

@app.get("/topic-analysis", response_class=HTMLResponse)
async def topic_analysis_page(request: Request):
    """Render the topic analysis page."""
    return templates.TemplateResponse("topic_analysis.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = check_database_health()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "version": "1.0.0"
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors."""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Page not found", "status_code": 404},
        status_code=404
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    """Handle 500 errors."""
    logger.error(f"Server error: {exc}")
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Internal server error", "status_code": 500},
        status_code=500
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
