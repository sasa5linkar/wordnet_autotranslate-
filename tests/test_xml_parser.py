"""
Tests for XML Synset Parser.
"""

import pytest
import sys
import textwrap
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wordnet_autotranslate.models.xml_synset_parser import XmlSynsetParser, Synset
from wordnet_autotranslate.utils.language_utils import LanguageUtils


def test_xml_synset_parser_init():
    """Test XmlSynsetParser initialization."""
    parser = XmlSynsetParser()
    assert parser.synsets == {}
    assert parser.english_links == {}


def test_parse_sample_xml():
    """Test parsing sample XML content."""
    parser = XmlSynsetParser()
    
    sample_xml = textwrap.dedent("""
    <root>
       <SYNSET>
          <ID>ENG30-03574555-n</ID>
          <POS>n</POS>
          <SYNONYM>
             <LITERAL>ustanova<SENSE>1y</SENSE><LNOTE>N600</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja</DEF>
          <BCS>1</BCS>
          <ILR>ENG30-03297735-n<TYPE>hypernym</TYPE></ILR>
          <ILR>ENG30-03907654-n<TYPE>hyponym</TYPE></ILR>
          <NL>yes</NL>
          <STAMP>Cvetana 20.7.2006. 00.00.00</STAMP>
          <SUMO>StationaryArtifact<TYPE>+</TYPE></SUMO>
          <SENTIMENT>
             <POSITIVE>0,00000</POSITIVE>
             <NEGATIVE>0,00000</NEGATIVE>
          </SENTIMENT>
          <DOMAIN>factotum</DOMAIN>
       </SYNSET>
    </root>""").strip()
    
    synsets = parser.parse_xml_string(sample_xml)
    
    assert len(synsets) == 1
    synset = synsets[0]
    
    assert synset.id == "ENG30-03574555-n"
    assert synset.pos == "n"
    assert len(synset.synonyms) == 1
    assert synset.synonyms[0]['literal'] == "ustanova"
    assert synset.synonyms[0]['sense'] == "1y"
    assert synset.synonyms[0]['lnote'] == "N600"
    assert synset.definition == "zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja"
    assert synset.bcs == "1"
    assert len(synset.ilr) == 2
    assert synset.ilr[0]['target'] == "ENG30-03297735-n"
    assert synset.ilr[0]['type'] == "hypernym"
    assert synset.nl == "yes"
    assert synset.domain == "factotum"
    assert synset.sentiment['positive'] == 0.0
    assert synset.sentiment['negative'] == 0.0


def test_parse_multiple_synsets():
    """Test parsing multiple synsets."""
    parser = XmlSynsetParser()
    
    sample_xml = textwrap.dedent("""
    <root>
       <SYNSET>
          <ID>ENG30-03574555-n</ID>
          <POS>n</POS>
          <SYNONYM>
             <LITERAL>ustanova<SENSE>1y</SENSE><LNOTE>N600</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja</DEF>
          <BCS>1</BCS>
          <NL>yes</NL>
       </SYNSET>
       <SYNSET>
          <ID>ENG30-07810907-n</ID>
          <POS>n</POS>
          <SYNONYM>
             <LITERAL>začin<SENSE>1x</SENSE><LNOTE>N1</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>pripremljeni dodatak jelu za poboljšanje ukusa</DEF>
          <BCS>1</BCS>
          <NL>yes</NL>
       </SYNSET>
    </root>""").strip()
    
    synsets = parser.parse_xml_string(sample_xml)
    
    assert len(synsets) == 2
    assert synsets[0].id == "ENG30-03574555-n"
    assert synsets[1].id == "ENG30-07810907-n"
    assert synsets[0].synonyms[0]['literal'] == "ustanova"
    assert synsets[1].synonyms[0]['literal'] == "začin"


def test_english_id_extraction():
   """Test English ID extraction."""
   parser = XmlSynsetParser()

   # Test valid English ID
   english_id = parser._extract_english_id("ENG30-03574555-n")
   assert english_id == "ENG30-03574555-n"

   # Serbian-style adverb POS should normalize to English 'r'
   english_id_adv = parser._extract_english_id("ENG30-00001740-b")
   assert english_id_adv == "ENG30-00001740-r"

   # Test non-English ID
   english_id = parser._extract_english_id("SRP-00468874")
   assert english_id is None


def test_pos_normalization_helpers():
   """Ensure POS normalization between Serbian and English is correct."""
   # Serbian -> English
   assert LanguageUtils.normalize_pos_for_english('b') == 'r'
   assert LanguageUtils.normalize_pos_for_english('n') == 'n'
   # English -> Serbian
   assert LanguageUtils.normalize_pos_for_serbian('r') == 'b'
   assert LanguageUtils.normalize_pos_for_serbian('a') == 'a'


def test_search_synsets():
    """Test synset searching functionality."""
    parser = XmlSynsetParser()
    
    sample_xml = textwrap.dedent("""
    <root>
       <SYNSET>
          <ID>ENG30-03574555-n</ID>
          <POS>n</POS>
          <SYNONYM>
             <LITERAL>ustanova<SENSE>1y</SENSE><LNOTE>N600</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja</DEF>
          <BCS>1</BCS>
       </SYNSET>
       <SYNSET>
          <ID>ENG30-07810907-n</ID>
          <POS>n</POS>
          <SYNONYM>
             <LITERAL>začin<SENSE>1x</SENSE><LNOTE>N1</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>pripremljeni dodatak jelu za poboljšanje ukusa</DEF>
          <BCS>1</BCS>
       </SYNSET>
    </root>""").strip()
    
    synsets = parser.parse_xml_string(sample_xml)
    
    # Search by definition
    results = parser.search_synsets("zgrada")
    assert len(results) == 1
    assert results[0].id == "ENG30-03574555-n"
    
    # Search by synonym
    results = parser.search_synsets("začin")
    assert len(results) == 1
    assert results[0].id == "ENG30-07810907-n"
    
    # Search with no results
    results = parser.search_synsets("nonexistent")
    assert len(results) == 0


def test_get_synsets_by_pos():
    """Test filtering synsets by part of speech."""
    parser = XmlSynsetParser()
    
    sample_xml = textwrap.dedent("""
    <root>
       <SYNSET>
          <ID>ENG30-03574555-n</ID>
          <POS>n</POS>
          <SYNONYM>
             <LITERAL>ustanova<SENSE>1y</SENSE><LNOTE>N600</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>zgrada</DEF>
          <BCS>1</BCS>
       </SYNSET>
       <SYNSET>
          <ID>ENG30-12345678-v</ID>
          <POS>v</POS>
          <SYNONYM>
             <LITERAL>raditi<SENSE>1</SENSE><LNOTE>V1</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>obavljati posao</DEF>
          <BCS>1</BCS>
       </SYNSET>
    </root>""").strip()
    
    synsets = parser.parse_xml_string(sample_xml)
    
    # Get nouns
    nouns = parser.get_synsets_by_pos('n')
    assert len(nouns) == 1
    assert nouns[0].id == "ENG30-03574555-n"
    
    # Get verbs
    verbs = parser.get_synsets_by_pos('v')
    assert len(verbs) == 1
    assert verbs[0].id == "ENG30-12345678-v"


def test_clear():
    """Test clearing parser data."""
    parser = XmlSynsetParser()
    
    sample_xml = textwrap.dedent("""
    <root>
       <SYNSET>
          <ID>ENG30-03574555-n</ID>
          <POS>n</POS>
          <SYNONYM>
             <LITERAL>ustanova<SENSE>1y</SENSE><LNOTE>N600</LNOTE></LITERAL>
          </SYNONYM>
          <DEF>zgrada</DEF>
          <BCS>1</BCS>
       </SYNSET>
    </root>""").strip()
    
    synsets = parser.parse_xml_string(sample_xml)
    assert len(synsets) == 1
    assert len(parser.synsets) == 1
    
    parser.clear()
    assert len(parser.synsets) == 0
    assert len(parser.english_links) == 0


if __name__ == "__main__":
    pytest.main([__file__])