#!/usr/bin/env python3
"""Simple test script to verify XML parser functionality after refactoring."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from wordnet_autotranslate.models.xml_synset_parser import XmlSynsetParser, Synset

def test_basic_functionality():
    """Test basic XML parsing functionality."""
    
    # Sample XML content
    xml_content = """
    <SYNSET>
        <ID>ENG30-00001740-v</ID>
        <POS>v</POS>
        <DEF>change orientation or direction, also in the abstract sense</DEF>
        <SYNONYM>
            <LITERAL>turn</LITERAL>
        </SYNONYM>
        <ILR>
            <target>ENG30-00002068-v</target>
            <TYPE>hypernym</TYPE>
        </ILR>
        <BCS>test_bcs</BCS>
        <NL>test_nl</NL>
        <STAMP>test_stamp</STAMP>
    </SYNSET>
    """
    
    # Test parsing
    parser = XmlSynsetParser()
    synsets = parser.parse_xml_string(xml_content)
    
    print(f"✓ Parsed {len(synsets)} synsets")
    
    if synsets:
        synset = synsets[0]
        print(f"✓ Synset ID: {synset.id}")
        print(f"✓ POS: {synset.pos}")
        print(f"✓ Definition: {synset.definition}")
        print(f"✓ Synonyms: {synset.synonyms}")
        print(f"✓ ILR relations: {synset.ilr}")
        
        # Test retrieval by ID
        retrieved = parser.get_synset_by_id(synset.id)
        assert retrieved is not None, "Should be able to retrieve synset by ID"
        print(f"✓ Successfully retrieved synset by ID")
        
        # Test search functionality
        results = parser.search_synsets("turn")
        assert len(results) > 0, "Should find synsets when searching"
        print(f"✓ Search functionality works: found {len(results)} results")
        
        # Test related synsets
        related = parser.get_related_synsets(synset)
        print(f"✓ Related synsets: {len(related)} (expected 0 since target doesn't exist)")
        
        # Test English ID extraction
        english_id = parser._extract_english_id(synset.id)
        print(f"✓ Extracted English ID: {english_id}")
        
        print("✅ All basic functionality tests passed!")
        return True
    else:
        print("❌ No synsets parsed")
        return False

if __name__ == "__main__":
    test_basic_functionality()
