"""
Base scraper class for web scraping operations.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time
import re
from urllib.parse import urljoin, urlparse
from user_agent import generate_user_agent
from requests_ratelimiter import LimiterSession

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all web scrapers."""
    
    def __init__(self, source_config: Dict[str, Any]):
        """Initialize the scraper with source configuration."""
        self.source_config = source_config
        self.name = source_config.get('name', 'Unknown Source')
        self.source_type = source_config.get('source_type', 'unknown')
        self.url_pattern = source_config.get('url_pattern', '')
        self.keywords = source_config.get('keywords', [])
        self.scraping_config = source_config.get('scraping_config', {})
        self.rate_limit = source_config.get('rate_limit', 60)
        self.reliability_score = source_config.get('reliability_score', 0.5)
        
        # Setup rate-limited session
        self.session = LimiterSession(per_minute=self.rate_limit)
        self.session.headers.update({
            'User-Agent': generate_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.scraped_urls = set()  # Track scraped URLs to avoid duplicates
        
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method - to be implemented by subclasses.
        
        Returns:
            List of scraped content items
        """
        raise NotImplementedError("Subclasses must implement the scrape method")
    
    def fetch_page(self, url: str, timeout: int = 30) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'lxml')
            return soup
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None
    
    def extract_text(self, element) -> str:
        """Extract clean text from BeautifulSoup element."""
        if not element:
            return ""
        
        text = element.get_text(strip=True)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and normalize links from page."""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            if self.is_valid_url(full_url):
                links.append(full_url)
        return list(set(links))  # Remove duplicates
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not already scraped."""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ['http', 'https'] and
                parsed.netloc and
                url not in self.scraped_urls
            )
        except:
            return False
    
    def matches_keywords(self, text: str) -> bool:
        """Check if text contains any of the configured keywords."""
        if not self.keywords:
            return True  # If no keywords specified, match everything
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.keywords)
    
    def extract_content_by_selector(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """Extract content using CSS selector."""
        try:
            elements = soup.select(selector)
            return [self.extract_text(elem) for elem in elements if elem]
        except Exception as e:
            logger.warning(f"Failed to extract content with selector '{selector}': {e}")
            return []
    
    def create_content_item(self, title: str, description: str, url: str, 
                          additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized content item."""
        item = {
            'title': title.strip(),
            'description': description.strip(),
            'url': url,
            'source_name': self.name,
            'source_type': self.source_type,
            'scraped_at': datetime.utcnow().isoformat(),
            'keywords_matched': [kw for kw in self.keywords if kw.lower() in (title + ' ' + description).lower()],
            'reliability_score': self.reliability_score
        }
        
        if additional_data:
            item.update(additional_data)
            
        return item
    
    def filter_by_keywords(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter content items by keywords."""
        if not self.keywords:
            return items
        
        filtered_items = []
        for item in items:
            text_to_check = f"{item.get('title', '')} {item.get('description', '')}"
            if self.matches_keywords(text_to_check):
                filtered_items.append(item)
        
        return filtered_items
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return {
            'source_name': self.name,
            'source_type': self.source_type,
            'urls_scraped': len(self.scraped_urls),
            'rate_limit': self.rate_limit,
            'reliability_score': self.reliability_score
        }
