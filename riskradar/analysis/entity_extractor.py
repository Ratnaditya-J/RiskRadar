"""
Entity extraction module for identifying key entities in threat content.
"""

from typing import Dict, List, Any
import re
import logging

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracts entities from text content for threat analysis."""
    
    def __init__(self):
        """Initialize the entity extractor."""
        # Predefined patterns for common entity types
        self.patterns = {
            'ip_addresses': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'domains': r'\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}\b',
            'urls': r'https?://[^\s<>"{}|\\^`\[\]]+',
            'email_addresses': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'file_hashes': r'\b[a-fA-F0-9]{32,64}\b',
            'cve_ids': r'CVE-\d{4}-\d{4,7}',
            'bitcoin_addresses': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'
        }
        
        # Common threat-related keywords
        self.threat_keywords = [
            'malware', 'ransomware', 'phishing', 'exploit', 'vulnerability',
            'breach', 'attack', 'trojan', 'virus', 'botnet', 'ddos',
            'injection', 'backdoor', 'rootkit', 'spyware', 'adware'
        ]
        
        logger.info("EntityExtractor initialized")
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from the given text.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary with entity types as keys and lists of found entities as values
        """
        if not text or not text.strip():
            return {}
        
        entities = {}
        
        # Extract entities using regex patterns
        for entity_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Remove duplicates while preserving order
                entities[entity_type] = list(dict.fromkeys(matches))
        
        # Extract threat keywords
        threat_keywords_found = []
        text_lower = text.lower()
        for keyword in self.threat_keywords:
            if keyword in text_lower:
                threat_keywords_found.append(keyword)
        
        if threat_keywords_found:
            entities['threat_keywords'] = threat_keywords_found
        
        # Extract organizations/companies (simple heuristic)
        org_patterns = [
            r'\b[A-Z][a-z]+ (?:Inc|Corp|LLC|Ltd|Company|Corporation|Technologies|Systems|Security)\b',
            r'\b(?:Microsoft|Google|Apple|Amazon|Facebook|Twitter|LinkedIn|GitHub|Cisco|IBM|Oracle)\b'
        ]
        
        organizations = []
        for pattern in org_patterns:
            matches = re.findall(pattern, text)
            organizations.extend(matches)
        
        if organizations:
            entities['organizations'] = list(dict.fromkeys(organizations))
        
        return entities
    
    def extract_iocs(self, text: str) -> Dict[str, List[str]]:
        """
        Extract Indicators of Compromise (IOCs) from text.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary with IOC types and their values
        """
        iocs = {}
        
        # Extract specific IOC types
        ioc_patterns = {
            'ip_addresses': self.patterns['ip_addresses'],
            'domains': self.patterns['domains'],
            'urls': self.patterns['urls'],
            'file_hashes': self.patterns['file_hashes'],
            'cve_ids': self.patterns['cve_ids']
        }
        
        for ioc_type, pattern in ioc_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                iocs[ioc_type] = list(dict.fromkeys(matches))
        
        return iocs
    
    def extract_batch(self, texts: List[str]) -> List[Dict[str, List[str]]]:
        """
        Extract entities from a batch of texts.
        
        Args:
            texts: List of text strings to analyze
            
        Returns:
            List of entity extraction results
        """
        return [self.extract_entities(text) for text in texts]
    
    def get_entity_summary(self, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Get a summary of extracted entities.
        
        Args:
            entities: Dictionary of extracted entities
            
        Returns:
            Summary statistics and counts
        """
        summary = {
            'total_entities': sum(len(entity_list) for entity_list in entities.values()),
            'entity_types': len(entities),
            'counts_by_type': {entity_type: len(entity_list) 
                             for entity_type, entity_list in entities.items()},
            'has_iocs': any(entity_type in ['ip_addresses', 'domains', 'urls', 'file_hashes', 'cve_ids'] 
                           for entity_type in entities.keys()),
            'has_threat_keywords': 'threat_keywords' in entities
        }
        
        return summary
    
    def validate_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Validate and clean extracted entities.
        
        Args:
            entities: Dictionary of extracted entities
            
        Returns:
            Cleaned and validated entities
        """
        validated = {}
        
        for entity_type, entity_list in entities.items():
            cleaned_entities = []
            
            for entity in entity_list:
                # Basic validation and cleaning
                entity = entity.strip()
                
                if entity_type == 'ip_addresses':
                    # Validate IP address format
                    parts = entity.split('.')
                    if len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts if part.isdigit()):
                        cleaned_entities.append(entity)
                
                elif entity_type == 'domains':
                    # Basic domain validation
                    if '.' in entity and len(entity) > 3:
                        cleaned_entities.append(entity.lower())
                
                elif entity_type == 'urls':
                    # Basic URL validation
                    if entity.startswith(('http://', 'https://')):
                        cleaned_entities.append(entity)
                
                else:
                    # For other types, just add if not empty
                    if entity:
                        cleaned_entities.append(entity)
            
            if cleaned_entities:
                validated[entity_type] = list(dict.fromkeys(cleaned_entities))
        
        return validated
