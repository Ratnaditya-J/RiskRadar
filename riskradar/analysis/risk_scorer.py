"""
Risk scoring module for threat evaluation.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class RiskScorer:
    """Calculates risk scores for incidents based on multiple factors."""
    
    def __init__(self):
        """Initialize the risk scorer."""
        self.scoring_weights = {
            'severity': 0.35,
            'confidence': 0.25,
            'sentiment': 0.20,
            'source_reliability': 0.20
        }
        
        self.severity_scores = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.5,
            'low': 0.2,
            'info': 0.1
        }
        
        self.source_scores = {
            'government': 0.9,
            'news': 0.7,
            'social_media': 0.4,
            'forum': 0.3,
            'blog': 0.5,
            'unknown': 0.3
        }
        
        logger.info("RiskScorer initialized")
    
    def calculate_risk_score(self, 
                           severity: str,
                           confidence_score: float,
                           sentiment_score: float,
                           source_type: str = 'unknown') -> float:
        """
        Calculate overall risk score based on multiple factors.
        
        Args:
            severity: Severity level string
            confidence_score: Confidence score (0.0 to 1.0)
            sentiment_score: Sentiment score (-1.0 to 1.0)
            source_type: Type of source
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        # Severity component
        severity_component = self.severity_scores.get(severity.lower(), 0.5)
        
        # Confidence component (higher confidence = higher risk if threat is confirmed)
        confidence_component = confidence_score
        
        # Sentiment component (more negative sentiment = higher risk)
        # Convert sentiment from [-1, 1] to [0, 1] where negative is higher risk
        sentiment_component = max(0.0, (1.0 - sentiment_score) / 2.0)
        
        # Source reliability component
        source_component = self.source_scores.get(source_type.lower(), 0.3)
        
        # Calculate weighted score
        risk_score = (
            severity_component * self.scoring_weights['severity'] +
            confidence_component * self.scoring_weights['confidence'] +
            sentiment_component * self.scoring_weights['sentiment'] +
            source_component * self.scoring_weights['source_reliability']
        )
        
        return min(1.0, max(0.0, risk_score))
    
    def get_risk_level(self, risk_score: float) -> str:
        """
        Convert risk score to human-readable risk level.
        
        Args:
            risk_score: Risk score between 0.0 and 1.0
            
        Returns:
            Risk level string
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
    
    def score_batch(self, incidents_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score a batch of incidents.
        
        Args:
            incidents_data: List of incident data dictionaries
            
        Returns:
            List of scoring results
        """
        results = []
        
        for incident_data in incidents_data:
            risk_score = self.calculate_risk_score(
                severity=incident_data.get('severity', 'medium'),
                confidence_score=incident_data.get('confidence_score', 0.5),
                sentiment_score=incident_data.get('sentiment_score', 0.0),
                source_type=incident_data.get('source_type', 'unknown')
            )
            
            risk_level = self.get_risk_level(risk_score)
            
            results.append({
                'incident_id': incident_data.get('id'),
                'risk_score': risk_score,
                'risk_level': risk_level,
                'components': {
                    'severity': incident_data.get('severity', 'medium'),
                    'confidence': incident_data.get('confidence_score', 0.5),
                    'sentiment': incident_data.get('sentiment_score', 0.0),
                    'source_type': incident_data.get('source_type', 'unknown')
                }
            })
        
        return results
    
    def update_weights(self, new_weights: Dict[str, float]) -> bool:
        """
        Update scoring weights.
        
        Args:
            new_weights: Dictionary of new weights
            
        Returns:
            True if weights were updated successfully
        """
        # Validate weights sum to 1.0
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, not 1.0")
            return False
        
        self.scoring_weights.update(new_weights)
        logger.info(f"Updated scoring weights: {self.scoring_weights}")
        return True
