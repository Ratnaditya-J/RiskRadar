"""
Government source scraper for extracting security advisories and alerts.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GovernmentScraper(BaseScraper):
    """Scraper for government sources like CISA, US-CERT, etc."""
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape security advisories from government sources.
        
        Returns:
            List of security advisory items
        """
        logger.info(f"Starting government scraping for {self.name}")
        
        try:
            # Fetch the main page
            soup = self.fetch_page(self.url_pattern)
            if not soup:
                logger.error(f"Failed to fetch main page for {self.name}")
                return []
            
            advisories = []
            
            # Extract advisories using configured selectors
            advisory_selector = self.scraping_config.get('article_selector', '.c-teaser, .views-row')
            title_selector = self.scraping_config.get('title_selector', 'h3 a, h2 a')
            content_selector = self.scraping_config.get('content_selector', '.c-teaser__summary, .field-content')
            link_selector = self.scraping_config.get('link_selector', 'h3 a, h2 a')
            
            # Find all advisory containers
            advisory_elements = soup.select(advisory_selector)
            logger.info(f"Found {len(advisory_elements)} advisory elements")
            
            for advisory_elem in advisory_elements[:15]:  # Limit to 15 advisories per scrape
                try:
                    # Extract title
                    title_elem = advisory_elem.select_one(title_selector)
                    if not title_elem:
                        continue
                    
                    title = self.extract_text(title_elem)
                    if not title or len(title) < 5:
                        continue
                    
                    # Extract link
                    link_elem = advisory_elem.select_one(link_selector)
                    advisory_url = self.url_pattern  # Default to main URL
                    
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        if href.startswith('http'):
                            advisory_url = href
                        elif href.startswith('/'):
                            base_url = '/'.join(self.url_pattern.split('/')[:3])
                            advisory_url = base_url + href
                    
                    # Skip if already scraped
                    if advisory_url in self.scraped_urls:
                        continue
                    
                    # Extract summary/description
                    description = ""
                    content_elems = advisory_elem.select(content_selector)
                    if content_elems:
                        desc_parts = []
                        for elem in content_elems[:2]:
                            text = self.extract_text(elem)
                            if text and len(text) > 10:
                                desc_parts.append(text)
                        description = ' '.join(desc_parts)[:600]
                    
                    # If no description found, try to extract from linked page
                    if not description and advisory_url != self.url_pattern:
                        description = self._extract_advisory_content(advisory_url)
                    
                    # Check if content matches keywords
                    if not self.matches_keywords(f"{title} {description}"):
                        continue
                    
                    # Extract additional metadata
                    severity = self._extract_severity(advisory_elem, title, description)
                    advisory_id = self._extract_advisory_id(title, advisory_url)
                    
                    # Create content item
                    item = self.create_content_item(
                        title=title,
                        description=description,
                        url=advisory_url,
                        additional_data={
                            'article_type': 'security_advisory',
                            'advisory_id': advisory_id,
                            'severity': severity,
                            'published_date': self._extract_publish_date(advisory_elem),
                            'cve_ids': self._extract_cve_ids(title, description),
                            'affected_products': self._extract_affected_products(description)
                        }
                    )
                    
                    advisories.append(item)
                    self.scraped_urls.add(advisory_url)
                    
                except Exception as e:
                    logger.warning(f"Error processing advisory element: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(advisories)} advisories from {self.name}")
            return advisories
            
        except Exception as e:
            logger.error(f"Error scraping {self.name}: {e}")
            return []
    
    def _extract_advisory_content(self, url: str) -> str:
        """Extract content from individual advisory page."""
        try:
            soup = self.fetch_page(url)
            if not soup:
                return ""
            
            # Try common content selectors for government sites
            content_selectors = [
                '.field-content',
                '.advisory-content',
                '.alert-content',
                'main .content',
                '.page-content p',
                'article p'
            ]
            
            for selector in content_selectors:
                content_elems = soup.select(selector)
                if content_elems:
                    content_parts = []
                    for elem in content_elems[:4]:
                        text = self.extract_text(elem)
                        if text and len(text) > 15:
                            content_parts.append(text)
                    
                    if content_parts:
                        return ' '.join(content_parts)[:1000]
            
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to extract advisory content from {url}: {e}")
            return ""
    
    def _extract_severity(self, advisory_elem, title: str, description: str) -> str:
        """Extract severity level from advisory."""
        try:
            # Look for severity indicators in text
            text = f"{title} {description}".lower()
            
            if any(word in text for word in ['critical', 'emergency', 'urgent']):
                return 'CRITICAL'
            elif any(word in text for word in ['high', 'important', 'severe']):
                return 'HIGH'
            elif any(word in text for word in ['medium', 'moderate']):
                return 'MEDIUM'
            elif any(word in text for word in ['low', 'minor']):
                return 'LOW'
            
            # Look for CVSS scores
            import re
            cvss_match = re.search(r'cvss[:\s]*(\d+\.?\d*)', text)
            if cvss_match:
                score = float(cvss_match.group(1))
                if score >= 9.0:
                    return 'CRITICAL'
                elif score >= 7.0:
                    return 'HIGH'
                elif score >= 4.0:
                    return 'MEDIUM'
                else:
                    return 'LOW'
            
            return 'MEDIUM'  # Default
            
        except Exception:
            return 'MEDIUM'
    
    def _extract_advisory_id(self, title: str, url: str) -> str:
        """Extract advisory ID from title or URL."""
        try:
            import re
            
            # Look for common advisory ID patterns
            patterns = [
                r'(CVE-\d{4}-\d+)',
                r'(CISA-\d{4}-\d+)',
                r'(AA\d{2}-\d+)',
                r'(ICS-CERT-\d+)',
                r'(VU#\d+)'
            ]
            
            text = f"{title} {url}"
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return ""
            
        except Exception:
            return ""
    
    def _extract_publish_date(self, advisory_elem) -> str:
        """Extract publish date from advisory element."""
        try:
            # Try common date selectors for government sites
            date_selectors = [
                'time',
                '.date',
                '.published',
                '.release-date',
                '.field-date'
            ]
            
            for selector in date_selectors:
                date_elem = advisory_elem.select_one(selector)
                if date_elem:
                    if date_elem.get('datetime'):
                        return date_elem['datetime']
                    
                    date_text = self.extract_text(date_elem)
                    if date_text:
                        return date_text
            
            return ""
            
        except Exception:
            return ""
    
    def _extract_cve_ids(self, title: str, description: str) -> List[str]:
        """Extract CVE IDs from text."""
        try:
            import re
            text = f"{title} {description}"
            cve_pattern = r'CVE-\d{4}-\d+'
            return list(set(re.findall(cve_pattern, text, re.IGNORECASE)))
        except Exception:
            return []
    
    def _extract_affected_products(self, description: str) -> List[str]:
        """Extract affected products/vendors from description."""
        try:
            # Common product/vendor keywords
            products = []
            product_keywords = [
                'microsoft', 'windows', 'office', 'exchange',
                'cisco', 'juniper', 'vmware', 'apache',
                'oracle', 'adobe', 'google', 'chrome',
                'firefox', 'safari', 'linux', 'ubuntu'
            ]
            
            description_lower = description.lower()
            for keyword in product_keywords:
                if keyword in description_lower:
                    products.append(keyword.title())
            
            return list(set(products))
            
        except Exception:
            return []
