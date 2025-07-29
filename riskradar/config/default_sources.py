"""
Default preconfigured sources for RiskRadar threat monitoring.
"""

from typing import List, Dict, Any
from ..core.models import SourceType

DEFAULT_SOURCES: List[Dict[str, Any]] = [
    # News Sources
    {
        "name": "Reuters Security News",
        "source_type": SourceType.NEWS,
        "url_pattern": "https://www.reuters.com/technology/cybersecurity/",
        "keywords": ["cybersecurity", "data breach", "hack", "malware", "ransomware"],
        "scraping_config": {
            "article_selector": "article",
            "title_selector": "h3 a",
            "content_selector": "div[data-testid='paragraph']",
            "link_selector": "h3 a",
            "rate_limit": 30
        },
        "enabled": True,
        "reliability_score": 0.95
    },
    {
        "name": "Associated Press Security",
        "source_type": SourceType.NEWS,
        "url_pattern": "https://apnews.com/hub/technology",
        "keywords": ["security breach", "cyber attack", "hacking", "privacy"],
        "scraping_config": {
            "article_selector": "div.FeedCard",
            "title_selector": "h1, h2, h3",
            "content_selector": "div.RichTextStoryBody",
            "link_selector": "a",
            "rate_limit": 30
        },
        "enabled": True,
        "reliability_score": 0.93
    },
    {
        "name": "BBC Technology Security",
        "source_type": SourceType.NEWS,
        "url_pattern": "https://www.bbc.com/news/technology",
        "keywords": ["cyber", "security", "breach", "attack", "threat"],
        "scraping_config": {
            "article_selector": "div[data-testid='edinburgh-article']",
            "title_selector": "h1, h2",
            "content_selector": "div[data-component='text-block']",
            "link_selector": "a",
            "rate_limit": 30
        },
        "enabled": True,
        "reliability_score": 0.90
    },
    {
        "name": "TechCrunch Security",
        "source_type": SourceType.NEWS,
        "url_pattern": "https://techcrunch.com/category/security/",
        "keywords": ["startup security", "tech breach", "privacy", "encryption"],
        "scraping_config": {
            "article_selector": "article",
            "title_selector": "h2 a",
            "content_selector": "div.article-content",
            "link_selector": "h2 a",
            "rate_limit": 20
        },
        "enabled": False,
        "reliability_score": 0.85
    },
    
    # Government Sources
    {
        "name": "CISA Security Advisories",
        "source_type": SourceType.GOVERNMENT,
        "url_pattern": "https://www.cisa.gov/news-events/cybersecurity-advisories",
        "keywords": ["vulnerability", "advisory", "alert", "critical"],
        "scraping_config": {
            "article_selector": "div.c-teaser",
            "title_selector": "h3 a",
            "content_selector": "div.c-teaser__summary",
            "link_selector": "h3 a",
            "rate_limit": 60
        },
        "enabled": True,
        "reliability_score": 0.98
    },
    {
        "name": "US-CERT Alerts",
        "source_type": SourceType.GOVERNMENT,
        "url_pattern": "https://www.cisa.gov/news-events/alerts",
        "keywords": ["security alert", "threat", "incident", "response"],
        "scraping_config": {
            "article_selector": "div.views-row",
            "title_selector": "h3 a",
            "content_selector": "div.field-content",
            "link_selector": "h3 a",
            "rate_limit": 60
        },
        "enabled": True,
        "reliability_score": 0.97
    },
    
    # Social Media Sources
    {
        "name": "Reddit r/cybersecurity",
        "source_type": SourceType.SOCIAL_MEDIA,
        "url_pattern": "https://www.reddit.com/r/cybersecurity/hot.json",
        "keywords": ["breach", "vulnerability", "exploit", "incident"],
        "scraping_config": {
            "api_endpoint": "https://www.reddit.com/r/cybersecurity/hot.json",
            "post_selector": "data.children",
            "title_selector": "data.title",
            "content_selector": "data.selftext",
            "score_selector": "data.score",
            "rate_limit": 60
        },
        "enabled": False,
        "reliability_score": 0.70
    },
    {
        "name": "Reddit r/netsec",
        "source_type": SourceType.SOCIAL_MEDIA,
        "url_pattern": "https://www.reddit.com/r/netsec/hot.json",
        "keywords": ["security research", "exploit", "vulnerability", "analysis"],
        "scraping_config": {
            "api_endpoint": "https://www.reddit.com/r/netsec/hot.json",
            "post_selector": "data.children",
            "title_selector": "data.title",
            "content_selector": "data.selftext",
            "score_selector": "data.score",
            "rate_limit": 60
        },
        "enabled": True,
        "reliability_score": 0.75
    },
    
    # Security Forums
    {
        "name": "Krebs on Security",
        "source_type": SourceType.BLOG,
        "url_pattern": "https://krebsonsecurity.com/",
        "keywords": ["investigation", "fraud", "cybercrime", "breach"],
        "scraping_config": {
            "article_selector": "article",
            "title_selector": "h1, h2",
            "content_selector": "div.entry-content",
            "link_selector": "h1 a, h2 a",
            "rate_limit": 30
        },
        "enabled": True,
        "reliability_score": 0.92
    },
    {
        "name": "Threatpost Security News",
        "source_type": SourceType.NEWS,
        "url_pattern": "https://threatpost.com/",
        "keywords": ["threat intelligence", "malware", "apt", "zero-day"],
        "scraping_config": {
            "article_selector": "article",
            "title_selector": "h2 a",
            "content_selector": "div.entry-content",
            "link_selector": "h2 a",
            "rate_limit": 20
        },
        "enabled": False,
        "reliability_score": 0.88
    }
]

# Source categories for UI organization
SOURCE_CATEGORIES = {
    "news": {
        "label": "News Sources",
        "description": "Major news outlets covering cybersecurity",
        "sources": ["Reuters Security News", "Associated Press Security", "BBC Technology Security", "TechCrunch Security", "Threatpost Security News"]
    },
    "government": {
        "label": "Government Sources", 
        "description": "Official government security advisories",
        "sources": ["CISA Security Advisories", "US-CERT Alerts"]
    },
    "social": {
        "label": "Social Media & Forums",
        "description": "Community discussions and security forums",
        "sources": ["Reddit r/cybersecurity", "Reddit r/netsec"]
    },
    "blogs": {
        "label": "Security Blogs",
        "description": "Expert security analysis and research",
        "sources": ["Krebs on Security"]
    }
}

def get_default_sources() -> List[Dict[str, Any]]:
    """Get the list of default preconfigured sources."""
    return DEFAULT_SOURCES.copy()

def get_source_categories() -> Dict[str, Dict[str, Any]]:
    """Get source categories for UI organization."""
    return SOURCE_CATEGORIES.copy()

def get_sources_by_category(category: str) -> List[Dict[str, Any]]:
    """Get sources filtered by category."""
    if category not in SOURCE_CATEGORIES:
        return []
    
    category_sources = SOURCE_CATEGORIES[category]["sources"]
    return [source for source in DEFAULT_SOURCES if source["name"] in category_sources]
