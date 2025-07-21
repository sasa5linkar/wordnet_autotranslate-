"""
Streamlit GUI for browsing Serbian WordNet synsets and pairing with English synsets.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Optional, Set
from pathlib import Path
import json
import tempfile
import sys
import os

# Add src to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from wordnet_autotranslate.models.xml_synset_parser import XmlSynsetParser, Synset
from wordnet_autotranslate.models.synset_handler import SynsetHandler


class SynsetBrowserApp:
    """Main Streamlit application for synset browsing."""
    
    def __init__(self):
        """Initialize the application."""
        self.parser = XmlSynsetParser()
        self.synset_handler = SynsetHandler()
        self.selected_pairs = []  # List of (serbian_synset, english_synset) pairs
        
        # Initialize session state
        if 'current_synset' not in st.session_state:
            st.session_state.current_synset = None
        if 'selected_pairs' not in st.session_state:
            st.session_state.selected_pairs = []
        if 'loaded_synsets' not in st.session_state:
            st.session_state.loaded_synsets = []
    
    def run(self):
        """Run the main application."""
        st.set_page_config(
            page_title="Serbian WordNet Synset Browser",
            page_icon="📚",
            layout="wide"
        )
        
        st.title("📚 Serbian WordNet Synset Browser")
        st.markdown("Browse Serbian synsets and pair them with English synsets for translation training.")
        
        # Sidebar for navigation and controls
        with st.sidebar:
            self._render_sidebar()
        
        # Main content area
        if st.session_state.loaded_synsets:
            self._render_main_content()
        else:
            self._render_welcome_screen()
    
    def _render_sidebar(self):
        """Render the sidebar with navigation and controls."""
        st.header("🔧 Controls")
        
        # File upload section
        st.subheader("📁 Load Synsets")
        uploaded_file = st.file_uploader(
            "Upload XML file with Serbian synsets",
            type=['xml'],
            help="Upload an XML file containing Serbian WordNet synsets"
        )
        
        if uploaded_file is not None:
            if st.button("Load Synsets"):
                with st.spinner("Parsing XML file..."):
                    try:
                        content = uploaded_file.read().decode('utf-8')
                        synsets = self.parser.parse_xml_string(content)
                        st.session_state.loaded_synsets = synsets
                        st.success(f"Loaded {len(synsets)} synsets!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading file: {e}")
        
        # Sample data option
        st.subheader("📝 Use Sample Data")
        if st.button("Load Sample Serbian Synsets"):
            sample_xml = self._get_sample_xml()
            with st.spinner("Loading sample data..."):
                try:
                    synsets = self.parser.parse_xml_string(sample_xml)
                    st.session_state.loaded_synsets = synsets
                    st.success(f"Loaded {len(synsets)} sample synsets!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading sample data: {e}")
        
        # Search and navigation
        if st.session_state.loaded_synsets:
            st.subheader("🔍 Search")
            search_query = st.text_input("Search synsets", placeholder="Enter search term...")
            
            if search_query:
                search_results = self.parser.search_synsets(search_query, limit=10)
                if search_results:
                    st.write("Search Results:")
                    for i, synset in enumerate(search_results):
                        display_text = f"{synset.id}: {synset.synonyms[0]['literal'] if synset.synonyms else 'No synonyms'}"
                        if st.button(display_text, key=f"search_{i}"):
                            st.session_state.current_synset = synset
                            st.rerun()
                else:
                    st.write("No results found")
            
            # Part of speech filter
            st.subheader("🏷️ Filter by POS")
            pos_options = list(set(s.pos for s in st.session_state.loaded_synsets))
            selected_pos = st.selectbox("Part of Speech", ["All"] + sorted(pos_options))
            
            if selected_pos != "All":
                filtered_synsets = [s for s in st.session_state.loaded_synsets if s.pos == selected_pos]
                st.write(f"{len(filtered_synsets)} synsets with POS '{selected_pos}'")
        
        # Selected pairs management
        st.subheader("📋 Selected Pairs")
        st.write(f"Selected pairs: {len(st.session_state.selected_pairs)}")
        
        if st.session_state.selected_pairs:
            if st.button("📥 Export Pairs"):
                self._export_pairs()
            
            if st.button("🗑️ Clear All Pairs"):
                st.session_state.selected_pairs = []
                st.success("All pairs cleared!")
                st.rerun()
    
    def _render_welcome_screen(self):
        """Render the welcome screen when no synsets are loaded."""
        st.markdown("""
        ## Welcome to the Serbian WordNet Synset Browser!
        
        This tool helps you browse Serbian WordNet synsets and pair them with English synsets for translation training.
        
        ### How to get started:
        1. **Upload an XML file** containing Serbian synsets in the sidebar, or
        2. **Use sample data** to explore the functionality
        
        ### Features:
        - 🔍 **Search synsets** by definition or synonyms
        - 🔗 **Navigate hyperlinks** between related synsets
        - 🎯 **Pair Serbian and English synsets** for training data
        - 📊 **Export selected pairs** for machine learning
        
        ### XML Format Expected:
        The tool expects XML files with Serbian synsets in the format containing:
        - `<SYNSET>` elements with ID, POS, SYNONYM, DEF, and ILR relations
        - IDs in format like `ENG30-03574555-n` for English WordNet links
        - Inter-lingual relations for hypernym/hyponym navigation
        """)
        
        # Show sample XML format
        with st.expander("📄 Sample XML Format"):
            st.code("""
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
            """, language='xml')
    
    def _render_main_content(self):
        """Render the main content area with synset browsing."""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_synset_browser()
        
        with col2:
            self._render_pairing_panel()
    
    def _render_synset_browser(self):
        """Render the main synset browsing interface."""
        st.header("🔍 Browse Synsets")
        
        # Display current synset or synset list
        if st.session_state.current_synset:
            self._render_synset_details(st.session_state.current_synset)
        else:
            self._render_synset_list()
    
    def _render_synset_list(self):
        """Render a list of all synsets."""
        st.subheader("📋 All Synsets")
        
        # Create a DataFrame for better display
        synset_data = []
        for synset in st.session_state.loaded_synsets[:50]:  # Limit to first 50 for performance
            synset_data.append({
                'ID': synset.id,
                'POS': synset.pos,
                'Synonyms': ', '.join([s.get('literal', '') for s in synset.synonyms]),
                'Definition': synset.definition[:100] + "..." if len(synset.definition) > 100 else synset.definition
            })
        
        df = pd.DataFrame(synset_data)
        
        # Display with clickable rows
        st.write(f"Showing first 50 of {len(st.session_state.loaded_synsets)} synsets")
        
        selected_idx = st.selectbox(
            "Select a synset to view details:",
            range(len(synset_data)),
            format_func=lambda x: f"{synset_data[x]['ID']}: {synset_data[x]['Synonyms']}"
        )
        
        if st.button("View Selected Synset"):
            st.session_state.current_synset = st.session_state.loaded_synsets[selected_idx]
            st.rerun()
        
        # Display the table
        st.dataframe(df, use_container_width=True)
    
    def _render_synset_details(self, synset: Synset):
        """Render detailed view of a synset."""
        st.subheader(f"📖 Synset Details: {synset.id}")
        
        # Back button
        if st.button("← Back to List"):
            st.session_state.current_synset = None
            st.rerun()
        
        # Basic information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Part of Speech", synset.pos)
        with col2:
            st.metric("BCS", synset.bcs)
        with col3:
            st.metric("Natural Language", synset.nl)
        
        # Synonyms
        st.subheader("🔤 Synonyms")
        if synset.synonyms:
            for i, synonym in enumerate(synset.synonyms):
                with st.expander(f"Synonym {i+1}: {synonym.get('literal', 'N/A')}"):
                    st.write(f"**Literal:** {synonym.get('literal', 'N/A')}")
                    st.write(f"**Sense:** {synonym.get('sense', 'N/A')}")
                    st.write(f"**Note:** {synonym.get('lnote', 'N/A')}")
        else:
            st.write("No synonyms available")
        
        # Definition
        st.subheader("📝 Definition")
        st.write(synset.definition)
        
        # Relations (with hyperlinks)
        st.subheader("🔗 Related Synsets")
        if synset.ilr:
            for relation in synset.ilr:
                target_id = relation['target']
                rel_type = relation['type']
                
                # Check if target synset is loaded
                target_synset = self.parser.get_synset_by_id(target_id)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.write(f"**{rel_type}**")
                with col2:
                    st.write(target_id)
                with col3:
                    if target_synset:
                        if st.button(f"→ View", key=f"nav_{target_id}"):
                            st.session_state.current_synset = target_synset
                            st.rerun()
                    else:
                        st.write("(Not loaded)")
        else:
            st.write("No relations available")
        
        # Additional information
        with st.expander("ℹ️ Additional Information"):
            if synset.sumo:
                st.write(f"**SUMO:** {synset.sumo['concept']} ({synset.sumo['type']})")
            
            if synset.sentiment:
                st.write(f"**Sentiment:** Positive: {synset.sentiment['positive']}, Negative: {synset.sentiment['negative']}")
            
            if synset.domain:
                st.write(f"**Domain:** {synset.domain}")
            
            if synset.stamp:
                st.write(f"**Stamp:** {synset.stamp}")
    
    def _render_pairing_panel(self):
        """Render the pairing panel for selecting English/Serbian pairs."""
        st.header("🎯 Synset Pairing")
        
        if st.session_state.current_synset:
            serbian_synset = st.session_state.current_synset
            
            st.subheader("🇷🇸 Selected Serbian Synset")
            st.write(f"**ID:** {serbian_synset.id}")
            st.write(f"**Synonyms:** {', '.join([s.get('literal', '') for s in serbian_synset.synonyms])}")
            st.write(f"**Definition:** {serbian_synset.definition}")
            
            # Try to find linked English synset
            english_id = self._extract_english_id(serbian_synset.id)
            
            if english_id:
                st.subheader("🇺🇸 Linked English Synset")
                st.write(f"**English ID:** {english_id}")
                
                # Try to get English synset data
                try:
                    import re
                    numeric_id_match = re.match(r"ENG30-(\d+)-[nvar]", english_id)
                    numeric_id = numeric_id_match.group(1) if numeric_id_match else None
                    english_synsets = self.synset_handler.get_synsets(numeric_id)
                    
                    if english_synsets:
                        english_synset = english_synsets[0]
                        st.write(f"**Definition:** {english_synset.get('definition', 'N/A')}")
                        st.write(f"**Lemmas:** {', '.join(english_synset.get('lemmas', []))}")
                        
                        # Pairing button
                        if st.button("✅ Add to Pairs"):
                            pair = {
                                'serbian_id': serbian_synset.id,
                                'serbian_synonyms': [s.get('literal', '') for s in serbian_synset.synonyms],
                                'serbian_definition': serbian_synset.definition,
                                'english_id': english_id,
                                'english_definition': english_synset.get('definition', ''),
                                'english_lemmas': english_synset.get('lemmas', [])
                            }
                            
                            # Check if pair already exists
                            existing = any(p['serbian_id'] == serbian_synset.id for p in st.session_state.selected_pairs)
                            if not existing:
                                st.session_state.selected_pairs.append(pair)
                                st.success("Pair added!")
                                st.rerun()
                            else:
                                st.warning("This pair is already selected!")
                    else:
                        st.write("English synset not found in WordNet")
                        
                except Exception as e:
                    st.error(f"Error fetching English synset: {e}")
            else:
                st.subheader("🇺🇸 Manual English Synset Selection")
                st.write("No automatic English link found. You can manually search for an English synset to pair.")
                
                english_search = st.text_input("Search English synsets", placeholder="Enter English word...")
                
                if english_search:
                    try:
                        english_synsets = self.synset_handler.search_synsets(english_search, limit=5)
                        
                        if english_synsets:
                            st.write("Select an English synset:")
                            for i, eng_synset in enumerate(english_synsets):
                                with st.expander(f"{eng_synset['name']}: {eng_synset['definition'][:100]}..."):
                                    st.write(f"**Name:** {eng_synset['name']}")
                                    st.write(f"**Definition:** {eng_synset['definition']}")
                                    st.write(f"**Lemmas:** {', '.join(eng_synset['lemmas'])}")
                                    
                                    if st.button(f"✅ Pair with this synset", key=f"manual_pair_{i}"):
                                        pair = {
                                            'serbian_id': serbian_synset.id,
                                            'serbian_synonyms': [s.get('literal', '') for s in serbian_synset.synonyms],
                                            'serbian_definition': serbian_synset.definition,
                                            'english_id': eng_synset['name'],
                                            'english_definition': eng_synset['definition'],
                                            'english_lemmas': eng_synset['lemmas']
                                        }
                                        
                                        existing = any(p['serbian_id'] == serbian_synset.id for p in st.session_state.selected_pairs)
                                        if not existing:
                                            st.session_state.selected_pairs.append(pair)
                                            st.success("Manual pair added!")
                                            st.rerun()
                                        else:
                                            st.warning("This pair is already selected!")
                        else:
                            st.write("No English synsets found")
                    except Exception as e:
                        st.error(f"Error searching English synsets: {e}")
        
        # Display current pairs
        if st.session_state.selected_pairs:
            st.subheader("📋 Selected Pairs")
            
            for i, pair in enumerate(st.session_state.selected_pairs):
                with st.expander(f"Pair {i+1}: {pair['serbian_id']} ↔ {pair['english_id']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**🇷🇸 Serbian:**")
                        st.write(f"ID: {pair['serbian_id']}")
                        st.write(f"Synonyms: {', '.join(pair['serbian_synonyms'])}")
                        st.write(f"Definition: {pair['serbian_definition']}")
                    
                    with col2:
                        st.write("**🇺🇸 English:**")
                        st.write(f"ID: {pair['english_id']}")
                        st.write(f"Lemmas: {', '.join(pair['english_lemmas'])}")
                        st.write(f"Definition: {pair['english_definition']}")
                    
                    if st.button(f"🗑️ Remove Pair {i+1}", key=f"remove_{i}"):
                        st.session_state.selected_pairs.pop(i)
                        st.success("Pair removed!")
                        st.rerun()
    
    def _extract_english_id(self, synset_id: str) -> Optional[str]:
        """Extract English WordNet ID if present."""
        if synset_id.startswith('ENG30-'):
            return synset_id
        return None
    
    def _export_pairs(self):
        """Export selected pairs to JSON."""
        if st.session_state.selected_pairs:
            data = {
                'pairs': st.session_state.selected_pairs,
                'metadata': {
                    'total_pairs': len(st.session_state.selected_pairs),
                    'created_by': 'Serbian WordNet Synset Browser',
                    'format_version': '1.0'
                }
            }
            
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📥 Download Pairs (JSON)",
                data=json_str,
                file_name="serbian_english_synset_pairs.json",
                mime="application/json"
            )
    
    def _get_sample_xml(self) -> str:
        """Get sample XML data for testing."""
        return """<root>
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


def main():
    """Main entry point for the application."""
    app = SynsetBrowserApp()
    app.run()


if __name__ == "__main__":
    main()