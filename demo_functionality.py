#!/usr/bin/env python3
"""
Demonstration script for the Serbian WordNet Synset Browser functionality.
This script shows how the key components work without the GUI.
"""

import sys
from pathlib import Path

# Add src to path for importing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from wordnet_autotranslate.models.xml_synset_parser import XmlSynsetParser, Synset
from wordnet_autotranslate.models.synset_handler import SynsetHandler


def demo_xml_parsing():
    """Demo XML parsing functionality."""
    print("=== Serbian WordNet XML Parsing Demo ===")
    
    parser = XmlSynsetParser()
    
    # Sample XML from the problem statement
    sample_xml = """<root>
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
      <ILR>ENG30-03528100-n<TYPE>hyponym</TYPE></ILR>
      <NL>yes</NL>
      <STAMP>Cvetana 20.7.2006. 00.00.00</STAMP>
      <SUMO>StationaryArtifact<TYPE>+</TYPE></SUMO>
      <SENTIMENT>
         <POSITIVE>0,00000</POSITIVE>
         <NEGATIVE>0,00000</NEGATIVE>
      </SENTIMENT>
      <DOMAIN>factotum</DOMAIN>
   </SYNSET>
   <SYNSET>
      <ID>ENG30-07810907-n</ID>
      <POS>n</POS>
      <SYNONYM>
         <LITERAL>začin<SENSE>1x</SENSE><LNOTE>N1</LNOTE></LITERAL>
      </SYNONYM>
      <DEF>pripremljeni dodatak jelu za poboljšanje ukusa</DEF>
      <BCS>1</BCS>
      <ILR>ENG30-07809368-n<TYPE>hypernym</TYPE></ILR>
      <ILR>ENG30-07829412-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07828987-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07822197-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07819480-n<TYPE>hyponym</TYPE></ILR>
      <ILR>SRP-00468874<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07582441-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07582609-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07825972-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07823105-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07824383-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07857356-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07856270-n<TYPE>hyponym</TYPE></ILR>
      <ILR>ENG30-07824502-n<TYPE>hyponym</TYPE></ILR>
      <NL>yes</NL>
      <STAMP>Cvetana</STAMP>
      <SUMO>Food<TYPE>+</TYPE></SUMO>
      <SENTIMENT>
         <POSITIVE>0,00000</POSITIVE>
         <NEGATIVE>0,25000</NEGATIVE>
      </SENTIMENT>
      <DOMAIN>gastronomy</DOMAIN>
   </SYNSET>
   <SYNSET>
      <ID>ENG30-00721431-n</ID>
      <POS>n</POS>
      <SYNONYM>
         <LITERAL>mesto<SENSE>z</SENSE><LNOTE>N300</LNOTE></LITERAL>
      </SYNONYM>
      <DEF>u nečijim prilikama, mogućnostima</DEF>
      <BCS>1</BCS>
      <ILR>ENG30-00720565-n<TYPE>hypernym</TYPE></ILR>
      <NL>yes</NL>
      <STAMP>Cvetana</STAMP>
      <SUMO>IntentionalProcess<TYPE>+</TYPE></SUMO>
      <SENTIMENT>
         <POSITIVE>0,00000</POSITIVE>
         <NEGATIVE>0,00000</NEGATIVE>
      </SENTIMENT>
      <DOMAIN>factotum</DOMAIN>
   </SYNSET>
</root>"""
    
    # Parse the XML
    synsets = parser.parse_xml_string(sample_xml)
    print(f"✅ Successfully parsed {len(synsets)} Serbian synsets")
    
    # Display synset information
    for i, synset in enumerate(synsets, 1):
        print(f"\n📖 Synset {i}: {synset.id}")
        print(f"   Part of Speech: {synset.pos}")
        print(f"   Synonyms: {[s.get('literal', '') for s in synset.synonyms]}")
        print(f"   Definition: {synset.definition}")
        print(f"   Relations: {len(synset.ilr)} hyperlinks")
        if synset.domain:
            print(f"   Domain: {synset.domain}")
    
    return parser, synsets


def demo_hyperlink_navigation(parser, synsets):
    """Demo hyperlink navigation between synsets."""
    print("\n=== Hyperlink Navigation Demo ===")
    
    # Take first synset and show its relations
    synset = synsets[0]
    print(f"\n🔗 Navigating from synset: {synset.id}")
    print(f"   Definition: {synset.definition}")
    
    print(f"\n   Related synsets ({len(synset.ilr)} relations):")
    for relation in synset.ilr:
        target_id = relation['target']
        rel_type = relation['type']
        
        # Check if we have the target synset loaded
        target_synset = parser.get_synset_by_id(target_id)
        
        if target_synset:
            print(f"   → {rel_type}: {target_id} ✅ (loaded)")
            print(f"     Definition: {target_synset.definition}")
        else:
            print(f"   → {rel_type}: {target_id} ⚠️ (not in current dataset)")


def demo_search_functionality(parser):
    """Demo search functionality."""
    print("\n=== Search Functionality Demo ===")
    
    search_terms = ["ustanova", "začin", "mesto", "zgrada"]
    
    for term in search_terms:
        results = parser.search_synsets(term, limit=5)
        print(f"\n🔍 Search for '{term}': {len(results)} results")
        
        for result in results:
            synonyms = [s.get('literal', '') for s in result.synonyms]
            print(f"   • {result.id}: {', '.join(synonyms)}")
            print(f"     {result.definition[:80]}...")


def demo_english_serbian_pairing():
    """Demo English-Serbian synset pairing."""
    print("\n=== English-Serbian Pairing Demo ===")
    
    # Initialize English WordNet handler
    try:
        english_handler = SynsetHandler()
        print("✅ English WordNet handler initialized")
        
        # Example pairing - institution/ustanova
        english_synsets = english_handler.search_synsets("institution", limit=3)
        
        if english_synsets:
            print(f"\n🇺🇸 English synsets for 'institution': {len(english_synsets)} found")
            
            for i, eng_synset in enumerate(english_synsets, 1):
                print(f"   {i}. {eng_synset['name']}")
                print(f"      Definition: {eng_synset['definition']}")
                print(f"      Lemmas: {', '.join(eng_synset['lemmas'])}")
                
                # Show how this could pair with Serbian synset
                if i == 1:  # First result
                    print(f"\n🔗 Potential pairing:")
                    print(f"   🇷🇸 Serbian: ENG30-03574555-n (ustanova)")
                    print(f"      zgrada u kojoj se nalazi organizaciona jedinica...")
                    print(f"   🇺🇸 English: {eng_synset['name']}")
                    print(f"      {eng_synset['definition']}")
                    print(f"   ✅ This would be a good translation pair!")
        else:
            print("⚠️ No English synsets found for 'institution'")
            
    except Exception as e:
        print(f"⚠️ English WordNet not available: {e}")
        print("   (This is normal if NLTK WordNet data is not downloaded)")


def demo_export_format():
    """Demo export format for training data."""
    print("\n=== Export Format Demo ===")
    
    # Example of what the exported JSON would look like
    sample_pairs = [
        {
            "serbian_id": "ENG30-03574555-n",
            "serbian_synonyms": ["ustanova"],
            "serbian_definition": "zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja",
            "english_id": "institution.n.01",
            "english_definition": "a building that houses an administrative unit of some government",
            "english_lemmas": ["institution", "establishment"]
        },
        {
            "serbian_id": "ENG30-07810907-n",
            "serbian_synonyms": ["začin"],
            "serbian_definition": "pripremljeni dodatak jelu za poboljšanje ukusa",
            "english_id": "spice.n.01",
            "english_definition": "aromatic substances of vegetable origin used as a preservative",
            "english_lemmas": ["spice"]
        }
    ]
    
    export_data = {
        "pairs": sample_pairs,
        "metadata": {
            "total_pairs": len(sample_pairs),
            "created_by": "Serbian WordNet Synset Browser",
            "format_version": "1.0",
            "description": "Manually selected Serbian-English synset pairs for translation training"
        }
    }
    
    print("📊 Sample export format:")
    import json
    print(json.dumps(export_data, indent=2, ensure_ascii=False))


def main():
    """Run the complete demonstration."""
    print("🚀 Serbian WordNet Synset Browser - Functionality Demo")
    print("=" * 60)
    
    try:
        # Demo XML parsing
        parser, synsets = demo_xml_parsing()
        
        # Demo hyperlink navigation
        demo_hyperlink_navigation(parser, synsets)
        
        # Demo search
        demo_search_functionality(parser)
        
        # Demo English-Serbian pairing
        demo_english_serbian_pairing()
        
        # Demo export format
        demo_export_format()
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("\n📚 To run the full GUI:")
        print("   python launch_gui.py")
        print("   or")
        print("   streamlit run src/wordnet_autotranslate/gui/synset_browser.py")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()