"""
API router for threat management and exploration endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ...core.database import get_db
from ...core.models import IncidentORM, Incident, SeverityLevel, IncidentStatus

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Incident])
async def get_threats(
    status: Optional[str] = Query(None, description="Filter by status (confirmed, pending, dismissed)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    keyword: Optional[str] = Query(None, description="Search by keyword"),
    days_back: int = Query(30, description="Number of days to look back"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    sort_by: str = Query("created_at", description="Sort field (created_at, risk_score, severity)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    db: Session = Depends(get_db)
):
    """Get threats with filtering and pagination."""
    try:
        query = db.query(IncidentORM)
        
        # Date filter
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        query = query.filter(IncidentORM.created_at >= cutoff_date)
        
        # Status filter
        if status:
            query = query.filter(IncidentORM.status == status)
        
        # Severity filter
        if severity:
            query = query.filter(IncidentORM.severity == severity)
        
        # Source type filter
        if source_type:
            query = query.filter(IncidentORM.incident_metadata.contains({"source_type": source_type}))
        
        # Keyword search
        if keyword:
            keyword_filter = or_(
                IncidentORM.title.ilike(f"%{keyword}%"),
                IncidentORM.description.ilike(f"%{keyword}%"),
                IncidentORM.keywords.contains([keyword])
            )
            query = query.filter(keyword_filter)
        
        # Sorting
        sort_field = getattr(IncidentORM, sort_by, IncidentORM.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(asc(sort_field))
        
        # Pagination
        query = query.offset(offset).limit(limit)
        
        incidents = query.all()
        
        return [Incident.from_orm(incident) for incident in incidents]
        
    except Exception as e:
        logger.error(f"Error fetching threats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{threat_id}", response_model=Incident)
async def get_threat(threat_id: int, db: Session = Depends(get_db)):
    """Get a specific threat by ID."""
    try:
        incident = db.query(IncidentORM).filter(IncidentORM.id == threat_id).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Threat not found")
        
        return Incident.from_orm(incident)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching threat {threat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{threat_id}/status")
async def update_threat_status(
    threat_id: int,
    new_status: str,
    db: Session = Depends(get_db)
):
    """Update threat status (confirmed, dismissed, pending)."""
    try:
        incident = db.query(IncidentORM).filter(IncidentORM.id == threat_id).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Threat not found")
        
        # Validate status
        valid_statuses = ["confirmed", "dismissed", "pending", "investigating"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        old_status = incident.status
        incident.status = new_status
        incident.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Threat {threat_id} status changed from {old_status} to {new_status}")
        
        return {
            "id": threat_id,
            "old_status": old_status,
            "new_status": new_status,
            "message": f"Threat status updated to {new_status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating threat status {threat_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/summary")
async def get_threat_stats(
    days_back: int = Query(30, description="Number of days for statistics"),
    db: Session = Depends(get_db)
):
    """Get threat statistics summary."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Total counts
        total_threats = db.query(IncidentORM).filter(
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
        
        dismissed_threats = db.query(IncidentORM).filter(
            and_(
                IncidentORM.created_at >= cutoff_date,
                IncidentORM.status == "dismissed"
            )
        ).count()
        
        # Severity breakdown
        severity_counts = {}
        for severity in SeverityLevel:
            count = db.query(IncidentORM).filter(
                and_(
                    IncidentORM.created_at >= cutoff_date,
                    IncidentORM.severity == severity.value
                )
            ).count()
            severity_counts[severity.value] = count
        
        # Risk score statistics
        risk_stats = db.query(IncidentORM).filter(
            IncidentORM.created_at >= cutoff_date
        ).all()
        
        if risk_stats:
            risk_scores = [incident.risk_score for incident in risk_stats]
            avg_risk_score = sum(risk_scores) / len(risk_scores)
            max_risk_score = max(risk_scores)
            min_risk_score = min(risk_scores)
        else:
            avg_risk_score = max_risk_score = min_risk_score = 0
        
        # Recent high-risk threats
        high_risk_threats = db.query(IncidentORM).filter(
            and_(
                IncidentORM.created_at >= cutoff_date,
                IncidentORM.risk_score >= 7.0
            )
        ).order_by(desc(IncidentORM.risk_score)).limit(5).all()
        
        return {
            "period_days": days_back,
            "total_threats": total_threats,
            "confirmed_threats": confirmed_threats,
            "pending_threats": pending_threats,
            "dismissed_threats": dismissed_threats,
            "confirmation_rate": round((confirmed_threats / max(1, total_threats)) * 100, 1),
            "severity_breakdown": severity_counts,
            "risk_score_stats": {
                "average": round(avg_risk_score, 2),
                "maximum": round(max_risk_score, 2),
                "minimum": round(min_risk_score, 2)
            },
            "high_risk_count": len(high_risk_threats),
            "recent_high_risk": [
                {
                    "id": threat.id,
                    "title": threat.title[:100] + "..." if len(threat.title) > 100 else threat.title,
                    "risk_score": threat.risk_score,
                    "severity": threat.severity,
                    "created_at": threat.created_at.isoformat()
                }
                for threat in high_risk_threats
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching threat stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/timeline")
async def get_threat_timeline(
    days_back: int = Query(7, description="Number of days for timeline"),
    db: Session = Depends(get_db)
):
    """Get threat timeline data for charts."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get incidents grouped by day
        incidents = db.query(IncidentORM).filter(
            IncidentORM.created_at >= cutoff_date
        ).order_by(IncidentORM.created_at).all()
        
        # Group by date
        timeline_data = {}
        for incident in incidents:
            date_key = incident.created_at.date().isoformat()
            
            if date_key not in timeline_data:
                timeline_data[date_key] = {
                    "date": date_key,
                    "total": 0,
                    "confirmed": 0,
                    "pending": 0,
                    "dismissed": 0,
                    "avg_risk_score": 0,
                    "risk_scores": []
                }
            
            timeline_data[date_key]["total"] += 1
            timeline_data[date_key][incident.status] += 1
            timeline_data[date_key]["risk_scores"].append(incident.risk_score)
        
        # Calculate average risk scores
        for date_data in timeline_data.values():
            if date_data["risk_scores"]:
                date_data["avg_risk_score"] = round(
                    sum(date_data["risk_scores"]) / len(date_data["risk_scores"]), 2
                )
            del date_data["risk_scores"]  # Remove raw scores from response
        
        return {
            "period_days": days_back,
            "timeline": list(timeline_data.values())
        }
        
    except Exception as e:
        logger.error(f"Error fetching threat timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-update")
async def bulk_update_threats(
    threat_ids: List[int],
    action: str,
    value: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Bulk update multiple threats."""
    try:
        threats = db.query(IncidentORM).filter(IncidentORM.id.in_(threat_ids)).all()
        
        if not threats:
            raise HTTPException(status_code=404, detail="No threats found")
        
        updated_count = 0
        
        if action == "status" and value:
            valid_statuses = ["confirmed", "dismissed", "pending", "investigating"]
            if value not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {valid_statuses}"
                )
            
            for threat in threats:
                threat.status = value
                threat.updated_at = datetime.utcnow()
                updated_count += 1
        
        else:
            raise HTTPException(status_code=400, detail="Invalid bulk action")
        
        db.commit()
        
        logger.info(f"Bulk updated {updated_count} threats: {action}={value}")
        
        return {
            "updated_count": updated_count,
            "action": action,
            "value": value,
            "message": f"Successfully updated {updated_count} threats"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk updating threats: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
