"""
Automated threat confirmation system for RiskRadar.
Determines if analyzed incidents should be confirmed as threats.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..core.models import Incident, RiskAssessment, SeverityLevel, IncidentStatus


@dataclass
class ConfirmationCriteria:
    """Criteria for automated threat confirmation."""
    min_risk_score: float = 6.0
    min_confidence_score: float = 0.7
    max_negative_sentiment: float = -0.3  # More negative = higher threat
    min_source_reliability: float = 0.8
    require_multiple_sources: bool = True
    min_keyword_matches: int = 2
    
    # Time-based criteria
    recent_incident_window_hours: int = 24
    escalation_factor: float = 1.2  # Boost score if similar recent incidents
    
    # Source type weights
    source_type_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.source_type_weights is None:
            self.source_type_weights = {
                "government": 1.0,
                "news": 0.9,
                "blog": 0.8,
                "social_media": 0.6,
                "forum": 0.5,
                "other": 0.4
            }


class ThreatConfirmer:
    """
    Automated system for confirming threats based on analysis results.
    
    Uses multiple criteria including risk scores, sentiment analysis,
    source reliability, and historical patterns to automatically
    determine if incidents should be confirmed as threats.
    """
    
    def __init__(self, criteria: Optional[ConfirmationCriteria] = None):
        self.criteria = criteria or ConfirmationCriteria()
        self.logger = logging.getLogger(__name__)
        
        # Track recent confirmations for pattern analysis
        self.recent_confirmations: List[Incident] = []
    
    async def evaluate_incident(
        self, 
        incident: Incident, 
        risk_assessment: Optional[RiskAssessment] = None,
        historical_incidents: Optional[List[Incident]] = None
    ) -> Tuple[bool, float, str]:
        """
        Evaluate if an incident should be confirmed as a threat.
        
        Returns:
            Tuple of (should_confirm, confidence_score, reason)
        """
        try:
            # Calculate confirmation score
            confirmation_score, factors = await self._calculate_confirmation_score(
                incident, risk_assessment, historical_incidents
            )
            
            # Determine if should confirm
            should_confirm = confirmation_score >= self.criteria.min_risk_score
            
            # Generate explanation
            reason = self._generate_confirmation_reason(
                incident, confirmation_score, factors, should_confirm
            )
            
            self.logger.info(
                f"Threat evaluation for '{incident.title[:50]}...': "
                f"Score={confirmation_score:.2f}, Confirm={should_confirm}"
            )
            
            return should_confirm, confirmation_score, reason
            
        except Exception as e:
            self.logger.error(f"Error evaluating incident {incident.id}: {e}")
            return False, 0.0, f"Evaluation error: {str(e)}"
    
    async def _calculate_confirmation_score(
        self,
        incident: Incident,
        risk_assessment: Optional[RiskAssessment],
        historical_incidents: Optional[List[Incident]]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate the overall confirmation score and contributing factors."""
        
        factors = {}
        base_score = incident.risk_score
        factors["base_risk_score"] = base_score
        
        # 1. Confidence score factor
        confidence_factor = self._evaluate_confidence(incident)
        factors["confidence_factor"] = confidence_factor
        
        # 2. Sentiment factor
        sentiment_factor = self._evaluate_sentiment(incident)
        factors["sentiment_factor"] = sentiment_factor
        
        # 3. Source reliability factor
        source_factor = self._evaluate_source_reliability(incident)
        factors["source_factor"] = source_factor
        
        # 4. Keyword relevance factor
        keyword_factor = self._evaluate_keyword_relevance(incident)
        factors["keyword_factor"] = keyword_factor
        
        # 5. Historical pattern factor
        pattern_factor = self._evaluate_historical_patterns(incident, historical_incidents)
        factors["pattern_factor"] = pattern_factor
        
        # 6. Risk assessment factor (if available)
        assessment_factor = self._evaluate_risk_assessment(risk_assessment)
        factors["assessment_factor"] = assessment_factor
        
        # Calculate weighted final score
        final_score = (
            base_score * 0.3 +
            confidence_factor * 0.15 +
            sentiment_factor * 0.15 +
            source_factor * 0.15 +
            keyword_factor * 0.10 +
            pattern_factor * 0.10 +
            assessment_factor * 0.05
        )
        
        factors["final_score"] = final_score
        
        return final_score, factors
    
    def _evaluate_confidence(self, incident: Incident) -> float:
        """Evaluate confidence score contribution."""
        if incident.confidence_score >= self.criteria.min_confidence_score:
            return incident.confidence_score * 10  # Scale to 0-10
        else:
            return incident.confidence_score * 5  # Penalty for low confidence
    
    def _evaluate_sentiment(self, incident: Incident) -> float:
        """Evaluate sentiment contribution to threat score."""
        sentiment = incident.sentiment_score
        
        # More negative sentiment = higher threat score
        if sentiment <= self.criteria.max_negative_sentiment:
            # Very negative sentiment boosts threat score
            return abs(sentiment) * 8
        elif sentiment < 0:
            # Somewhat negative sentiment
            return abs(sentiment) * 5
        elif sentiment < 0.3:
            # Neutral sentiment
            return 3.0
        else:
            # Positive sentiment reduces threat score
            return max(1.0, 3.0 - sentiment * 2)
    
    def _evaluate_source_reliability(self, incident: Incident) -> float:
        """Evaluate source reliability contribution."""
        # Extract source type from metadata
        source_type = incident.incident_metadata.get("source_type", "other")
        weight = self.criteria.source_type_weights.get(source_type, 0.5)
        
        # Base score from source type
        reliability_score = weight * 10
        
        # Boost for multiple sources
        if len(incident.source_urls) > 1:
            reliability_score *= 1.2
        
        return min(10.0, reliability_score)
    
    def _evaluate_keyword_relevance(self, incident: Incident) -> float:
        """Evaluate keyword match relevance."""
        keyword_count = len(incident.keywords)
        
        if keyword_count >= self.criteria.min_keyword_matches:
            # Good keyword coverage
            return min(10.0, keyword_count * 2)
        else:
            # Insufficient keyword matches
            return keyword_count * 1.5
    
    def _evaluate_historical_patterns(
        self, 
        incident: Incident, 
        historical_incidents: Optional[List[Incident]]
    ) -> float:
        """Evaluate based on historical incident patterns."""
        if not historical_incidents:
            return 5.0  # Neutral score
        
        # Look for similar incidents in recent history
        cutoff_time = datetime.utcnow() - timedelta(
            hours=self.criteria.recent_incident_window_hours
        )
        
        recent_similar = []
        for hist_incident in historical_incidents:
            if hist_incident.created_at >= cutoff_time:
                # Check for keyword overlap
                keyword_overlap = len(
                    set(incident.keywords) & set(hist_incident.keywords)
                )
                if keyword_overlap >= 1:
                    recent_similar.append(hist_incident)
        
        if recent_similar:
            # Escalating pattern detected
            avg_risk = sum(inc.risk_score for inc in recent_similar) / len(recent_similar)
            return min(10.0, avg_risk * self.criteria.escalation_factor)
        else:
            return 5.0  # No pattern detected
    
    def _evaluate_risk_assessment(
        self, 
        risk_assessment: Optional[RiskAssessment]
    ) -> float:
        """Evaluate risk assessment contribution if available."""
        if not risk_assessment:
            return 5.0  # Neutral score
        
        # Combine business impact and urgency
        combined_score = (
            risk_assessment.business_impact * 0.6 +
            risk_assessment.urgency * 0.4
        )
        
        # Factor in likelihood
        return combined_score * risk_assessment.likelihood
    
    def _generate_confirmation_reason(
        self,
        incident: Incident,
        score: float,
        factors: Dict[str, float],
        confirmed: bool
    ) -> str:
        """Generate human-readable explanation for confirmation decision."""
        
        if confirmed:
            reason = f"THREAT CONFIRMED (Score: {score:.1f}/10)\n\n"
            reason += "Contributing factors:\n"
        else:
            reason = f"Threat not confirmed (Score: {score:.1f}/10)\n\n"
            reason += "Limiting factors:\n"
        
        # Analyze key factors
        if factors.get("confidence_factor", 0) >= 7:
            reason += f"✓ High confidence ({incident.confidence_score:.2f})\n"
        elif factors.get("confidence_factor", 0) < 5:
            reason += f"⚠ Low confidence ({incident.confidence_score:.2f})\n"
        
        if factors.get("sentiment_factor", 0) >= 6:
            reason += f"✓ Negative sentiment indicates threat ({incident.sentiment_score:.2f})\n"
        elif factors.get("sentiment_factor", 0) < 4:
            reason += f"⚠ Positive/neutral sentiment ({incident.sentiment_score:.2f})\n"
        
        if factors.get("source_factor", 0) >= 7:
            reason += f"✓ Reliable source type\n"
        elif factors.get("source_factor", 0) < 5:
            reason += f"⚠ Lower reliability source\n"
        
        if factors.get("keyword_factor", 0) >= 6:
            reason += f"✓ Strong keyword matches ({len(incident.keywords)} keywords)\n"
        elif factors.get("keyword_factor", 0) < 4:
            reason += f"⚠ Limited keyword matches ({len(incident.keywords)} keywords)\n"
        
        if factors.get("pattern_factor", 0) >= 7:
            reason += f"✓ Similar recent incidents detected (escalating pattern)\n"
        elif factors.get("pattern_factor", 0) < 4:
            reason += f"⚠ No recent similar incidents\n"
        
        reason += f"\nSeverity: {incident.severity.value.upper()}"
        reason += f"\nKeywords: {', '.join(incident.keywords)}"
        
        return reason
    
    async def bulk_evaluate_incidents(
        self, 
        incidents: List[Incident],
        historical_incidents: Optional[List[Incident]] = None
    ) -> List[Tuple[Incident, bool, float, str]]:
        """Evaluate multiple incidents for threat confirmation."""
        
        results = []
        for incident in incidents:
            confirmed, score, reason = await self.evaluate_incident(
                incident, None, historical_incidents
            )
            results.append((incident, confirmed, score, reason))
        
        return results
    
    def update_criteria(self, new_criteria: ConfirmationCriteria):
        """Update confirmation criteria."""
        self.criteria = new_criteria
        self.logger.info("Threat confirmation criteria updated")
    
    def get_confirmation_stats(self) -> Dict[str, any]:
        """Get statistics about recent confirmations."""
        if not self.recent_confirmations:
            return {"total_confirmations": 0}
        
        total = len(self.recent_confirmations)
        avg_risk = sum(inc.risk_score for inc in self.recent_confirmations) / total
        severity_counts = {}
        
        for incident in self.recent_confirmations:
            severity = incident.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_confirmations": total,
            "average_risk_score": avg_risk,
            "severity_distribution": severity_counts,
            "confirmation_rate": total / max(1, total)  # Would need total evaluated
        }
