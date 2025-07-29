"""
Social media scraper for extracting posts from Reddit, Twitter, etc.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SocialScraper(BaseScraper):
    """Scraper for social media platforms like Reddit, Twitter, etc."""
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape posts from social media sources.
        
        Returns:
            List of social media post items
        """
        logger.info(f"Starting social media scraping for {self.name}")
        
        try:
            # Determine platform type
            if 'reddit.com' in self.url_pattern:
                return self._scrape_reddit()
            elif 'twitter.com' in self.url_pattern or 'x.com' in self.url_pattern:
                return self._scrape_twitter()
            else:
                return self._scrape_generic_forum()
            
        except Exception as e:
            logger.error(f"Error scraping {self.name}: {e}")
            return []
    
    def _scrape_reddit(self) -> List[Dict[str, Any]]:
        """Scrape Reddit posts."""
        try:
            # For Reddit, we'll scrape the web interface
            soup = self.fetch_page(self.url_pattern)
            if not soup:
                return []
            
            posts = []
            
            # Reddit post selectors
            post_selector = self.scraping_config.get('article_selector', '[data-testid="post-container"]')
            title_selector = self.scraping_config.get('title_selector', 'h3')
            content_selector = self.scraping_config.get('content_selector', '[data-testid="post-content"]')
            
            post_elements = soup.select(post_selector)
            logger.info(f"Found {len(post_elements)} Reddit post elements")
            
            for post_elem in post_elements[:10]:  # Limit to 10 posts
                try:
                    # Extract title
                    title_elem = post_elem.select_one(title_selector)
                    if not title_elem:
                        continue
                    
                    title = self.extract_text(title_elem)
                    if not title or len(title) < 5:
                        continue
                    
                    # Extract content
                    description = ""
                    content_elem = post_elem.select_one(content_selector)
                    if content_elem:
                        description = self.extract_text(content_elem)[:500]
                    
                    # Extract link
                    link_elem = post_elem.select_one('a[href*="/comments/"]')
                    post_url = self.url_pattern
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        if href.startswith('/'):
                            post_url = 'https://reddit.com' + href
                        elif href.startswith('http'):
                            post_url = href
                    
                    # Skip if already scraped
                    if post_url in self.scraped_urls:
                        continue
                    
                    # Check keywords
                    if not self.matches_keywords(f"{title} {description}"):
                        continue
                    
                    # Extract metadata
                    upvotes = self._extract_reddit_upvotes(post_elem)
                    comments = self._extract_reddit_comments(post_elem)
                    subreddit = self._extract_subreddit(post_url)
                    
                    item = self.create_content_item(
                        title=title,
                        description=description,
                        url=post_url,
                        additional_data={
                            'article_type': 'reddit_post',
                            'platform': 'reddit',
                            'subreddit': subreddit,
                            'upvotes': upvotes,
                            'comments_count': comments,
                            'engagement_score': upvotes + (comments * 2)
                        }
                    )
                    
                    posts.append(item)
                    self.scraped_urls.add(post_url)
                    
                except Exception as e:
                    logger.warning(f"Error processing Reddit post: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"Error scraping Reddit: {e}")
            return []
    
    def _scrape_twitter(self) -> List[Dict[str, Any]]:
        """Scrape Twitter/X posts (limited due to API restrictions)."""
        try:
            # Note: Twitter scraping is very limited due to their restrictions
            # This is a basic implementation that may not work reliably
            soup = self.fetch_page(self.url_pattern)
            if not soup:
                return []
            
            tweets = []
            
            # Twitter selectors (these may change frequently)
            tweet_selector = '[data-testid="tweet"]'
            text_selector = '[data-testid="tweetText"]'
            
            tweet_elements = soup.select(tweet_selector)
            logger.info(f"Found {len(tweet_elements)} tweet elements")
            
            for tweet_elem in tweet_elements[:5]:  # Very limited
                try:
                    text_elem = tweet_elem.select_one(text_selector)
                    if not text_elem:
                        continue
                    
                    text = self.extract_text(text_elem)
                    if not text or len(text) < 10:
                        continue
                    
                    # Check keywords
                    if not self.matches_keywords(text):
                        continue
                    
                    item = self.create_content_item(
                        title=text[:100] + "..." if len(text) > 100 else text,
                        description=text,
                        url=self.url_pattern,
                        additional_data={
                            'article_type': 'tweet',
                            'platform': 'twitter',
                            'character_count': len(text)
                        }
                    )
                    
                    tweets.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error processing tweet: {e}")
                    continue
            
            return tweets
            
        except Exception as e:
            logger.error(f"Error scraping Twitter: {e}")
            return []
    
    def _scrape_generic_forum(self) -> List[Dict[str, Any]]:
        """Scrape generic forum or discussion platform."""
        try:
            soup = self.fetch_page(self.url_pattern)
            if not soup:
                return []
            
            posts = []
            
            # Generic forum selectors
            post_selector = self.scraping_config.get('article_selector', '.post, .topic, .thread')
            title_selector = self.scraping_config.get('title_selector', 'h2, h3, .title')
            content_selector = self.scraping_config.get('content_selector', '.content, .message, p')
            
            post_elements = soup.select(post_selector)
            logger.info(f"Found {len(post_elements)} forum post elements")
            
            for post_elem in post_elements[:15]:
                try:
                    title_elem = post_elem.select_one(title_selector)
                    if not title_elem:
                        continue
                    
                    title = self.extract_text(title_elem)
                    if not title or len(title) < 5:
                        continue
                    
                    # Extract content
                    description = ""
                    content_elems = post_elem.select(content_selector)
                    if content_elems:
                        desc_parts = []
                        for elem in content_elems[:2]:
                            text = self.extract_text(elem)
                            if text and len(text) > 10:
                                desc_parts.append(text)
                        description = ' '.join(desc_parts)[:400]
                    
                    # Extract link
                    link_elem = post_elem.select_one('a')
                    post_url = self.url_pattern
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        if href.startswith('http'):
                            post_url = href
                        elif href.startswith('/'):
                            base_url = '/'.join(self.url_pattern.split('/')[:3])
                            post_url = base_url + href
                    
                    # Skip if already scraped
                    if post_url in self.scraped_urls:
                        continue
                    
                    # Check keywords
                    if not self.matches_keywords(f"{title} {description}"):
                        continue
                    
                    item = self.create_content_item(
                        title=title,
                        description=description,
                        url=post_url,
                        additional_data={
                            'article_type': 'forum_post',
                            'platform': 'forum'
                        }
                    )
                    
                    posts.append(item)
                    self.scraped_urls.add(post_url)
                    
                except Exception as e:
                    logger.warning(f"Error processing forum post: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"Error scraping forum: {e}")
            return []
    
    def _extract_reddit_upvotes(self, post_elem) -> int:
        """Extract upvote count from Reddit post."""
        try:
            upvote_selectors = [
                '[data-testid="upvote-button"]',
                '.upvotes',
                '.score'
            ]
            
            for selector in upvote_selectors:
                upvote_elem = post_elem.select_one(selector)
                if upvote_elem:
                    text = self.extract_text(upvote_elem)
                    # Extract number from text
                    import re
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        return int(numbers[0])
            
            return 0
            
        except Exception:
            return 0
    
    def _extract_reddit_comments(self, post_elem) -> int:
        """Extract comment count from Reddit post."""
        try:
            comment_selectors = [
                '[data-testid="comment-button"]',
                '.comments',
                '.comment-count'
            ]
            
            for selector in comment_selectors:
                comment_elem = post_elem.select_one(selector)
                if comment_elem:
                    text = self.extract_text(comment_elem)
                    import re
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        return int(numbers[0])
            
            return 0
            
        except Exception:
            return 0
    
    def _extract_subreddit(self, url: str) -> str:
        """Extract subreddit name from Reddit URL."""
        try:
            import re
            match = re.search(r'/r/([^/]+)', url)
            if match:
                return match.group(1)
            return ""
        except Exception:
            return ""
