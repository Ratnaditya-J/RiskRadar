"""
RiskRadar - Early warning system for emerging threats

An open-source incident response intelligence platform that automatically 
monitors the web and social media for emerging threats, providing companies 
with real-time risk assessments and sentiment-driven prioritization.
"""

__version__ = "0.1.0"
__author__ = "RiskRadar Team"
__email__ = "contact@riskradar.io"

from .core.models import Incident, RiskAssessment, Alert
from .core.engine import RiskRadarEngine

__all__ = [
    "Incident",
    "RiskAssessment", 
    "Alert",
    "RiskRadarEngine",
]
