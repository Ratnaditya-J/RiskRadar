"""
Core RiskRadar engine for orchestrating incident detection and analysis.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models import Incident, RiskAssessment, Alert, SeverityLevel, IncidentStatus
from ..scrapers.manager import ScrapingManager
from ..analysis.sentiment import SentimentAnalyzer
from ..analysis.risk_scorer import RiskScorer
from ..analysis.entity_extractor import EntityExtractor


@dataclass
class EngineConfig:
    """Configuration for the RiskRadar engine."""
    monitoring_keywords: List[str]
    scraping_interval: int = 300  # seconds
    risk_threshold: float = 5.0
    sentiment_weight: float = 0.3
    max_concurrent_scrapers: int = 10
    alert_cooldown: int = 3600  # seconds


class RiskRadarEngine:
    """
    Main orchestration engine for RiskRadar incident detection and analysis.
    
    Coordinates web scraping, content analysis, risk assessment, and alerting
    to provide comprehensive incident response intelligence.
    """
    
    def __init__(self, config: EngineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.scraping_manager = ScrapingManager(
            max_concurrent=config.max_concurrent_scrapers
        )
        self.sentiment_analyzer = SentimentAnalyzer()
        self.risk_scorer = RiskScorer()
        self.entity_extractor = EntityExtractor()
        
        # Runtime state
        self.active_incidents: Dict[str, Incident] = {}
        self.recent_alerts: Dict[str, datetime] = {}
        self.is_running = False
        
    async def start_monitoring(self) -> None:
        """Start the continuous monitoring process."""
        self.logger.info("Starting RiskRadar monitoring engine")
        self.is_running = True
        
        while self.is_running:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(self.config.scraping_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring process."""
        self.logger.info("Stopping RiskRadar monitoring engine")
        self.is_running = False
        await self.scraping_manager.shutdown()
    
    async def _monitoring_cycle(self) -> None:
        """Execute a single monitoring cycle."""
        self.logger.info("Starting monitoring cycle")
        
        # 1. Scrape content from all configured sources
        scraped_content = await self.scraping_manager.scrape_all_sources(
            keywords=self.config.monitoring_keywords
        )
        
        # 2. Process each piece of content
        new_incidents = []
        for content in scraped_content:
            incident = await self._process_content(content)
            if incident:
                new_incidents.append(incident)
        
        # 3. Update existing incidents and detect trends
        await self._update_incident_trends()
        
        # 4. Generate alerts for high-risk incidents
        await self._generate_alerts(new_incidents)
        
        self.logger.info(f"Monitoring cycle complete. Processed {len(scraped_content)} items, "
                        f"detected {len(new_incidents)} new incidents")
    
    async def _process_content(self, content: Dict[str, Any]) -> Optional[Incident]:
        """Process a single piece of scraped content into an incident."""
        try:
            # Extract basic information
            title = content.get('title', '')
            text = content.get('text', '')
            url = content.get('url', '')
            source_type = content.get('source_type', 'unknown')
            
            if not title or not text:
                return None
            
            # Check if content matches monitoring keywords
            matched_keywords = self._extract_matched_keywords(text)
            if not matched_keywords:
                return None
            
            # Perform analysis
            sentiment_score = await self.sentiment_analyzer.analyze(text)
            entities = await self.entity_extractor.extract(text)
            risk_score = await self.risk_scorer.calculate_risk(
                text=text,
                sentiment=sentiment_score,
                entities=entities,
                source_type=source_type
            )
            
            # Create incident
            incident = Incident(
                title=title,
                description=text[:1000],  # Truncate for storage
                keywords=matched_keywords,
                severity=self._calculate_severity(risk_score),
                confidence_score=self._calculate_confidence(content),
                risk_score=risk_score,
                sentiment_score=sentiment_score,
                source_urls=[url],
                entities=entities,
                incident_metadata={
                    'source_type': source_type,
                    'scraped_at': datetime.utcnow().isoformat(),
                    'content_length': len(text)
                }
            )
            
            # Check for duplicates
            if not self._is_duplicate_incident(incident):
                self.active_incidents[incident.id] = incident
                return incident
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing content: {e}")
            return None
    
    def _extract_matched_keywords(self, text: str) -> List[str]:
        """Extract keywords that match monitoring criteria."""
        text_lower = text.lower()
        matched = []
        
        for keyword in self.config.monitoring_keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        
        return matched
    
    def _calculate_severity(self, risk_score: float) -> SeverityLevel:
        """Calculate severity level based on risk score."""
        if risk_score >= 8.0:
            return SeverityLevel.CRITICAL
        elif risk_score >= 6.0:
            return SeverityLevel.HIGH
        elif risk_score >= 4.0:
            return SeverityLevel.MEDIUM
        elif risk_score >= 2.0:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.INFO
    
    def _calculate_confidence(self, content: Dict[str, Any]) -> float:
        """Calculate confidence score based on content quality indicators."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for reputable sources
        source_domain = content.get('domain', '').lower()
        if any(domain in source_domain for domain in ['reuters.com', 'ap.org', 'bbc.com']):
            confidence += 0.3
        
        # Boost confidence for longer, detailed content
        text_length = len(content.get('text', ''))
        if text_length > 500:
            confidence += 0.1
        if text_length > 1000:
            confidence += 0.1
        
        # Reduce confidence for social media posts
        if content.get('source_type') == 'social_media':
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def _is_duplicate_incident(self, new_incident: Incident) -> bool:
        """Check if incident is a duplicate of existing incidents."""
        for existing_incident in self.active_incidents.values():
            # Simple similarity check based on title and keywords
            title_similarity = self._calculate_text_similarity(
                new_incident.title, existing_incident.title
            )
            
            keyword_overlap = len(set(new_incident.keywords) & set(existing_incident.keywords))
            
            if title_similarity > 0.8 or keyword_overlap >= 2:
                return True
        
        return False
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity score."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    async def _update_incident_trends(self) -> None:
        """Update trends for existing incidents."""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Remove old incidents
        expired_incidents = [
            incident_id for incident_id, incident in self.active_incidents.items()
            if incident.created_at < cutoff_time
        ]
        
        for incident_id in expired_incidents:
            del self.active_incidents[incident_id]
    
    async def _generate_alerts(self, new_incidents: List[Incident]) -> None:
        """Generate alerts for high-risk incidents."""
        for incident in new_incidents:
            if incident.risk_score >= self.config.risk_threshold:
                # Check alert cooldown
                if self._should_send_alert(incident):
                    alert = Alert(
                        incident_id=incident.id,
                        alert_type="high_risk_incident",
                        severity=incident.severity,
                        title=f"High Risk Incident Detected: {incident.title}",
                        message=self._format_alert_message(incident)
                    )
                    
                    # TODO: Send alert via configured channels
                    self.logger.warning(f"ALERT: {alert.title}")
                    self.recent_alerts[incident.id] = datetime.utcnow()
    
    def _should_send_alert(self, incident: Incident) -> bool:
        """Check if an alert should be sent for this incident."""
        # Check if we've recently sent an alert for similar incidents
        last_alert = self.recent_alerts.get(incident.id)
        if last_alert:
            time_since_alert = (datetime.utcnow() - last_alert).total_seconds()
            if time_since_alert < self.config.alert_cooldown:
                return False
        
        return True
    
    def _format_alert_message(self, incident: Incident) -> str:
        """Format alert message for incident."""
        return f"""
Risk Score: {incident.risk_score:.1f}/10
Severity: {incident.severity.value.upper()}
Sentiment: {incident.sentiment_score:.2f}
Keywords: {', '.join(incident.keywords)}

Description: {incident.description[:200]}...

Source URLs:
{chr(10).join(incident.source_urls[:3])}
        """.strip()
    
    async def get_active_incidents(self) -> List[Incident]:
        """Get all currently active incidents."""
        return list(self.active_incidents.values())
    
    async def get_incident_by_id(self, incident_id: str) -> Optional[Incident]:
        """Get a specific incident by ID."""
        return self.active_incidents.get(incident_id)
    
    async def dismiss_incident(self, incident_id: str) -> bool:
        """Dismiss an incident."""
        if incident_id in self.active_incidents:
            self.active_incidents[incident_id].status = IncidentStatus.DISMISSED
            return True
        return False
