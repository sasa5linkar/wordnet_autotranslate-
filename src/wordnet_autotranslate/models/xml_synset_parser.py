"""
XML Synset Parser for Serbian WordNet synsets.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Set
from pathlib import Path
import re
import logging
from dataclasses import dataclass

# POS normalization utilities (Serbian <-> English)
try:
    from ..utils.language_utils import LanguageUtils
except Exception:
    # Fallback import path when running outside package context
    from wordnet_autotranslate.utils.language_utils import LanguageUtils

# Set up logger
logger = logging.getLogger(__name__)

# Constants for XML element names
class XmlElements:
    """XML element name constants."""
    SYNSET = 'SYNSET'
    ID = 'ID'
    POS = 'POS'
    DEF = 'DEF'
    SYNONYM = 'SYNONYM'
    LITERAL = 'LITERAL'
    SENSE = 'SENSE'
    LNOTE = 'LNOTE'
    ILR = 'ILR'
    TYPE = 'TYPE'
    BCS = 'BCS'
    NL = 'NL'
    STAMP = 'STAMP'
    SUMO = 'SUMO'
    SENTIMENT = 'SENTIMENT'
    POSITIVE = 'POSITIVE'
    NEGATIVE = 'NEGATIVE'
    DOMAIN = 'DOMAIN'
    USAGE = 'USAGE'

# Constants for patterns and defaults
ENGLISH_ID_PATTERN = r'(ENG30-\d+-[a-z])'
DEFAULT_RELATION_TYPE = "related"
DEBUG_SYNSET_ID = "ENG30-08621598-n"


@dataclass
class Synset:
    """Represents a WordNet synset from XML."""
    id: str
    pos: str
    synonyms: List[Dict[str, str]]  # [{'literal': str, 'sense': str, 'lnote': str}]
    definition: str
    bcs: str
    ilr: List[Dict[str, str]]  # [{'target': str, 'type': str}]
    nl: str
    stamp: str
    sumo: Optional[Dict[str, str]] = None  # {'concept': str, 'type': str}
    sentiment: Optional[Dict[str, float]] = None  # {'positive': float, 'negative': float}
    domain: Optional[str] = None
    usage: Optional[str] = None  # Usage example


class XmlSynsetParser:
    """Parser for Serbian WordNet synsets in XML format."""
    
    def __init__(self):
        """Initialize the parser."""
        self.synsets: Dict[str, Synset] = {}
        self.english_links: Dict[str, List[Synset]] = {}  # Map English IDs to Serbian synsets
        self._search_cache: Dict[str, List[Synset]] = {}  # Cache for search results
        
    def parse_xml_file(self, xml_file_path: str) -> List[Synset]:
        """
        Parse XML file containing Serbian synsets.
        
        Args:
            xml_file_path: Path to XML file
            
        Returns:
            List of parsed synsets
            
        Raises:
            ET.ParseError: If XML parsing fails
            FileNotFoundError: If file doesn't exist
        """
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            return self._parse_synsets_from_root(root)
            
        except ET.ParseError as e:
            logger.error(f"Error parsing XML file {xml_file_path}: {e}")
            raise
        except FileNotFoundError:
            logger.error(f"XML file not found: {xml_file_path}")
            raise
    
    def parse_xml_string(self, xml_content: str) -> List[Synset]:
        """
        Parse XML content from string.
        
        Args:
            xml_content: XML content as string
            
        Returns:
            List of parsed synsets
        """
        try:
            root = self._prepare_xml_root(xml_content)
            synsets = self._parse_synsets_from_root(root)
            
            logger.debug(f"Parsed {len(synsets)} synsets total")
            
            return synsets
            
        except ET.ParseError as e:
            logger.error(f"Error parsing XML content: {e}")
            return []
    
    def _prepare_xml_root(self, xml_content: str) -> ET.Element:
        """Prepare XML content and return root element."""
        # Clean up the XML content - remove leading/trailing whitespace
        xml_content = xml_content.strip()
        
        # Wrap content in root element if not already wrapped
        if not xml_content.startswith('<root>'):
            xml_content = f"<root>{xml_content}</root>"
            
        return ET.fromstring(xml_content)
    
    def _parse_synsets_from_root(self, root: ET.Element) -> List[Synset]:
        """Parse synsets from XML root element."""
        synsets = []
        parsed_count = 0
        
        for synset_elem in root.findall(f'.//{XmlElements.SYNSET}'):
            synset = self._parse_synset_element(synset_elem)
            if synset:
                synsets.append(synset)
                self._store_synset(synset)
                parsed_count += 1
                
                # Debug logging for specific synset
                if synset.id == DEBUG_SYNSET_ID:
                    logger.debug(f"Successfully stored synset {synset.id} in parser.synsets")
                    logger.debug(f"Can retrieve it: {self.synsets.get(synset.id) is not None}")
            else:
                logger.warning("Failed to parse synset element")
        
        logger.debug(f"Parsed {parsed_count} synsets total")
        return synsets
    
    def _store_synset(self, synset: Synset) -> None:
        """Store synset in internal dictionaries."""
        self.synsets[synset.id] = synset
        
        # Index English links
        english_id = self._extract_english_id(synset.id)
        if english_id:
            # Normalize POS in ENG30 id for consistent English lookups.
            # Serbian XML may use '-b' for adverbs; WordNet uses '-r'.
            if english_id.endswith('-b'):
                english_id = english_id[:-1] + 'r'
            if english_id not in self.english_links:
                self.english_links[english_id] = []
            self.english_links[english_id].append(synset)
    
    def _parse_synset_element(self, synset_elem: ET.Element) -> Optional[Synset]:
        """Parse a single SYNSET XML element."""
        try:
            # Parse required fields
            synset_id, pos, definition = self._parse_required_fields(synset_elem)
            if not synset_id:
                return None
                
            # Debug logging for specific synset
            if synset_id == DEBUG_SYNSET_ID:
                logger.info(f"Parsing target synset: {synset_id}")
                logger.debug(f"Parsing target synset: {synset_id}")
            
            # Parse all components
            synonyms = self._parse_synonyms(synset_elem)
            ilr_relations = self._parse_ilr_relations(synset_elem)
            bcs = self._get_element_text(synset_elem, XmlElements.BCS)
            nl = self._get_element_text(synset_elem, XmlElements.NL)
            stamp = self._get_element_text(synset_elem, XmlElements.STAMP)
            sumo = self._parse_sumo(synset_elem)
            sentiment = self._parse_sentiment(synset_elem)
            domain = self._get_element_text(synset_elem, XmlElements.DOMAIN)
            usage = self._get_element_text(synset_elem, XmlElements.USAGE)
            
            return Synset(
                id=synset_id,
                pos=pos,
                synonyms=synonyms,
                definition=definition,
                bcs=bcs,
                ilr=ilr_relations,
                nl=nl,
                stamp=stamp,
                sumo=sumo,
                sentiment=sentiment,
                domain=domain,
                usage=usage
            )
            
        except Exception as e:
            logger.error(f"Error parsing synset element: {e}")
            return None
    
    def _parse_required_fields(self, synset_elem: ET.Element) -> tuple[str, str, str]:
        """Parse required fields from synset element."""
        id_elem = synset_elem.find(XmlElements.ID)
        pos_elem = synset_elem.find(XmlElements.POS)
        def_elem = synset_elem.find(XmlElements.DEF)
        
        if id_elem is None or pos_elem is None:
            logger.warning(f"Missing required fields: ID={id_elem}, POS={pos_elem}")
            return "", "", ""
            
        synset_id = self._get_stripped_text(id_elem)
        pos = self._get_stripped_text(pos_elem)
        definition = self._get_stripped_text(def_elem) if def_elem is not None else ""
        
        if not synset_id:
            logger.warning("Empty synset ID found")
            return "", "", ""
            
        return synset_id, pos, definition
    
    def _get_stripped_text(self, element: Optional[ET.Element]) -> str:
        """Get stripped text from XML element, handling None cases."""
        return element.text.strip() if element is not None and element.text else ""
    
    def _get_element_text(self, parent: ET.Element, tag: str) -> str:
        """Get text content from child element."""
        elem = parent.find(tag)
        return self._get_stripped_text(elem)
    
    def _parse_synonyms(self, synset_elem: ET.Element) -> List[Dict[str, str]]:
        """Parse synonyms from synset element."""
        synonyms = []
        synonym_elem = synset_elem.find(XmlElements.SYNONYM)
        
        if synonym_elem is not None:
            for literal_elem in synonym_elem.findall(XmlElements.LITERAL):
                if literal_elem.text:
                    literal_data = {'literal': literal_elem.text}
                    
                    # Parse SENSE and LNOTE if present
                    sense_text = self._get_element_text(literal_elem, XmlElements.SENSE)
                    if sense_text:
                        literal_data['sense'] = sense_text
                        
                    lnote_text = self._get_element_text(literal_elem, XmlElements.LNOTE)
                    if lnote_text:
                        literal_data['lnote'] = lnote_text
                        
                    synonyms.append(literal_data)
        
        return synonyms
    
    def _parse_ilr_relations(self, synset_elem: ET.Element) -> List[Dict[str, str]]:
        """Parse ILR (Inter-Lingual Relations) from synset element."""
        ilr_relations = []
        
        for ilr_elem in synset_elem.findall(XmlElements.ILR):
            if ilr_elem.text:
                target = ilr_elem.text.strip()
                rel_type = self._get_element_text(ilr_elem, XmlElements.TYPE) or DEFAULT_RELATION_TYPE
                ilr_relations.append({'target': target, 'type': rel_type})
        
        return ilr_relations
    
    def _parse_sumo(self, synset_elem: ET.Element) -> Optional[Dict[str, str]]:
        """Parse SUMO information from synset element."""
        sumo_elem = synset_elem.find(XmlElements.SUMO)
        if sumo_elem is not None and sumo_elem.text:
            sumo_text = sumo_elem.text.strip()
            sumo_type = self._get_element_text(sumo_elem, XmlElements.TYPE)
            return {'concept': sumo_text, 'type': sumo_type}
        return None
    
    def _parse_sentiment(self, synset_elem: ET.Element) -> Optional[Dict[str, float]]:
        """Parse sentiment information from synset element."""
        sentiment_elem = synset_elem.find(XmlElements.SENTIMENT)
        if sentiment_elem is None:
            return None
            
        pos_elem = sentiment_elem.find(XmlElements.POSITIVE)
        neg_elem = sentiment_elem.find(XmlElements.NEGATIVE)
        
        if pos_elem is not None and neg_elem is not None:
            try:
                positive = self._parse_float_with_comma(pos_elem.text) if pos_elem.text else 0.0
                negative = self._parse_float_with_comma(neg_elem.text) if neg_elem.text else 0.0
                return {'positive': positive, 'negative': negative}
            except ValueError:
                logger.warning("Failed to parse sentiment values")
                return None
        
        return None
    
    def _parse_float_with_comma(self, text: str) -> float:
        """Parse float value, handling comma as decimal separator."""
        return float(text.replace(',', '.'))
    
    def _extract_english_id(self, synset_id: str) -> Optional[str]:
        """Extract English WordNet ID from synset ID if present."""
        match = re.match(ENGLISH_ID_PATTERN, synset_id)
        if not match:
            return None
        eng_id = match.group(1)
        # Normalize Serbian 'b' (adverb) to English 'r' for downstream use
        if eng_id.endswith('-b'):
            return eng_id[:-1] + 'r'
        return eng_id
    
    def get_synset_by_id(self, synset_id: str) -> Optional[Synset]:
        """Get synset by ID."""
        result = self.synsets.get(synset_id)
        
        # Debug logging for specific synset
        if synset_id == DEBUG_SYNSET_ID:
            logger.debug(f"Looking up synset {synset_id}")
            logger.debug(f"Found in parser.synsets: {result is not None}")
            logger.debug(f"Total synsets in parser: {len(self.synsets)}")
            logger.debug(f"Sample synset IDs: {list(self.synsets.keys())[:5]}")
            
        return result
    
    def get_related_synsets(self, synset: Synset) -> List[Synset]:
        """
        Get synsets related through ILR relations.
        
        Args:
            synset: Source synset
            
        Returns:
            List of related synsets
        """
        related = []
        for relation in synset.ilr:
            target_id = relation['target']
            target_synset = self.synsets.get(target_id)
            if target_synset:
                related.append(target_synset)
        return related
    
    def get_english_linked_synsets(self, english_id: str) -> List[Synset]:
        """
        Get Serbian synsets linked to an English WordNet ID.
        
        Args:
            english_id: English WordNet ID
            
        Returns:
            List of linked Serbian synsets
        """
        return self.english_links.get(english_id, [])
    
    def search_synsets(self, query: str, limit: int = 20) -> List[Synset]:
        """
        Search synsets by query in definition, synonyms, or usage examples with caching.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching synsets
        """
        if not query:
            return []
            
        query_lower = query.lower()
        
        # Create cache key from query and limit
        cache_key = f"{query_lower}:{limit}"
        
        # Check cache first
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        results = []
        
        for synset in self.synsets.values():
            if self._synset_matches_query(synset, query_lower):
                results.append(synset)
                if len(results) >= limit:
                    break
        
        # Cache the results
        self._search_cache[cache_key] = results
        
        return results
    
    def _synset_matches_query(self, synset: Synset, query_lower: str) -> bool:
        """Check if synset matches the search query."""
        # Search in definition
        if query_lower in synset.definition.lower():
            return True
            
        # Search in synonyms
        for synonym in synset.synonyms:
            if query_lower in synonym.get('literal', '').lower():
                return True
        
        # Search in usage examples
        if synset.usage and query_lower in synset.usage.lower():
            return True
            
        return False
    
    def get_synsets_by_pos(self, pos: str) -> List[Synset]:
        """
        Get all synsets with specific part of speech.
        
        Args:
            pos: Part of speech to filter by
            
        Returns:
            List of synsets with matching POS
        """
        return [synset for synset in self.synsets.values() if synset.pos == pos]
    
    def get_all_synsets(self) -> List[Synset]:
        """
        Get all loaded synsets.
        
        Returns:
            List of all synsets
        """
        return list(self.synsets.values())
    
    def clear(self) -> None:
        """Clear all loaded synsets and caches."""
        self.synsets.clear()
        self.english_links.clear()
        self._search_cache.clear()
    
    def get_synset_count(self) -> int:
        """Get the total number of loaded synsets."""
        return len(self.synsets)
    
    def get_english_links_count(self) -> int:
        """Get the total number of English links."""
        return len(self.english_links)