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

# Add the src directory to the Python path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import models
try:
    from ..models.xml_synset_parser import XmlSynsetParser, Synset
    from ..models.synset_handler import SynsetHandler
except ImportError:
    # Fallback for when running as script
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
        if 'current_synset_index' not in st.session_state:
            st.session_state.current_synset_index = 0
        if 'synset_list_page' not in st.session_state:
            st.session_state.synset_list_page = 0
    
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
    
    def _ensure_parser_synced(self):
        """Ensure parser's internal dictionary is synced with session state."""
        if (st.session_state.loaded_synsets and 
            len(self.parser.synsets) != len(st.session_state.loaded_synsets)):
            
            print(f"DEBUG: Syncing parser - session has {len(st.session_state.loaded_synsets)}, parser has {len(self.parser.synsets)}")
            
            # Rebuild parser's internal dictionaries from session state
            self.parser.clear()
            for synset in st.session_state.loaded_synsets:
                self.parser.synsets[synset.id] = synset
                
                # Rebuild English links
                if synset.id.startswith('ENG30-'):
                    english_id = synset.id
                    if english_id not in self.parser.english_links:
                        self.parser.english_links[english_id] = []
                    self.parser.english_links[english_id].append(synset)
            
            print(f"DEBUG: Parser synced - now has {len(self.parser.synsets)} synsets")
    
    def _render_sidebar(self):
        """Render the sidebar with navigation and controls."""
        # Ensure parser is synced with session state
        self._ensure_parser_synced()
        
        st.header("🔧 Controls")
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
                        # Clear parser before loading new data
                        self.parser.clear()
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
                    # Clear parser before loading new data
                    self.parser.clear()
                    synsets = self.parser.parse_xml_string(sample_xml)
                    st.session_state.loaded_synsets = synsets
                    st.success(f"Loaded {len(synsets)} sample synsets!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading sample data: {e}")
        
        # Local XML file option
        st.subheader("📁 Load Local XML File")
        st.write("Load XML file from your local data directory:")
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        
        if data_dir.exists():
            xml_files = list(data_dir.glob("*.xml"))
            if xml_files:
                selected_file = st.selectbox(
                    "Select XML file:",
                    xml_files,
                    format_func=lambda x: x.name
                )
                
                if st.button("Load Selected XML File"):
                    with st.spinner(f"Loading {selected_file.name}..."):
                        try:
                            # Clear parser before loading new data
                            self.parser.clear()
                            synsets = self.parser.parse_xml_file(str(selected_file))
                            st.session_state.loaded_synsets = synsets
                            st.success(f"Loaded {len(synsets)} synsets from {selected_file.name}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error loading {selected_file.name}: {e}")
            else:
                st.info("No XML files found in data directory. Place your XML files in the 'data' folder.")
        else:
            st.info("Data directory not found. Create a 'data' folder in the project root and place your XML files there.")
        
        # Search and navigation
        if st.session_state.loaded_synsets:
            st.subheader("� Search")
            search_query = st.text_input("Search synsets", placeholder="Enter search term...")
            
            if search_query:
                search_results = self.parser.search_synsets(search_query, limit=10)
                if search_results:
                    st.write("Search Results:")
                    for i, synset in enumerate(search_results):
                        display_text = f"{synset.id}: {synset.synonyms[0]['literal'] if synset.synonyms else 'No synonyms'}"
                        if st.button(display_text, key=f"search_{i}"):
                            st.session_state.current_synset = synset
                            # Find the index of this synset in the loaded_synsets
                            try:
                                st.session_state.current_synset_index = st.session_state.loaded_synsets.index(synset)
                            except ValueError:
                                st.session_state.current_synset_index = 0
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
        2. **Load from local data directory** if you have XML files in the `data` folder, or
        3. **Use sample data** to explore the functionality
        
        ### Features:
        - 🔍 **Search synsets** by definition, synonyms, or usage examples
        - 🔗 **Navigate hyperlinks** between related synsets
        - 🎯 **Pair Serbian and English synsets** for training data
        - � **View usage examples** when available (Serbian) and examples (English)
        - �📊 **Export selected pairs** for machine learning with usage examples
        
        ### XML Format Expected:
        The tool expects XML files with Serbian synsets in the format containing:
        - `<SYNSET>` elements with ID, POS, SYNONYM, DEF, and ILR relations
        - Optional `<USAGE>` elements with usage examples in Serbian
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
    <UCS>1</BCS>
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
        """Render a list of all synsets with pagination."""
        st.subheader("📋 All Synsets")
        
        # Show total count
        total_synsets = len(st.session_state.loaded_synsets)
        st.write(f"Total loaded synsets: {total_synsets}")
        
        if total_synsets == 0:
            return
        
        # Pagination settings
        synsets_per_page = 50
        total_pages = (total_synsets + synsets_per_page - 1) // synsets_per_page
        current_page = st.session_state.synset_list_page
        
        # Ensure current page is valid
        if current_page >= total_pages:
            st.session_state.synset_list_page = 0
            current_page = 0
        
        # Calculate range for current page
        start_idx = current_page * synsets_per_page
        end_idx = min(start_idx + synsets_per_page, total_synsets)
        
        # Pagination controls
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️ First", disabled=(current_page == 0)):
                st.session_state.synset_list_page = 0
                st.rerun()
        
        with col2:
            if st.button("◀️ Previous", disabled=(current_page == 0)):
                st.session_state.synset_list_page = current_page - 1
                st.rerun()
        
        with col3:
            st.write(f"Page {current_page + 1} of {total_pages} (showing {start_idx + 1}-{end_idx} of {total_synsets})")
        
        with col4:
            if st.button("Next ▶️", disabled=(current_page >= total_pages - 1)):
                st.session_state.synset_list_page = current_page + 1
                st.rerun()
        
        with col5:
            if st.button("Last ⏭️", disabled=(current_page >= total_pages - 1)):
                st.session_state.synset_list_page = total_pages - 1
                st.rerun()
        
        # Create a DataFrame for current page
        synset_data = []
        for i, synset in enumerate(st.session_state.loaded_synsets[start_idx:end_idx]):
            usage_indicator = " 💡" if synset.usage else ""
            synset_data.append({
                'Index': start_idx + i,
                'ID': synset.id,
                'POS': synset.pos,
                'Synonyms': ', '.join([s.get('literal', '') for s in synset.synonyms]),
                'Definition': synset.definition[:100] + "..." if len(synset.definition) > 100 else synset.definition,
                'Usage': "Yes" + usage_indicator if synset.usage else "No"
            })
        
        df = pd.DataFrame(synset_data)
        
        # Quick selection dropdown for current page
        if synset_data:
            selected_idx = st.selectbox(
                "Select a synset to view details:",
                range(len(synset_data)),
                format_func=lambda x: f"{synset_data[x]['ID']}: {synset_data[x]['Synonyms'][:50]}..."
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("👁️ View Selected Synset"):
                    global_idx = start_idx + selected_idx
                    st.session_state.current_synset = st.session_state.loaded_synsets[global_idx]
                    st.session_state.current_synset_index = global_idx
                    st.rerun()
            
            with col2:
                if st.button("🚀 Start Sequential Review from Selected"):
                    global_idx = start_idx + selected_idx
                    st.session_state.current_synset = st.session_state.loaded_synsets[global_idx]
                    st.session_state.current_synset_index = global_idx
                    st.rerun()
        
        # Display the table
        st.dataframe(df, use_container_width=True)
    
    def _render_synset_details(self, synset: Synset):
        """Render detailed view of a synset with navigation."""
        # Ensure parser is synced before looking up relations
        self._ensure_parser_synced()
        
        st.subheader(f"📖 Synset Details: {synset.id}")
        
        # Navigation controls
        total_synsets = len(st.session_state.loaded_synsets)
        current_idx = st.session_state.current_synset_index
        
        # Navigation buttons
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 2, 1, 1, 1])
        
        with col1:
            if st.button("← Back to List"):
                st.session_state.current_synset = None
                st.rerun()
        
        with col2:
            if st.button("⏮️ First", disabled=(current_idx == 0)):
                st.session_state.current_synset_index = 0
                st.session_state.current_synset = st.session_state.loaded_synsets[0]
                st.rerun()
        
        with col3:
            st.write(f"Synset {current_idx + 1} of {total_synsets}")
        
        with col4:
            if st.button("◀️ Previous", disabled=(current_idx == 0)):
                st.session_state.current_synset_index = current_idx - 1
                st.session_state.current_synset = st.session_state.loaded_synsets[current_idx - 1]
                st.rerun()
        
        with col5:
            if st.button("Next ▶️", disabled=(current_idx >= total_synsets - 1)):
                st.session_state.current_synset_index = current_idx + 1
                st.session_state.current_synset = st.session_state.loaded_synsets[current_idx + 1]
                st.rerun()
        
        with col6:
            if st.button("Last ⏭️", disabled=(current_idx >= total_synsets - 1)):
                st.session_state.current_synset_index = total_synsets - 1
                st.session_state.current_synset = st.session_state.loaded_synsets[total_synsets - 1]
                st.rerun()
        
        # Quick jump
        with st.expander("🎯 Quick Jump"):
            jump_to_idx = st.number_input(
                "Jump to synset number:",
                min_value=1,
                max_value=total_synsets,
                value=current_idx + 1,
                step=1
            ) - 1  # Convert to 0-based index
            
            if st.button("Jump"):
                st.session_state.current_synset_index = jump_to_idx
                st.session_state.current_synset = st.session_state.loaded_synsets[jump_to_idx]
                st.rerun()
        
        # Basic information with quality indicators
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Part of Speech", synset.pos)
        with col2:
            st.metric("BCS", synset.bcs)
        with col3:
            st.metric("Natural Language", synset.nl)
        with col4:
            if synset.domain:
                st.metric("Domain", synset.domain)
            else:
                st.metric("Domain", "Not specified")
        
        # Quality and provenance information (prominently displayed)
        st.subheader("👤 Translation Quality Info")
        col1, col2 = st.columns(2)
        
        with col1:
            if synset.stamp:
                # Parse stamp to extract translator and date
                stamp_parts = synset.stamp.split()
                if len(stamp_parts) >= 2:
                    translator = stamp_parts[0]
                    date_info = ' '.join(stamp_parts[1:])
                    st.info(f"**Translator:** {translator}")
                    st.info(f"**Date:** {date_info}")
                else:
                    st.info(f"**Stamp:** {synset.stamp}")
            else:
                st.warning("**No translation stamp available**")
        
        with col2:
            # Sentiment analysis if available
            if synset.sentiment:
                positive = synset.sentiment.get('positive', 0)
                negative = synset.sentiment.get('negative', 0)
                
                if positive > 0 or negative > 0:
                    st.write("**Sentiment Analysis:**")
                    sentiment_text = f"Positive: {positive:.3f}, Negative: {negative:.3f}"
                    
                    # Color code based on sentiment
                    if positive > negative:
                        st.success(f"😊 {sentiment_text}")
                    elif negative > positive:
                        st.error(f"😞 {sentiment_text}")
                    else:
                        st.info(f"😐 {sentiment_text}")
                else:
                    st.info("😐 **Neutral sentiment**")
            else:
                st.info("**No sentiment data**")
        
        # Usage indicator
        if synset.usage:
            st.success("💡 **Has usage example** - High quality synset")
        else:
            st.warning("⚠️ **No usage example** - Consider verifying translation")
        
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
        
        # Usage example
        if synset.usage:
            st.subheader("💡 Usage Example")
            st.write(f"*{synset.usage}*")
        
        # Relations (with hyperlinks) - show all with debug info
        st.subheader("🔗 Related Synsets")
        if synset.ilr:
            st.write(f"Found {len(synset.ilr)} relations:")
            
        # Relations (with enhanced information display)
        st.subheader("🔗 Related Synsets")
        if synset.ilr:
            st.write(f"Found {len(synset.ilr)} relations:")
            
            # Create table data for relations
            relation_data = []
            available_relations = []
            
            for relation in synset.ilr:
                target_id = relation['target']
                rel_type = relation['type']
                
                # Check if target synset is loaded
                target_synset = self.parser.get_synset_by_id(target_id)
                
                if target_synset:
                    # Get synonyms (literals) from target synset
                    target_literals = ', '.join([s.get('literal', '') for s in target_synset.synonyms]) if target_synset.synonyms else 'No synonyms'
                    
                    # Truncate definition if too long
                    target_definition = target_synset.definition
                    if len(target_definition) > 100:
                        target_definition = target_definition[:100] + "..."
                    
                    relation_data.append({
                        'Relation': rel_type,
                        'Target ID': target_id,
                        'Synonyms': target_literals,
                        'Definition': target_definition,
                        'Available': '✅'
                    })
                    available_relations.append((relation, target_synset))
                else:
                    relation_data.append({
                        'Relation': rel_type,
                        'Target ID': target_id,
                        'Synonyms': 'Not loaded',
                        'Definition': 'Not available',
                        'Available': '❌'
                    })
            
            # Display relations table
            if relation_data:
                df_relations = pd.DataFrame(relation_data)
                st.dataframe(df_relations, use_container_width=True, hide_index=True)
                
                # Navigation buttons for available relations
                if available_relations:
                    st.write("**Navigate to related synsets:**")
                    
                    # Group by relation type for better organization
                    relations_by_type = {}
                    for relation, target_synset in available_relations:
                        rel_type = relation['type']
                        if rel_type not in relations_by_type:
                            relations_by_type[rel_type] = []
                        relations_by_type[rel_type].append((relation, target_synset))
                    
                    # Display navigation buttons grouped by type
                    for rel_type, type_relations in relations_by_type.items():
                        with st.expander(f"🔗 {rel_type.title()} ({len(type_relations)} synsets)"):
                            cols = st.columns(min(3, len(type_relations)))  # Max 3 columns
                            for i, (relation, target_synset) in enumerate(type_relations):
                                with cols[i % 3]:
                                    target_literals = ', '.join([s.get('literal', '') for s in target_synset.synonyms][:2])  # First 2 synonyms
                                    if len(target_literals) > 30:
                                        target_literals = target_literals[:30] + "..."
                                    
                                    button_label = f"→ {target_literals}"
                                    if st.button(button_label, key=f"nav_{relation['target']}", help=f"Go to {relation['target']}"):
                                        st.session_state.current_synset = target_synset
                                        # Find the index of this synset in the loaded_synsets
                                        try:
                                            st.session_state.current_synset_index = st.session_state.loaded_synsets.index(target_synset)
                                        except ValueError:
                                            st.session_state.current_synset_index = 0
                                        st.rerun()
                
                # Show statistics
                available_count = len(available_relations)
                total_count = len(synset.ilr)
                unavailable_count = total_count - available_count
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Available Relations", available_count)
                with col2:
                    st.metric("External Relations", unavailable_count)
                with col3:
                    st.metric("Total Relations", total_count)
            
            # Debug information
            with st.expander("� Debug Info"):
                st.write(f"Parser has {len(self.parser.synsets)} synsets loaded")
                st.write(f"Session state has {len(st.session_state.loaded_synsets)} synsets")
                st.write("Sample of parser synset IDs:")
                parser_ids = list(self.parser.synsets.keys())[:5]
                for sid in parser_ids:
                    st.write(f"  - {sid}")
                st.write("Target IDs from relations:")
                for relation in synset.ilr[:5]:  # Show first 5
                    target_id = relation['target']
                    found = target_id in self.parser.synsets
                    st.write(f"  - {target_id} {'✓' if found else '✗'}")
        else:
            st.write("No relations available")
        
        # Additional technical information
        with st.expander("🔧 Technical Information"):
            if synset.sumo:
                st.write(f"**SUMO:** {synset.sumo['concept']} ({synset.sumo['type']})")
            
            # Full stamp details
            if synset.stamp:
                st.write(f"**Full Stamp:** {synset.stamp}")
            
            # Raw sentiment values
            if synset.sentiment:
                st.write(f"**Raw Sentiment Values:**")
                st.write(f"  • Positive: {synset.sentiment['positive']}")
                st.write(f"  • Negative: {synset.sentiment['negative']}")
    
    def _render_pairing_panel(self):
        """Render the pairing panel for selecting English/Serbian pairs."""
        st.header("🎯 Synset Pairing")
        
        if st.session_state.current_synset:
            serbian_synset = st.session_state.current_synset
            
            st.subheader("🇷🇸 Selected Serbian Synset")
            st.write(f"**ID:** {serbian_synset.id}")
            st.write(f"**Synonyms:** {', '.join([s.get('literal', '') for s in serbian_synset.synonyms])}")
            st.write(f"**Definition:** {serbian_synset.definition}")
            if serbian_synset.usage:
                st.write(f"**Usage:** *{serbian_synset.usage}*")
            
            # Quality indicators for pairing decision
            st.write("**Quality Indicators:**")
            quality_items = []
            
            if serbian_synset.stamp:
                stamp_parts = serbian_synset.stamp.split()
                translator = stamp_parts[0] if stamp_parts else "Unknown"
                quality_items.append(f"👤 Translator: {translator}")
            else:
                quality_items.append("⚠️ No translator info")
            
            if serbian_synset.usage:
                quality_items.append("💡 Has usage example")
            else:
                quality_items.append("⚠️ No usage example")
            
            if serbian_synset.domain:
                quality_items.append(f"🏷️ Domain: {serbian_synset.domain}")
            
            for item in quality_items:
                st.write(f"  • {item}")
            
            # Quality score for pairing recommendation
            quality_score = 0
            if serbian_synset.stamp:
                quality_score += 1
            if serbian_synset.usage:
                quality_score += 1
            if serbian_synset.domain:
                quality_score += 0.5
            
            if quality_score >= 2:
                st.success(f"⭐ **High Quality** (Score: {quality_score:.1f}/2.5) - Recommended for pairing")
            elif quality_score >= 1:
                st.warning(f"⚠️ **Medium Quality** (Score: {quality_score:.1f}/2.5) - Review carefully")
            else:
                st.error(f"❌ **Low Quality** (Score: {quality_score:.1f}/2.5) - Use with caution")
            
            # Try to find linked English synset
            english_id = self._extract_english_id(serbian_synset.id)
            
            if english_id:
                st.subheader("🇺🇸 Linked English Synset")
                st.write(f"**English ID:** {english_id}")
                
                # Try to get English synset data
                try:
                    import re
                    numeric_id_match = re.match(r"ENG30-(\d+)-([nvar])", english_id)
                    if numeric_id_match:
                        numeric_id = numeric_id_match.group(1)
                        pos = numeric_id_match.group(2)
                        
                        # Try to get synset by offset
                        english_synset = self.synset_handler.get_synset_by_offset(numeric_id, pos)
                        
                        if english_synset:
                            st.write(f"**Definition:** {english_synset.get('definition', 'N/A')}")
                            st.write(f"**Lemmas:** {', '.join(english_synset.get('lemmas', []))}")
                            if english_synset.get('examples'):
                                st.write(f"**Examples:** {'; '.join(english_synset.get('examples', []))}")
                            st.write(f"**WordNet Name:** {english_synset.get('name', 'N/A')}")
                            
                            # Pairing button
                            if st.button("✅ Add to Pairs"):
                                pair = {
                                    'serbian_id': serbian_synset.id,
                                    'serbian_synonyms': [s.get('literal', '') for s in serbian_synset.synonyms],
                                    'serbian_definition': serbian_synset.definition,
                                    'serbian_usage': serbian_synset.usage,
                                    'english_id': english_id,
                                    'english_definition': english_synset.get('definition', ''),
                                    'english_lemmas': english_synset.get('lemmas', []),
                                    'english_examples': english_synset.get('examples', [])
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
                            st.write(f"Looking for offset: {numeric_id}, POS: {pos}")
                    else:
                        st.write("Could not parse English ID format")
                        
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
                                    if eng_synset.get('examples'):
                                        st.write(f"**Examples:** {'; '.join(eng_synset['examples'])}")
                                    
                                    if st.button(f"✅ Pair with this synset", key=f"manual_pair_{i}"):
                                        pair = {
                                            'serbian_id': serbian_synset.id,
                                            'serbian_synonyms': [s.get('literal', '') for s in serbian_synset.synonyms],
                                            'serbian_definition': serbian_synset.definition,
                                            'serbian_usage': serbian_synset.usage,
                                            'english_id': eng_synset['name'],
                                            'english_definition': eng_synset['definition'],
                                            'english_lemmas': eng_synset['lemmas'],
                                            'english_examples': eng_synset.get('examples', [])
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
                        if pair.get('serbian_usage'):
                            st.write(f"Usage: *{pair['serbian_usage']}*")
                    
                    with col2:
                        st.write("**🇺🇸 English:**")
                        st.write(f"ID: {pair['english_id']}")
                        st.write(f"Lemmas: {', '.join(pair['english_lemmas'])}")
                        st.write(f"Definition: {pair['english_definition']}")
                        if pair.get('english_examples'):
                            st.write(f"Examples: {'; '.join(pair['english_examples'])}")
                    
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
      <USAGE>Nova ustanova će biti otvorena sledeće godine.</USAGE>
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
      <USAGE>Dodaj malo začina u supu da bude ukusnija.</USAGE>
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
      <USAGE>Da li si na mom mestu, šta bi učinio?</USAGE>
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