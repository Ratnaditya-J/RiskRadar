"""
Risk assessment module for threat evaluation.
"""

from typing import Dict, Any, List
import logging
from ..core.models import Incident

logger = logging.getLogger(__name__)


class RiskAssessor:
    """Assesses risk levels of incidents and threats."""
    
    def __init__(self):
        """Initialize the risk assessor."""
        self.risk_factors = {
            'severity_weights': {
                'critical': 1.0,
                'high': 0.8,
                'medium': 0.5,
                'low': 0.2,
                'info': 0.1
            },
            'source_reliability': {
                'government': 0.9,
                'news': 0.7,
                'social_media': 0.4,
                'forum': 0.3,
                'blog': 0.5
            }
        }
        logger.info("RiskAssessor initialized")
    
    def assess_risk(self, incident: Incident) -> float:
        """
        Assess the overall risk score for an incident.
        
        Args:
            incident: Incident to assess
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        # Base risk from severity
        severity_weight = self.risk_factors['severity_weights'].get(
            incident.severity.lower(), 0.5
        )
        
        # Adjust based on confidence score
        confidence_factor = incident.confidence_score
        
        # Adjust based on sentiment (more negative = higher risk)
        sentiment_factor = max(0.0, -incident.sentiment_score + 0.5)
        
        # Source reliability factor
        source_type = incident.incident_metadata.get('source_type', 'unknown')
        source_reliability = self.risk_factors['source_reliability'].get(
            source_type, 0.5
        )
        
        # Calculate weighted risk score
        risk_score = (
            severity_weight * 0.4 +
            confidence_factor * 0.3 +
            sentiment_factor * 0.2 +
            source_reliability * 0.1
        )
        
        return min(1.0, max(0.0, risk_score))
    
    def categorize_risk(self, risk_score: float) -> str:
        """
        Categorize risk score into human-readable levels.
        
        Args:
            risk_score: Risk score between 0.0 and 1.0
            
        Returns:
            Risk category string
        """
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        elif risk_score >= 0.2:
            return "low"
        else:
            return "minimal"
    
    def assess_batch(self, incidents: List[Incident]) -> List[Dict[str, Any]]:
        """
        Assess risk for a batch of incidents.
        
        Args:
            incidents: List of incidents to assess
            
        Returns:
            List of risk assessment results
        """
        results = []
        for incident in incidents:
            risk_score = self.assess_risk(incident)
            risk_category = self.categorize_risk(risk_score)
            
            results.append({
                'incident_id': incident.id,
                'risk_score': risk_score,
                'risk_category': risk_category,
                'factors': {
                    'severity': incident.severity,
                    'confidence': incident.confidence_score,
                    'sentiment': incident.sentiment_score,
                    'source_type': incident.incident_metadata.get('source_type', 'unknown')
                }
            })
        
        return results
    
    def get_risk_summary(self, incidents: List[Incident]) -> Dict[str, Any]:
        """
        Get a summary of risk levels across all incidents.
        
        Args:
            incidents: List of incidents to summarize
            
        Returns:
            Risk summary statistics
        """
        if not incidents:
            return {
                'total_incidents': 0,
                'risk_distribution': {},
                'average_risk': 0.0,
                'highest_risk': 0.0
            }
        
        risk_scores = [self.assess_risk(incident) for incident in incidents]
        risk_categories = [self.categorize_risk(score) for score in risk_scores]
        
        # Count risk categories
        risk_distribution = {}
        for category in risk_categories:
            risk_distribution[category] = risk_distribution.get(category, 0) + 1
        
        return {
            'total_incidents': len(incidents),
            'risk_distribution': risk_distribution,
            'average_risk': sum(risk_scores) / len(risk_scores),
            'highest_risk': max(risk_scores)
        }
