"""
API router for dashboard endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import Dict, Any
from datetime import datetime, timedelta
import logging

from ...core.database import get_db
from ...core.models import IncidentORM, DataSourceORM

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """Get dashboard overview statistics."""
    try:
        # Source statistics
        total_sources = db.query(DataSourceORM).count()
        active_sources = db.query(DataSourceORM).filter(DataSourceORM.enabled == True).count()
        
        # Incident statistics (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        total_incidents = db.query(IncidentORM).filter(
            IncidentORM.created_at >= cutoff_date
        ).count()
        
        confirmed_threats = db.query(IncidentORM).filter(
            and_(
                IncidentORM.created_at >= cutoff_date,
                IncidentORM.status == "confirmed"
            )
        ).count()
        
        pending_threats = db.query(IncidentORM).filter(
            and_(
                IncidentORM.created_at >= cutoff_date,
                IncidentORM.status == "pending"
            )
        ).count()
        
        high_risk_threats = db.query(IncidentORM).filter(
            and_(
                IncidentORM.created_at >= cutoff_date,
                IncidentORM.risk_score >= 7.0
            )
        ).count()
        
        # Recent activity
        recent_threats = db.query(IncidentORM).filter(
            IncidentORM.created_at >= cutoff_date
        ).order_by(desc(IncidentORM.created_at)).limit(5).all()
        
        # Calculate threat rate
        threat_rate = round((confirmed_threats / max(1, total_incidents)) * 100, 1)
        
        return {
            "sources": {
                "total": total_sources,
                "active": active_sources,
                "inactive": total_sources - active_sources,
                "health_percentage": round((active_sources / max(1, total_sources)) * 100, 1)
            },
            "threats": {
                "total_incidents": total_incidents,
                "confirmed_threats": confirmed_threats,
                "pending_threats": pending_threats,
                "high_risk_threats": high_risk_threats,
                "threat_rate": threat_rate
            },
            "recent_activity": [
                {
                    "id": threat.id,
                    "title": threat.title[:80] + "..." if len(threat.title) > 80 else threat.title,
                    "severity": threat.severity,
                    "risk_score": threat.risk_score,
                    "status": threat.status,
                    "created_at": threat.created_at.isoformat()
                }
                for threat in recent_threats
            ],
            "period": "Last 30 days",
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_dashboard_alerts(db: Session = Depends(get_db)):
    """Get current system alerts and notifications."""
    try:
        alerts = []
        
        # Check for inactive sources
        inactive_sources = db.query(DataSourceORM).filter(DataSourceORM.enabled == False).count()
        if inactive_sources > 0:
            alerts.append({
                "type": "warning",
                "title": "Inactive Sources",
                "message": f"{inactive_sources} sources are currently disabled",
                "action": "Review source configuration",
                "link": "/sources"
            })
        
        # Check for high-risk threats in last 24 hours
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        high_risk_recent = db.query(IncidentORM).filter(
            and_(
                IncidentORM.created_at >= cutoff_24h,
                IncidentORM.risk_score >= 8.0,
                IncidentORM.status == "pending"
            )
        ).count()
        
        if high_risk_recent > 0:
            alerts.append({
                "type": "critical",
                "title": "High-Risk Threats Detected",
                "message": f"{high_risk_recent} high-risk threats require attention",
                "action": "Review pending threats",
                "link": "/threats?status=pending&severity=high"
            })
        
        # Check for system health
        total_sources = db.query(DataSourceORM).count()
        if total_sources == 0:
            alerts.append({
                "type": "error",
                "title": "No Sources Configured",
                "message": "No monitoring sources are configured",
                "action": "Configure sources",
                "link": "/sources"
            })
        
        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "last_checked": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_dashboard_metrics(
    days_back: int = 7,
    db: Session = Depends(get_db)
):
    """Get dashboard metrics for charts and graphs."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Daily incident counts
        incidents = db.query(IncidentORM).filter(
            IncidentORM.created_at >= cutoff_date
        ).order_by(IncidentORM.created_at).all()
        
        # Group by date
        daily_metrics = {}
        for i in range(days_back):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            daily_metrics[date.isoformat()] = {
                "date": date.isoformat(),
                "incidents": 0,
                "confirmed": 0,
                "high_risk": 0,
                "avg_risk_score": 0
            }
        
        # Populate with actual data
        risk_scores_by_date = {}
        for incident in incidents:
            date_key = incident.created_at.date().isoformat()
            if date_key in daily_metrics:
                daily_metrics[date_key]["incidents"] += 1
                
                if incident.status == "confirmed":
                    daily_metrics[date_key]["confirmed"] += 1
                
                if incident.risk_score >= 7.0:
                    daily_metrics[date_key]["high_risk"] += 1
                
                if date_key not in risk_scores_by_date:
                    risk_scores_by_date[date_key] = []
                risk_scores_by_date[date_key].append(incident.risk_score)
        
        # Calculate average risk scores
        for date_key, scores in risk_scores_by_date.items():
            if scores:
                daily_metrics[date_key]["avg_risk_score"] = round(sum(scores) / len(scores), 2)
        
        # Severity distribution
        severity_counts = {}
        for incident in incidents:
            severity = incident.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Source type distribution
        source_type_counts = {}
        for incident in incidents:
            source_type = incident.incident_metadata.get("source_type", "unknown")
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        
        return {
            "period_days": days_back,
            "daily_metrics": list(daily_metrics.values()),
            "severity_distribution": severity_counts,
            "source_type_distribution": source_type_counts,
            "total_incidents": len(incidents),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
