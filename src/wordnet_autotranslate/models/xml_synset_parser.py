"""
XML Synset Parser for Serbian WordNet synsets.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Set
from pathlib import Path
import re
from dataclasses import dataclass


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


class XmlSynsetParser:
    """Parser for Serbian WordNet synsets in XML format."""
    
    def __init__(self):
        """Initialize the parser."""
        self.synsets = {}
        self.english_links = {}  # Map English IDs to Serbian synsets
        
    def parse_xml_file(self, xml_file_path: str) -> List[Synset]:
        """
        Parse XML file containing Serbian synsets.
        
        Args:
            xml_file_path: Path to XML file
            
        Returns:
            List of parsed synsets
        """
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            synsets = []
            for synset_elem in root.findall('.//SYNSET'):
                synset = self._parse_synset_element(synset_elem)
                if synset:
                    synsets.append(synset)
                    self.synsets[synset.id] = synset
                    
                    # Index English links
                    english_id = self._extract_english_id(synset.id)
                    if english_id:
                        if english_id not in self.english_links:
                            self.english_links[english_id] = []
                        self.english_links[english_id].append(synset)
            
            return synsets
            
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
            # Clean up the XML content - remove leading/trailing whitespace
            xml_content = xml_content.strip()
            
            # Wrap content in root element if not already wrapped
            if not xml_content.startswith('<root>'):
                xml_content = f"<root>{xml_content}</root>"
                
            root = ET.fromstring(xml_content)
            
            synsets = []
            for synset_elem in root.findall('.//SYNSET'):
                synset = self._parse_synset_element(synset_elem)
                if synset:
                    synsets.append(synset)
                    self.synsets[synset.id] = synset
                    
                    # Index English links
                    english_id = self._extract_english_id(synset.id)
                    if english_id:
                        if english_id not in self.english_links:
                            self.english_links[english_id] = []
                        self.english_links[english_id].append(synset)
            
            return synsets
            
        except ET.ParseError as e:
            print(f"Error parsing XML content: {e}")
            return []
    
    def _parse_synset_element(self, synset_elem) -> Optional[Synset]:
        """Parse a single SYNSET XML element."""
        try:
            # Required fields
            id_elem = synset_elem.find('ID')
            pos_elem = synset_elem.find('POS')
            def_elem = synset_elem.find('DEF')
            
            if id_elem is None or pos_elem is None:
                return None
                
            synset_id = id_elem.text.strip() if id_elem.text else ""
            pos = pos_elem.text.strip() if pos_elem.text else ""
            definition = def_elem.text.strip() if def_elem is not None and def_elem.text else ""
            
            # Parse synonyms
            synonyms = []
            synonym_elem = synset_elem.find('SYNONYM')
            if synonym_elem is not None:
                for literal_elem in synonym_elem.findall('LITERAL'):
                    if literal_elem.text:
                        literal_data = {'literal': literal_elem.text}
                        
                        # Parse SENSE and LNOTE if present
                        sense_elem = literal_elem.find('SENSE')
                        if sense_elem is not None and sense_elem.text:
                            literal_data['sense'] = sense_elem.text
                            
                        lnote_elem = literal_elem.find('LNOTE')
                        if lnote_elem is not None and lnote_elem.text:
                            literal_data['lnote'] = lnote_elem.text
                            
                        synonyms.append(literal_data)
            
            # Parse ILR (Inter-Lingual Relations)
            ilr_relations = []
            for ilr_elem in synset_elem.findall('ILR'):
                if ilr_elem.text:
                    target = ilr_elem.text.strip()
                    type_elem = ilr_elem.find('TYPE')
                    rel_type = type_elem.text.strip() if type_elem is not None and type_elem.text else "related"
                    ilr_relations.append({'target': target, 'type': rel_type})
            
            # Optional fields
            bcs_elem = synset_elem.find('BCS')
            bcs = bcs_elem.text.strip() if bcs_elem is not None and bcs_elem.text else ""
            
            nl_elem = synset_elem.find('NL')
            nl = nl_elem.text.strip() if nl_elem is not None and nl_elem.text else ""
            
            stamp_elem = synset_elem.find('STAMP')
            stamp = stamp_elem.text.strip() if stamp_elem is not None and stamp_elem.text else ""
            
            # Parse SUMO if present
            sumo = None
            sumo_elem = synset_elem.find('SUMO')
            if sumo_elem is not None and sumo_elem.text:
                sumo_text = sumo_elem.text.strip()
                type_elem = sumo_elem.find('TYPE')
                sumo_type = type_elem.text.strip() if type_elem is not None and type_elem.text else ""
                sumo = {'concept': sumo_text, 'type': sumo_type}
            
            # Parse SENTIMENT if present
            sentiment = None
            sentiment_elem = synset_elem.find('SENTIMENT')
            if sentiment_elem is not None:
                pos_elem = sentiment_elem.find('POSITIVE')
                neg_elem = sentiment_elem.find('NEGATIVE')
                
                if pos_elem is not None and neg_elem is not None:
                    try:
                        positive = float(pos_elem.text.replace(',', '.')) if pos_elem.text else 0.0
                        negative = float(neg_elem.text.replace(',', '.')) if neg_elem.text else 0.0
                        sentiment = {'positive': positive, 'negative': negative}
                    except ValueError:
                        sentiment = None
            
            # Parse DOMAIN if present
            domain = None
            domain_elem = synset_elem.find('DOMAIN')
            if domain_elem is not None and domain_elem.text:
                domain = domain_elem.text.strip()
            
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
                domain=domain
            )
            
        except Exception as e:
            print(f"Error parsing synset element: {e}")
            return None
    
    def _extract_english_id(self, synset_id: str) -> Optional[str]:
        """Extract English WordNet ID from synset ID if present."""
        # Look for ENG30-xxxxxxxx-x pattern
        match = re.match(r'(ENG30-\d+-[a-z])', synset_id)
        if match:
            return match.group(1)
        return None
    
    def get_synset_by_id(self, synset_id: str) -> Optional[Synset]:
        """Get synset by ID."""
        return self.synsets.get(synset_id)
    
    def get_related_synsets(self, synset: Synset) -> List[Synset]:
        """Get synsets related through ILR relations."""
        related = []
        for relation in synset.ilr:
            target_id = relation['target']
            target_synset = self.synsets.get(target_id)
            if target_synset:
                related.append(target_synset)
        return related
    
    def get_english_linked_synsets(self, english_id: str) -> List[Synset]:
        """Get Serbian synsets linked to an English WordNet ID."""
        return self.english_links.get(english_id, [])
    
    def search_synsets(self, query: str, limit: int = 20) -> List[Synset]:
        """
        Search synsets by query in definition or synonyms.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching synsets
        """
        query_lower = query.lower()
        results = []
        
        for synset in self.synsets.values():
            # Search in definition
            if query_lower in synset.definition.lower():
                results.append(synset)
                continue
                
            # Search in synonyms
            for synonym in synset.synonyms:
                if query_lower in synonym.get('literal', '').lower():
                    results.append(synset)
                    break
            
            if len(results) >= limit:
                break
        
        return results[:limit]
    
    def get_synsets_by_pos(self, pos: str) -> List[Synset]:
        """Get all synsets with specific part of speech."""
        return [synset for synset in self.synsets.values() if synset.pos == pos]
    
    def get_all_synsets(self) -> List[Synset]:
        """Get all loaded synsets."""
        return list(self.synsets.values())
    
    def clear(self):
        """Clear all loaded synsets."""
        self.synsets.clear()
        self.english_links.clear()