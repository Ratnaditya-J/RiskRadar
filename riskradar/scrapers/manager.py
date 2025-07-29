"""
Scraping manager for coordinating web scraping operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
import concurrent.futures
from threading import Lock

from .news_scraper import NewsScraper
from .government_scraper import GovernmentScraper
from .social_scraper import SocialScraper
from .blog_scraper import BlogScraper
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ScrapingManager:
    """Manages web scraping operations across different sources."""
    
    def __init__(self, max_workers: int = 5):
        """Initialize the scraping manager."""
        self.active_scrapers = {}
        self.scraping_stats = {
            'total_scraped': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'last_scrape_time': None,
            'sources_by_type': {},
            'total_items_scraped': 0
        }
        self.max_workers = max_workers
        self.stats_lock = Lock()
        
        # Scraper type mapping
        self.scraper_classes = {
            'news': NewsScraper,
            'government': GovernmentScraper,
            'social_media': SocialScraper,
            'blog': BlogScraper
        }
    
    def start_scraping(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Start scraping from the provided sources.
        
        Args:
            sources: List of source configurations
            
        Returns:
            Dictionary with scraping status and results
        """
        logger.info(f"Starting scraping for {len(sources)} sources")
        
        # Filter enabled sources
        enabled_sources = [source for source in sources if source.get('enabled', False)]
        logger.info(f"Found {len(enabled_sources)} enabled sources")
        
        if not enabled_sources:
            return {
                'status': 'completed',
                'sources_count': 0,
                'message': 'No enabled sources found',
                'results': []
            }
        
        # Scrape all enabled sources
        all_results = []
        scraping_errors = []
        
        # Use ThreadPoolExecutor for concurrent scraping
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit scraping tasks
            future_to_source = {
                executor.submit(self.scrape_single_source, source): source 
                for source in enabled_sources
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    results = future.result(timeout=120)  # 2 minute timeout per source
                    all_results.extend(results)
                    
                    with self.stats_lock:
                        self.scraping_stats['successful_scrapes'] += 1
                        self.scraping_stats['total_items_scraped'] += len(results)
                        
                    logger.info(f"Successfully scraped {len(results)} items from {source.get('name')}")
                    
                except Exception as e:
                    error_msg = f"Failed to scrape {source.get('name', 'Unknown')}: {str(e)}"
                    logger.error(error_msg)
                    scraping_errors.append(error_msg)
                    
                    with self.stats_lock:
                        self.scraping_stats['failed_scrapes'] += 1
        
        # Update stats
        with self.stats_lock:
            self.scraping_stats['total_scraped'] += len(enabled_sources)
            self.scraping_stats['last_scrape_time'] = datetime.utcnow()
            
            # Update source type stats
            for source in enabled_sources:
                source_type = source.get('source_type', 'unknown')
                if source_type not in self.scraping_stats['sources_by_type']:
                    self.scraping_stats['sources_by_type'][source_type] = 0
                self.scraping_stats['sources_by_type'][source_type] += 1
        
        results = {
            'status': 'completed',
            'sources_count': len(enabled_sources),
            'items_scraped': len(all_results),
            'successful_sources': self.scraping_stats['successful_scrapes'],
            'failed_sources': self.scraping_stats['failed_scrapes'],
            'started_at': datetime.utcnow().isoformat(),
            'results': all_results,
            'errors': scraping_errors
        }
        
        logger.info(f"Scraping completed: {len(all_results)} total items from {len(enabled_sources)} sources")
        return results
    
    def stop_scraping(self) -> Dict[str, Any]:
        """Stop all active scraping operations."""
        logger.info("Stopping all scraping operations")
        
        self.active_scrapers.clear()
        
        return {
            'status': 'stopped',
            'stopped_at': datetime.utcnow().isoformat()
        }
    
    def get_scraping_status(self) -> Dict[str, Any]:
        """Get current scraping status and statistics."""
        with self.stats_lock:
            return {
                'active_scrapers': len(self.active_scrapers),
                'stats': self.scraping_stats.copy(),
                'status': 'ready' if not self.active_scrapers else 'scraping'
            }
    
    def scrape_single_source(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape a single source and return results.
        
        Args:
            source_config: Configuration for the source to scrape
            
        Returns:
            List of scraped content items
        """
        source_name = source_config.get('name', 'Unknown')
        source_type = source_config.get('source_type', 'unknown')
        
        logger.info(f"Scraping source: {source_name} (type: {source_type})")
        
        try:
            # Get appropriate scraper class
            scraper_class = self.scraper_classes.get(source_type, BaseScraper)
            
            # Create scraper instance
            scraper = scraper_class(source_config)
            
            # Add to active scrapers
            scraper_id = f"{source_name}_{datetime.utcnow().timestamp()}"
            self.active_scrapers[scraper_id] = scraper
            
            try:
                # Perform scraping
                results = scraper.scrape()
                
                # Log scraping stats
                stats = scraper.get_scraping_stats()
                logger.info(f"Scraper stats for {source_name}: {stats}")
                
                return results
                
            finally:
                # Remove from active scrapers
                if scraper_id in self.active_scrapers:
                    del self.active_scrapers[scraper_id]
                    
        except Exception as e:
            logger.error(f"Error creating scraper for {source_name}: {e}")
            raise
    
    def get_supported_source_types(self) -> List[str]:
        """Get list of supported source types."""
        return list(self.scraper_classes.keys())
    
    def validate_source_config(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate source configuration.
        
        Args:
            source_config: Source configuration to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['name', 'source_type', 'url_pattern']
        for field in required_fields:
            if not source_config.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check source type
        source_type = source_config.get('source_type')
        if source_type and source_type not in self.scraper_classes:
            errors.append(f"Unsupported source type: {source_type}")
        
        # Check URL pattern
        url_pattern = source_config.get('url_pattern')
        if url_pattern and not url_pattern.startswith(('http://', 'https://')):
            errors.append(f"Invalid URL pattern: {url_pattern}")
        
        # Check keywords
        keywords = source_config.get('keywords', [])
        if not keywords:
            warnings.append("No keywords specified - will scrape all content")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
