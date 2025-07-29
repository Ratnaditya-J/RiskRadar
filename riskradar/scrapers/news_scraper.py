"""
News source scraper for extracting articles from news websites.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class NewsScraper(BaseScraper):
    """Scraper for news websites like Reuters, BBC, AP, etc."""
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape news articles from the configured source.
        
        Returns:
            List of news article items
        """
        logger.info(f"Starting news scraping for {self.name}")
        
        try:
            # Fetch the main page
            soup = self.fetch_page(self.url_pattern)
            if not soup:
                logger.error(f"Failed to fetch main page for {self.name}")
                return []
            
            articles = []
            
            # Extract articles using configured selectors
            article_selector = self.scraping_config.get('article_selector', 'article')
            title_selector = self.scraping_config.get('title_selector', 'h1, h2, h3')
            content_selector = self.scraping_config.get('content_selector', 'p')
            link_selector = self.scraping_config.get('link_selector', 'a')
            
            # Find all article containers
            article_elements = soup.select(article_selector)
            logger.info(f"Found {len(article_elements)} article elements")
            
            for article_elem in article_elements[:20]:  # Limit to 20 articles per scrape
                try:
                    # Extract title
                    title_elem = article_elem.select_one(title_selector)
                    if not title_elem:
                        continue
                    
                    title = self.extract_text(title_elem)
                    if not title or len(title) < 10:  # Skip very short titles
                        continue
                    
                    # Extract link
                    link_elem = article_elem.select_one(link_selector)
                    article_url = self.url_pattern  # Default to main URL
                    
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        if href.startswith('http'):
                            article_url = href
                        elif href.startswith('/'):
                            base_url = '/'.join(self.url_pattern.split('/')[:3])
                            article_url = base_url + href
                    
                    # Skip if already scraped
                    if article_url in self.scraped_urls:
                        continue
                    
                    # Extract description/summary
                    description = ""
                    content_elems = article_elem.select(content_selector)
                    if content_elems:
                        # Take first few paragraphs as description
                        desc_parts = []
                        for elem in content_elems[:3]:
                            text = self.extract_text(elem)
                            if text and len(text) > 20:
                                desc_parts.append(text)
                        description = ' '.join(desc_parts)[:500]  # Limit description length
                    
                    # If no description found in article element, try to extract from linked page
                    if not description and article_url != self.url_pattern:
                        description = self._extract_article_content(article_url)
                    
                    # Check if content matches keywords
                    if not self.matches_keywords(f"{title} {description}"):
                        continue
                    
                    # Create content item
                    item = self.create_content_item(
                        title=title,
                        description=description,
                        url=article_url,
                        additional_data={
                            'article_type': 'news',
                            'published_date': self._extract_publish_date(article_elem),
                            'author': self._extract_author(article_elem)
                        }
                    )
                    
                    articles.append(item)
                    self.scraped_urls.add(article_url)
                    
                except Exception as e:
                    logger.warning(f"Error processing article element: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(articles)} articles from {self.name}")
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping {self.name}: {e}")
            return []
    
    def _extract_article_content(self, url: str) -> str:
        """Extract content from individual article page."""
        try:
            soup = self.fetch_page(url)
            if not soup:
                return ""
            
            # Try common content selectors
            content_selectors = [
                self.scraping_config.get('content_selector', ''),
                'div.article-content',
                'div.story-body',
                'div.entry-content',
                'div.post-content',
                'main p',
                'article p'
            ]
            
            for selector in content_selectors:
                if not selector:
                    continue
                    
                content_elems = soup.select(selector)
                if content_elems:
                    content_parts = []
                    for elem in content_elems[:5]:  # First 5 paragraphs
                        text = self.extract_text(elem)
                        if text and len(text) > 20:
                            content_parts.append(text)
                    
                    if content_parts:
                        return ' '.join(content_parts)[:800]  # Limit content length
            
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to extract content from {url}: {e}")
            return ""
    
    def _extract_publish_date(self, article_elem) -> str:
        """Extract publish date from article element."""
        try:
            # Try common date selectors
            date_selectors = [
                'time',
                '.date',
                '.published',
                '.timestamp',
                '[datetime]'
            ]
            
            for selector in date_selectors:
                date_elem = article_elem.select_one(selector)
                if date_elem:
                    # Try datetime attribute first
                    if date_elem.get('datetime'):
                        return date_elem['datetime']
                    
                    # Try text content
                    date_text = self.extract_text(date_elem)
                    if date_text:
                        return date_text
            
            return ""
            
        except Exception:
            return ""
    
    def _extract_author(self, article_elem) -> str:
        """Extract author from article element."""
        try:
            # Try common author selectors
            author_selectors = [
                '.author',
                '.byline',
                '.writer',
                '[rel="author"]'
            ]
            
            for selector in author_selectors:
                author_elem = article_elem.select_one(selector)
                if author_elem:
                    author = self.extract_text(author_elem)
                    if author:
                        return author
            
            return ""
            
        except Exception:
            return ""
