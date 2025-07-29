"""
Blog scraper for extracting articles from security blogs and tech sites.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BlogScraper(BaseScraper):
    """Scraper for security blogs like KrebsOnSecurity, ThreatPost, etc."""
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape blog articles from the configured source.
        
        Returns:
            List of blog article items
        """
        logger.info(f"Starting blog scraping for {self.name}")
        
        try:
            # Fetch the main page
            soup = self.fetch_page(self.url_pattern)
            if not soup:
                logger.error(f"Failed to fetch main page for {self.name}")
                return []
            
            articles = []
            
            # Extract articles using configured selectors
            article_selector = self.scraping_config.get('article_selector', 'article, .post, .entry')
            title_selector = self.scraping_config.get('title_selector', 'h1, h2, h3, .title')
            content_selector = self.scraping_config.get('content_selector', '.content, .excerpt, p')
            link_selector = self.scraping_config.get('link_selector', 'a')
            
            # Find all article containers
            article_elements = soup.select(article_selector)
            logger.info(f"Found {len(article_elements)} blog article elements")
            
            for article_elem in article_elements[:15]:  # Limit to 15 articles per scrape
                try:
                    # Extract title
                    title_elem = article_elem.select_one(title_selector)
                    if not title_elem:
                        continue
                    
                    title = self.extract_text(title_elem)
                    if not title or len(title) < 10:
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
                    
                    # Extract description/excerpt
                    description = ""
                    content_elems = article_elem.select(content_selector)
                    if content_elems:
                        desc_parts = []
                        for elem in content_elems[:3]:
                            text = self.extract_text(elem)
                            if text and len(text) > 20:
                                desc_parts.append(text)
                        description = ' '.join(desc_parts)[:600]
                    
                    # If no description found, try to extract from linked page
                    if not description and article_url != self.url_pattern:
                        description = self._extract_article_content(article_url)
                    
                    # Check if content matches keywords
                    if not self.matches_keywords(f"{title} {description}"):
                        continue
                    
                    # Extract additional metadata
                    tags = self._extract_tags(article_elem)
                    category = self._extract_category(article_elem)
                    
                    # Create content item
                    item = self.create_content_item(
                        title=title,
                        description=description,
                        url=article_url,
                        additional_data={
                            'article_type': 'blog_post',
                            'published_date': self._extract_publish_date(article_elem),
                            'author': self._extract_author(article_elem),
                            'tags': tags,
                            'category': category,
                            'word_count': len(description.split()) if description else 0
                        }
                    )
                    
                    articles.append(item)
                    self.scraped_urls.add(article_url)
                    
                except Exception as e:
                    logger.warning(f"Error processing blog article element: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(articles)} articles from {self.name}")
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping {self.name}: {e}")
            return []
    
    def _extract_article_content(self, url: str) -> str:
        """Extract content from individual blog article page."""
        try:
            soup = self.fetch_page(url)
            if not soup:
                return ""
            
            # Try common content selectors for blogs
            content_selectors = [
                '.entry-content',
                '.post-content',
                '.article-content',
                '.content',
                'main p',
                'article p'
            ]
            
            for selector in content_selectors:
                content_elems = soup.select(selector)
                if content_elems:
                    content_parts = []
                    for elem in content_elems[:5]:  # First 5 paragraphs
                        text = self.extract_text(elem)
                        if text and len(text) > 20:
                            content_parts.append(text)
                    
                    if content_parts:
                        return ' '.join(content_parts)[:800]
            
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to extract blog content from {url}: {e}")
            return ""
    
    def _extract_publish_date(self, article_elem) -> str:
        """Extract publish date from article element."""
        try:
            # Try common date selectors for blogs
            date_selectors = [
                'time',
                '.date',
                '.published',
                '.post-date',
                '.entry-date',
                '.meta-date'
            ]
            
            for selector in date_selectors:
                date_elem = article_elem.select_one(selector)
                if date_elem:
                    if date_elem.get('datetime'):
                        return date_elem['datetime']
                    
                    date_text = self.extract_text(date_elem)
                    if date_text:
                        return date_text
            
            return ""
            
        except Exception:
            return ""
    
    def _extract_author(self, article_elem) -> str:
        """Extract author from article element."""
        try:
            # Try common author selectors for blogs
            author_selectors = [
                '.author',
                '.byline',
                '.post-author',
                '.entry-author',
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
    
    def _extract_tags(self, article_elem) -> List[str]:
        """Extract tags from article element."""
        try:
            tags = []
            
            # Try common tag selectors
            tag_selectors = [
                '.tags a',
                '.post-tags a',
                '.entry-tags a',
                '.tag-links a'
            ]
            
            for selector in tag_selectors:
                tag_elems = article_elem.select(selector)
                for tag_elem in tag_elems:
                    tag = self.extract_text(tag_elem)
                    if tag and len(tag) > 1:
                        tags.append(tag)
            
            return list(set(tags))  # Remove duplicates
            
        except Exception:
            return []
    
    def _extract_category(self, article_elem) -> str:
        """Extract category from article element."""
        try:
            # Try common category selectors
            category_selectors = [
                '.category',
                '.post-category',
                '.entry-category',
                '.cat-links a'
            ]
            
            for selector in category_selectors:
                category_elem = article_elem.select_one(selector)
                if category_elem:
                    category = self.extract_text(category_elem)
                    if category:
                        return category
            
            return ""
            
        except Exception:
            return ""
