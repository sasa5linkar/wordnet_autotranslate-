"""
Streamlit GUI for browsing Serbian WordNet synsets and pairing with English synsets.

This module provides a comprehensive interface for:
- Loading and browsing Serbian WordNet synsets from XML files
- Searching and filtering synsets by various criteria
- Viewing detailed synset information including relations and quality metrics
- Pairing Serbian synsets with English WordNet synsets
- Exporting paired data for machine learning applications

The application follows best practices including:
- Modular design with small, focused methods
- Constants for magic numbers and strings
- Proper error handling and logging
- Session state management with named constants
- Type hints and comprehensive documentation

Author: Serbian WordNet Team
Version: 2.0 (Refactored)

Optional Dependencies
---------------------
The GUI relies on :mod:`streamlit` and uses :mod:`pandas` for table
rendering and data export. These packages are optional; the rest of the
project can run in headless environments. Features that require them
will raise :class:`ImportError` when absent. Heavy WordNet resources are
also loaded lazily to avoid unnecessary downloads during import.
"""

import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

# Optional dependencies: pandas for table rendering/export, streamlit for GUI.
# Both are heavy and may not be installed in headless test environments.
try:  # pragma: no cover - trivial import shim
    import pandas as pd  # type: ignore
except Exception:  # ImportError or other issues
    pd = None  # type: ignore

try:  # pragma: no cover - trivial import shim
    import streamlit as st  # type: ignore
except Exception:  # ImportError or runtime issues
    class _StreamlitStub:
        """Minimal stub used when Streamlit isn't installed.

        Only exposes ``session_state`` and raises informative errors for
        any other attribute access.  This allows unit tests that don't rely on
        the GUI to run without the real dependency.
        """

        def __init__(self) -> None:
            self.session_state: Dict[str, object] = {}

        def __getattr__(self, name: str):  # pragma: no cover - simple helper
            def _missing(*_args, **_kwargs):
                raise ImportError("streamlit is required for GUI features")

            return _missing

    st = _StreamlitStub()  # type: ignore

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

# Constants
SYNSETS_PER_PAGE = 50
SEARCH_LIMIT = 10
QUALITY_SCORE_HIGH = 2.0
QUALITY_SCORE_MEDIUM = 1.0
MAX_DEFINITION_LENGTH = 100
MAX_DISPLAY_TEXT_LENGTH = 50
MAX_DISPLAYED_SYNONYMS = 2
MAX_DISPLAYED_RELATIONS = 3
EXPORT_FORMAT_VERSION = "2.0"

# Session state keys
SESSION_CURRENT_SYNSET = 'current_synset'
SESSION_SELECTED_PAIRS = 'selected_pairs'
SESSION_LOADED_SYNSETS = 'loaded_synsets'
SESSION_CURRENT_INDEX = 'current_synset_index'
SESSION_LIST_PAGE = 'synset_list_page'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _require_pandas() -> None:
    """Ensure :mod:`pandas` is available before using table features."""
    if pd is None:  # pragma: no cover - simple guard
        raise ImportError("pandas is required for this feature; please install it")
class SynsetBrowserApp:
    """Main Streamlit application for synset browsing."""
    
    def __init__(self, parser: Optional[XmlSynsetParser] = None, synset_handler: Optional[SynsetHandler] = None):
        """Initialize the application.

        Parameters
        ----------
        parser:
            Optional pre-created ``XmlSynsetParser`` instance.
        synset_handler:
            Optional ``SynsetHandler``.  When ``None`` the handler is
            initialised lazily on first access to avoid heavy WordNet
            downloads during unit tests.
        """
        self.parser = parser or XmlSynsetParser()
        self._synset_handler = synset_handler
        self.selected_pairs = []  # List of (serbian_synset, english_synset) pairs

        # Initialize session state
        self._init_session_state()

    @property
    def synset_handler(self) -> SynsetHandler:
        """Lazily instantiate :class:`SynsetHandler` when needed."""
        if self._synset_handler is None:  # pragma: no cover - simple lazy init
            self._synset_handler = SynsetHandler()
        return self._synset_handler
    
    def _init_session_state(self):
        """Initialize session state variables."""
        session_defaults = {
            SESSION_CURRENT_SYNSET: None,
            SESSION_SELECTED_PAIRS: [],
            SESSION_LOADED_SYNSETS: [],
            SESSION_CURRENT_INDEX: 0,
            SESSION_LIST_PAGE: 0,
        }
        
        for key, default_value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
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
        if st.session_state[SESSION_LOADED_SYNSETS]:
            self._render_main_content()
        else:
            self._render_welcome_screen()
    
    def _ensure_parser_synced(self):
        """Ensure parser's internal dictionary is synced with session state."""
        loaded_count = len(st.session_state[SESSION_LOADED_SYNSETS])
        parser_count = len(self.parser.synsets)
        
        if st.session_state[SESSION_LOADED_SYNSETS] and parser_count != loaded_count:
            logger.info(
                f"Syncing parser - session has {loaded_count}, parser has {parser_count}"
            )
            
            # Rebuild parser's internal dictionaries from session state
            self.parser.clear()
            for synset in st.session_state[SESSION_LOADED_SYNSETS]:
                self.parser.synsets[synset.id] = synset
                
                # Rebuild English links
                if synset.id.startswith('ENG30-'):
                    english_id = synset.id
                    if english_id not in self.parser.english_links:
                        self.parser.english_links[english_id] = []
                    self.parser.english_links[english_id].append(synset)
            
            logger.info(f"Parser synced - now has {len(self.parser.synsets)} synsets")
    
    def _render_sidebar(self):
        """Render the sidebar with navigation and controls."""
        # Ensure parser is synced with session state
        self._ensure_parser_synced()
        
        st.header("🔧 Controls")
        
        # File loading sections
        self._render_file_upload_section()
        self._render_sample_data_section()
        self._render_local_file_section()
        
        # Search and filtering sections
        if st.session_state[SESSION_LOADED_SYNSETS]:
            self._render_search_section()
            self._render_pos_filter_section()
        
        # Selected pairs management
        self._render_pairs_management_section()
    
    def _load_synsets_from_content(self, content: str, source_name: str) -> bool:
        """
        Load synsets from XML content with error handling.
        
        Args:
            content: XML content as string
            source_name: Name of the source for error messages
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.parser.clear()
            synsets = self.parser.parse_xml_string(content)
            st.session_state[SESSION_LOADED_SYNSETS] = synsets
            st.success(f"Loaded {len(synsets)} synsets from {source_name}!")
            st.rerun()
            return True
        except Exception as e:
            logger.error(f"Error loading {source_name}: {e}")
            st.error(f"Error loading {source_name}: {e}")
            return False
    
    def _load_synsets_from_file(self, file_path: str, source_name: str) -> bool:
        """
        Load synsets from XML file with error handling.
        
        Args:
            file_path: Path to XML file
            source_name: Name of the source for error messages
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.parser.clear()
            synsets = self.parser.parse_xml_file(file_path)
            st.session_state[SESSION_LOADED_SYNSETS] = synsets
            st.success(f"Loaded {len(synsets)} synsets from {source_name}!")
            st.rerun()
            return True
        except Exception as e:
            logger.error(f"Error loading {source_name}: {e}")
            st.error(f"Error loading {source_name}: {e}")
            return False
    
    def _render_file_upload_section(self):
        """Render the file upload section."""
        st.subheader("� Load Synsets")
        uploaded_file = st.file_uploader(
            "Upload XML file with Serbian synsets",
            type=['xml'],
            help="Upload an XML file containing Serbian WordNet synsets"
        )
        
        if uploaded_file is not None:
            if st.button("Load Synsets"):
                with st.spinner("Parsing XML file..."):
                    content = uploaded_file.read().decode('utf-8')
                    self._load_synsets_from_content(content, "uploaded file")
    
    def _render_sample_data_section(self):
        """Render the sample data section."""
        st.subheader("📝 Use Sample Data")
        if st.button("Load Sample Serbian Synsets"):
            sample_xml = self._get_sample_xml()
            with st.spinner("Loading sample data..."):
                self._load_synsets_from_content(sample_xml, "sample data")
    
    def _render_local_file_section(self):
        """Render the local file loading section."""
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
                        self._load_synsets_from_file(str(selected_file), selected_file.name)
            else:
                st.info("No XML files found in data directory. Place your XML files in the 'data' folder.")
        else:
            st.info("Data directory not found. Create a 'data' folder in the project root and place your XML files there.")
    
    def _render_search_section(self):
        """Render the search section."""
        st.subheader("🔍 Search")
        search_query = st.text_input("Search synsets", placeholder="Enter search term...")
        
        if search_query:
            search_results = self.parser.search_synsets(search_query, limit=SEARCH_LIMIT)
            if search_results:
                st.write("Search Results:")
                for i, synset in enumerate(search_results):
                    display_text = self._get_synset_display_text(synset)
                    if st.button(display_text, key=f"search_{i}"):
                        self._navigate_to_synset(synset)
            else:
                st.write("No results found")
    
    def _render_pos_filter_section(self):
        """Render the part-of-speech filter section."""
        st.subheader("🏷️ Filter by POS")
        pos_options = list(set(s.pos for s in st.session_state[SESSION_LOADED_SYNSETS]))
        selected_pos = st.selectbox("Part of Speech", ["All"] + sorted(pos_options))
        
        if selected_pos != "All":
            filtered_synsets = [
                s for s in st.session_state[SESSION_LOADED_SYNSETS] 
                if s.pos == selected_pos
            ]
            st.write(f"{len(filtered_synsets)} synsets with POS '{selected_pos}'")
    
    def _render_pairs_management_section(self):
        """Render the selected pairs management section."""
        st.subheader("📋 Selected Pairs")
        st.write(f"Selected pairs: {len(st.session_state[SESSION_SELECTED_PAIRS])}")
        
        # Import functionality
        self._render_import_section()
        
        if st.session_state[SESSION_SELECTED_PAIRS]:
            if st.button("📥 Export Pairs"):
                self._export_pairs()
            
            if st.button("🗑️ Clear All Pairs"):
                st.session_state[SESSION_SELECTED_PAIRS] = []
                st.success("All pairs cleared!")
                st.rerun()
    
    def _render_import_section(self):
        """Render the import section for uploading JSON pairs."""
        st.subheader("📤 Import Pairs")
        
        uploaded_file = st.file_uploader(
            "Upload JSON file with previously exported pairs",
            type=['json'],
            help="Upload a JSON file containing synset pairs exported from this application"
        )
        
        if uploaded_file is not None:
            # Import options
            col1, col2 = st.columns(2)
            with col1:
                import_mode = st.radio(
                    "Import mode:",
                    ["Merge with existing", "Replace existing"],
                    help="Choose whether to add to current pairs or replace them entirely"
                )
            
            with col2:
                if st.button("📤 Import Pairs", type="primary"):
                    self._import_pairs(uploaded_file, import_mode == "Replace existing")
    
    def _import_pairs(self, uploaded_file, replace_existing: bool):
        """
        Import pairs from uploaded JSON file.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            replace_existing: Whether to replace existing pairs or merge
        """
        try:
            # Read and parse JSON
            content = uploaded_file.read().decode('utf-8')
            data = json.loads(content)
            
            # Validate the imported data
            validation_result = self._validate_import_data(data)
            if not validation_result['valid']:
                st.error(f"Invalid file format: {validation_result['error']}")
                return
            
            # Extract pairs from the data
            imported_pairs = data.get('pairs', [])
            
            if not imported_pairs:
                st.warning("No pairs found in the uploaded file.")
                return
            
            # Handle import mode
            original_count = len(st.session_state[SESSION_SELECTED_PAIRS])
            
            if replace_existing:
                st.session_state[SESSION_SELECTED_PAIRS] = imported_pairs
                new_count = len(imported_pairs)
                st.success(f"✅ Successfully imported {new_count} pairs (replaced existing pairs)")
            else:
                # Merge: avoid duplicates based on serbian_id
                existing_ids = {pair['serbian_id'] for pair in st.session_state[SESSION_SELECTED_PAIRS]}
                new_pairs = [pair for pair in imported_pairs if pair['serbian_id'] not in existing_ids]
                duplicates = len(imported_pairs) - len(new_pairs)
                
                st.session_state[SESSION_SELECTED_PAIRS].extend(new_pairs)
                new_count = len(st.session_state[SESSION_SELECTED_PAIRS])
                
                if duplicates > 0:
                    st.success(f"✅ Successfully imported {len(new_pairs)} new pairs. "
                             f"Skipped {duplicates} duplicates. Total pairs: {new_count}")
                else:
                    st.success(f"✅ Successfully imported {len(new_pairs)} pairs. Total pairs: {new_count}")
            
            # Show import metadata if available
            metadata = data.get('metadata', {})
            if metadata:
                with st.expander("📊 Import Details"):
                    if 'export_timestamp' in metadata:
                        st.write(f"**Original export date:** {metadata['export_timestamp']}")
                    if 'format_version' in metadata:
                        st.write(f"**Format version:** {metadata['format_version']}")
                    if 'total_pairs' in metadata:
                        st.write(f"**Pairs in file:** {metadata['total_pairs']}")
                    if 'created_by' in metadata:
                        st.write(f"**Created by:** {metadata['created_by']}")
            
            st.rerun()
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON file: {str(e)}")
        except Exception as e:
            logger.error(f"Error importing pairs: {e}")
            st.error(f"Error importing pairs: {str(e)}")
    
    def _validate_import_data(self, data: Dict) -> Dict:
        """
        Validate the structure of imported JSON data.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            Dictionary with 'valid' boolean and 'error' message if invalid
        """
        try:
            # Check if data is a dictionary
            if not isinstance(data, dict):
                return {'valid': False, 'error': 'Root element must be a JSON object'}
            
            # Check for required top-level keys
            if 'pairs' not in data:
                return {'valid': False, 'error': 'Missing required "pairs" field'}
            
            # Check if pairs is a list
            if not isinstance(data['pairs'], list):
                return {'valid': False, 'error': '"pairs" field must be a list'}
            
            # Check format version compatibility if present
            metadata = data.get('metadata', {})
            if 'format_version' in metadata:
                file_version = metadata['format_version']
                
                # For now, accept versions 1.0 and 2.0
                supported_versions = ['1.0', '2.0']
                if file_version not in supported_versions:
                    return {
                        'valid': False, 
                        'error': f'Unsupported format version {file_version}. Supported versions: {", ".join(supported_versions)}'
                    }
            
            # Validate each pair has required fields
            required_pair_fields = ['serbian_id', 'english_id']
            for i, pair in enumerate(data['pairs']):
                if not isinstance(pair, dict):
                    return {'valid': False, 'error': f'Pair {i+1} is not a valid object'}
                
                for field in required_pair_fields:
                    if field not in pair:
                        return {'valid': False, 'error': f'Pair {i+1} missing required field: {field}'}
                    
                    if not isinstance(pair[field], str):
                        return {'valid': False, 'error': f'Pair {i+1} field "{field}" must be a string'}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {str(e)}'}

    def _get_synset_display_text(self, synset: Synset) -> str:
        """Get display text for a synset."""
        if synset.synonyms:
            synonym = synset.synonyms[0]['literal']
        else:
            synonym = 'No synonyms'
        return f"{synset.id}: {synonym}"
    
    def _navigate_to_synset(self, synset: Synset):
        """Navigate to a specific synset."""
        st.session_state[SESSION_CURRENT_SYNSET] = synset
        # Find the index of this synset in the loaded_synsets
        try:
            index = st.session_state[SESSION_LOADED_SYNSETS].index(synset)
            st.session_state[SESSION_CURRENT_INDEX] = index
        except ValueError:
            st.session_state[SESSION_CURRENT_INDEX] = 0
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
        - 📊 **Export selected pairs** for machine learning with usage examples
        - 📤 **Import previously exported pairs** to resume work or share progress
        
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
        if st.session_state[SESSION_CURRENT_SYNSET]:
            self._render_synset_details(st.session_state[SESSION_CURRENT_SYNSET])
        else:
            self._render_synset_list()
    
    def _render_synset_list(self):
        """Render a list of all synsets with pagination."""
        st.subheader("📋 All Synsets")
        
        # Show total count
        total_synsets = len(st.session_state[SESSION_LOADED_SYNSETS])
        st.write(f"Total loaded synsets: {total_synsets}")
        
        if total_synsets == 0:
            return
        
        # Pagination settings
        total_pages = (total_synsets + SYNSETS_PER_PAGE - 1) // SYNSETS_PER_PAGE
        current_page = st.session_state[SESSION_LIST_PAGE]
        
        # Ensure current page is valid
        if current_page >= total_pages:
            st.session_state[SESSION_LIST_PAGE] = 0
            current_page = 0
        
        # Calculate range for current page
        start_idx = current_page * SYNSETS_PER_PAGE
        end_idx = min(start_idx + SYNSETS_PER_PAGE, total_synsets)
        
        # Render pagination controls
        self._render_pagination_controls(current_page, total_pages, start_idx, end_idx, total_synsets)
        
        # Create and display synset table
        self._render_synset_table(start_idx, end_idx)
    
    def _render_pagination_controls(self, current_page: int, total_pages: int, 
                                   start_idx: int, end_idx: int, total_synsets: int):
        """Render pagination controls."""
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️ First", disabled=(current_page == 0)):
                st.session_state[SESSION_LIST_PAGE] = 0
                st.rerun()
        
        with col2:
            if st.button("◀️ Previous", disabled=(current_page == 0)):
                st.session_state[SESSION_LIST_PAGE] = current_page - 1
                st.rerun()
        
        with col3:
            st.write(f"Page {current_page + 1} of {total_pages} "
                    f"(showing {start_idx + 1}-{end_idx} of {total_synsets})")
        
        with col4:
            if st.button("Next ▶️", disabled=(current_page >= total_pages - 1)):
                st.session_state[SESSION_LIST_PAGE] = current_page + 1
                st.rerun()
        
        with col5:
            if st.button("Last ⏭️", disabled=(current_page >= total_pages - 1)):
                st.session_state[SESSION_LIST_PAGE] = total_pages - 1
                st.rerun()
    
    def _render_synset_table(self, start_idx: int, end_idx: int):
        """Render the synset table for the current page."""
        # Create a DataFrame for current page
        synset_data = []
        for i, synset in enumerate(st.session_state[SESSION_LOADED_SYNSETS][start_idx:end_idx]):
            usage_indicator = " 💡" if synset.usage else ""
            definition = synset.definition
            if len(definition) > MAX_DEFINITION_LENGTH:
                definition = definition[:MAX_DEFINITION_LENGTH] + "..."
            
            synset_data.append({
                'Index': start_idx + i,
                'ID': synset.id,
                'POS': synset.pos,
                'Synonyms': ', '.join([s.get('literal', '') for s in synset.synonyms]),
                'Definition': definition,
                'Usage': "Yes" + usage_indicator if synset.usage else "No"
            })
        
        if synset_data:
            # Quick selection dropdown for current page
            selected_idx = st.selectbox(
                "Select a synset to view details:",
                range(len(synset_data)),
                format_func=lambda x: f"{synset_data[x]['ID']}: {synset_data[x]['Synonyms'][:MAX_DISPLAY_TEXT_LENGTH]}..."
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("👁️ View Selected Synset"):
                    global_idx = start_idx + selected_idx
                    self._navigate_to_synset_by_index(global_idx)
            
            with col2:
                if st.button("🚀 Start Sequential Review from Selected"):
                    global_idx = start_idx + selected_idx
                    self._navigate_to_synset_by_index(global_idx)
            
            # Display the table
            _require_pandas()
            df = pd.DataFrame(synset_data)
            st.dataframe(df, use_container_width=True)
    
    def _navigate_to_synset_by_index(self, index: int):
        """Navigate to a synset by its index."""
        st.session_state[SESSION_CURRENT_SYNSET] = st.session_state[SESSION_LOADED_SYNSETS][index]
        st.session_state[SESSION_CURRENT_INDEX] = index
        st.rerun()
    
    def _render_synset_details(self, synset: Synset):
        """Render detailed view of a synset with navigation."""
        # Ensure parser is synced before looking up relations
        self._ensure_parser_synced()
        
        st.subheader(f"📖 Synset Details: {synset.id}")
        
        # Navigation controls
        self._render_synset_navigation()
        
        # Quick jump functionality
        self._render_quick_jump()
        
        # Synset information sections
        self._render_synset_basic_info(synset)
        self._render_synset_quality_info(synset)
        self._render_synset_content(synset)
        self._render_synset_relations(synset)
        self._render_synset_technical_info(synset)
    
    def _render_synset_navigation(self):
        """Render navigation controls for synset browsing."""
        total_synsets = len(st.session_state[SESSION_LOADED_SYNSETS])
        current_idx = st.session_state[SESSION_CURRENT_INDEX]
        
        # Navigation buttons
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 2, 1, 1, 1])
        
        with col1:
            if st.button("← Back to List"):
                st.session_state[SESSION_CURRENT_SYNSET] = None
                st.rerun()
        
        with col2:
            if st.button("⏮️ First", disabled=(current_idx == 0)):
                self._navigate_to_synset_by_index(0)
        
        with col3:
            st.write(f"Synset {current_idx + 1} of {total_synsets}")
        
        with col4:
            if st.button("◀️ Previous", disabled=(current_idx == 0)):
                self._navigate_to_synset_by_index(current_idx - 1)
        
        with col5:
            if st.button("Next ▶️", disabled=(current_idx >= total_synsets - 1)):
                self._navigate_to_synset_by_index(current_idx + 1)
        
        with col6:
            if st.button("Last ⏭️", disabled=(current_idx >= total_synsets - 1)):
                self._navigate_to_synset_by_index(total_synsets - 1)
    
    def _render_quick_jump(self):
        """Render quick jump functionality."""
        total_synsets = len(st.session_state[SESSION_LOADED_SYNSETS])
        current_idx = st.session_state[SESSION_CURRENT_INDEX]
        
        with st.expander("🎯 Quick Jump"):
            jump_to_idx = st.number_input(
                "Jump to synset number:",
                min_value=1,
                max_value=total_synsets,
                value=current_idx + 1,
                step=1
            ) - 1  # Convert to 0-based index
            
            if st.button("Jump"):
                self._navigate_to_synset_by_index(jump_to_idx)
    
    def _render_synset_basic_info(self, synset: Synset):
        """Render basic synset information."""
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Part of Speech", synset.pos)
        with col2:
            st.metric("BCS", synset.bcs)
        with col3:
            st.metric("Natural Language", synset.nl)
        with col4:
            domain = synset.domain if synset.domain else "Not specified"
            st.metric("Domain", domain)
    
    def _render_synset_quality_info(self, synset: Synset):
        """Render quality and provenance information."""
        st.subheader("👤 Translation Quality Info")
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_translator_info(synset)
        
        with col2:
            self._render_sentiment_info(synset)
        
        # Usage indicator
        if synset.usage:
            st.success("💡 **Has usage example** - High quality synset")
        else:
            st.warning("⚠️ **No usage example** - Consider verifying translation")
    
    def _render_translator_info(self, synset: Synset):
        """Render translator information."""
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
    
    def _render_sentiment_info(self, synset: Synset):
        """Render sentiment analysis information."""
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
    
    def _render_synset_content(self, synset: Synset):
        """Render synset content (synonyms, definition, usage)."""
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
    
    def _render_synset_relations(self, synset: Synset):
        """Render Serbian WordNet relations section."""
        st.subheader("🔗 Serbian WordNet Relations")
        if synset.ilr:
            st.write(f"Found {len(synset.ilr)} relations:")
            
            # Process relations data
            relation_data, available_relations = self._process_synset_relations(synset)
            
            # Display relations table
            if relation_data:
                _require_pandas()
                df_relations = pd.DataFrame(relation_data)
                st.dataframe(df_relations, use_container_width=True, hide_index=True)
                
                # Navigation buttons for available relations
                if available_relations:
                    self._render_relation_navigation(available_relations)
                
                # Show statistics
                self._render_relation_statistics(available_relations, len(synset.ilr))
            
            # Debug information
            self._render_debug_info()
        else:
            st.write("No relations available")
    
    def _process_synset_relations(self, synset: Synset) -> tuple:
        """Process synset relations and return data for display."""
        relation_data = []
        available_relations = []
        
        for relation in synset.ilr:
            target_id = relation['target']
            rel_type = relation['type']
            
            # Check if target synset is loaded
            target_synset = self.parser.get_synset_by_id(target_id)
            
            if target_synset:
                # Get synonyms (literals) from target synset
                target_literals = ', '.join([
                    s.get('literal', '') for s in target_synset.synonyms
                ]) if target_synset.synonyms else 'No synonyms'
                
                # Truncate definition if too long
                target_definition = target_synset.definition
                if len(target_definition) > MAX_DEFINITION_LENGTH:
                    target_definition = target_definition[:MAX_DEFINITION_LENGTH] + "..."
                
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
        
        return relation_data, available_relations
    
    def _render_relation_navigation(self, available_relations: List):
        """Render navigation buttons for available relations."""
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
                        target_literals = ', '.join([
                            s.get('literal', '') for s in target_synset.synonyms[:MAX_DISPLAYED_SYNONYMS]
                        ])  # First 2 synonyms
                        if len(target_literals) > MAX_DISPLAY_TEXT_LENGTH:
                            target_literals = target_literals[:MAX_DISPLAY_TEXT_LENGTH] + "..."
                        
                        button_label = f"→ {target_literals}"
                        if st.button(
                            button_label, 
                            key=f"nav_{relation['target']}", 
                            help=f"Go to {relation['target']}"
                        ):
                            self._navigate_to_synset(target_synset)
    
    def _render_relation_statistics(self, available_relations: List, total_relations: int):
        """Render relation statistics."""
        available_count = len(available_relations)
        unavailable_count = total_relations - available_count
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Available Relations", available_count)
        with col2:
            st.metric("External Relations", unavailable_count)
        with col3:
            st.metric("Total Relations", total_relations)
    
    def _render_debug_info(self):
        """Render debug information."""
        with st.expander("🐛 Debug Info"):
            st.write(f"Parser has {len(self.parser.synsets)} synsets loaded")
            st.write(f"Session state has {len(st.session_state[SESSION_LOADED_SYNSETS])} synsets")
            st.write("Sample of parser synset IDs:")
            parser_ids = list(self.parser.synsets.keys())[:5]
            for sid in parser_ids:
                st.write(f"  - {sid}")
    
    def _render_synset_technical_info(self, synset: Synset):
        """Render technical information section."""
        with st.expander("🔧 Technical Information"):
            if synset.sumo:
                st.write(f"**SUMO:** {synset.sumo['concept']} ({synset.sumo['type']})")
            
            # Full stamp details
            if synset.stamp:
                st.write(f"**Full Stamp:** {synset.stamp}")
            
            # Raw sentiment values
            if synset.sentiment:
                st.write("**Raw Sentiment Values:**")
                st.write(f"  • Positive: {synset.sentiment['positive']}")
                st.write(f"  • Negative: {synset.sentiment['negative']}")
    
    def _render_pairing_panel(self):
        """Render the pairing panel for selecting English/Serbian pairs."""
        st.header("🎯 Synset Pairing")
        
        if st.session_state[SESSION_CURRENT_SYNSET]:
            serbian_synset = st.session_state[SESSION_CURRENT_SYNSET]
            
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
                    # Accept Serbian 'b' for adverbs and normalize to 'r' for NLTK lookups
                    numeric_id_match = re.match(r"ENG30-(\d+)-([nvarb])", english_id)
                    if numeric_id_match:
                        numeric_id = numeric_id_match.group(1)
                        pos = numeric_id_match.group(2)
                        if pos == 'b':  # Serbian adverb tag
                            pos = 'r'   # Princeton/NLTK adverb tag
                        
                        # Try to get synset by offset
                        english_synset = self.synset_handler.get_synset_by_offset(numeric_id, pos)
                        
                        if english_synset:
                            st.write(f"**Definition:** {english_synset.get('definition', 'N/A')}")
                            st.write(f"**Lemmas:** {', '.join(english_synset.get('lemmas', []))}")
                            if english_synset.get('examples'):
                                st.write(f"**Examples:** {'; '.join(english_synset.get('examples', []))}")
                            st.write(f"**WordNet Name:** {english_synset.get('name', 'N/A')}")
                            
                            # Display Princeton WordNet Relations
                            self._display_english_relations(english_synset)
                            
                            # Pairing button
                            if st.button("✅ Add to Pairs"):
                                pair = {
                                    'serbian_id': serbian_synset.id,
                                    'serbian_synonyms': [s.get('literal', '') for s in serbian_synset.synonyms],
                                    'serbian_definition': serbian_synset.definition,
                                    'serbian_usage': serbian_synset.usage,
                                    'serbian_pos': serbian_synset.pos,
                                    'serbian_domain': serbian_synset.domain,
                                    'serbian_relations': self._extract_serbian_relations(serbian_synset),
                                    'english_id': english_id,
                                    'english_definition': english_synset.get('definition', ''),
                                    'english_lemmas': english_synset.get('lemmas', []),
                                    'english_examples': english_synset.get('examples', []),
                                    'english_pos': english_synset.get('pos', ''),
                                    'english_name': english_synset.get('name', ''),
                                    'english_relations': english_synset.get('relations', {}),
                                    'pairing_metadata': {
                                        'pair_type': 'automatic',
                                        'quality_score': quality_score,
                                        'translator': stamp_parts[0] if serbian_synset.stamp and serbian_synset.stamp.split() else 'Unknown',
                                        'translation_date': ' '.join(stamp_parts[1:]) if serbian_synset.stamp and len(serbian_synset.stamp.split()) > 1 else 'Unknown'
                                    }
                                }
                                
                                # Check if pair already exists
                                existing = any(p['serbian_id'] == serbian_synset.id for p in st.session_state[SESSION_SELECTED_PAIRS])
                                if not existing:
                                    st.session_state[SESSION_SELECTED_PAIRS].append(pair)
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
                                            'serbian_pos': serbian_synset.pos,
                                            'serbian_domain': serbian_synset.domain,
                                            'serbian_relations': self._extract_serbian_relations(serbian_synset),
                                            'english_id': eng_synset['name'],
                                            'english_definition': eng_synset['definition'],
                                            'english_lemmas': eng_synset['lemmas'],
                                            'english_examples': eng_synset.get('examples', []),
                                            'english_pos': eng_synset.get('pos', ''),
                                            'english_name': eng_synset['name'],
                                            'english_relations': eng_synset.get('relations', {}),
                                            'pairing_metadata': {
                                                'pair_type': 'manual',
                                                'quality_score': quality_score,
                                                'translator': stamp_parts[0] if serbian_synset.stamp and serbian_synset.stamp.split() else 'Unknown',
                                                'translation_date': ' '.join(stamp_parts[1:]) if serbian_synset.stamp and len(serbian_synset.stamp.split()) > 1 else 'Unknown'
                                            }
                                        }
                                        
                                        existing = any(p['serbian_id'] == serbian_synset.id for p in st.session_state[SESSION_SELECTED_PAIRS])
                                        if not existing:
                                            st.session_state[SESSION_SELECTED_PAIRS].append(pair)
                                            st.success("Manual pair added!")
                                            st.rerun()
                                        else:
                                            st.warning("This pair is already selected!")
                        else:
                            st.write("No English synsets found")
                    except Exception as e:
                        st.error(f"Error searching English synsets: {e}")
        
        # Display current pairs - this was missing!
        self._render_current_pairs()
    
    def _render_current_pairs(self):
        """Render the current selected pairs."""
        if st.session_state[SESSION_SELECTED_PAIRS]:
            st.subheader("📋 Selected Pairs")
            
            for i, pair in enumerate(st.session_state[SESSION_SELECTED_PAIRS]):
                with st.expander(f"Pair {i+1}: {pair['serbian_id']} ↔ {pair['english_id']}"):
                    # Header with metadata
                    metadata = pair.get('pairing_metadata', {})
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"**Type:** {metadata.get('pair_type', 'unknown').title()}")
                    with col2:
                        st.info(f"**Quality:** {metadata.get('quality_score', 0):.1f}/2.5")
                    with col3:
                        st.info(f"**Translator:** {metadata.get('translator', 'Unknown')}")
                    
                    # Main content in two columns
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**🇷🇸 Serbian:**")
                        st.write(f"**ID:** {pair['serbian_id']}")
                        st.write(f"**POS:** {pair.get('serbian_pos', 'N/A')}")
                        st.write(f"**Domain:** {pair.get('serbian_domain', 'N/A')}")
                        st.write(f"**Synonyms:** {', '.join(pair['serbian_synonyms'])}")
                        st.write(f"**Definition:** {pair['serbian_definition']}")
                        if pair.get('serbian_usage'):
                            st.write(f"**Usage:** *{pair['serbian_usage']}*")
                        
                        # Serbian Relations Summary
                        serbian_relations = pair.get('serbian_relations', {})
                        if serbian_relations.get('total_relations', 0) > 0:
                            st.write(f"**Relations:** {serbian_relations['total_relations']} total")
                            relations_by_type = serbian_relations.get('relations_by_type', {})
                            for rel_type, relations in relations_by_type.items():
                                available_count = sum(1 for r in relations if r.get('available', False))
                                st.write(f"  • {rel_type}: {available_count}/{len(relations)} available")
                        else:
                            st.write("**Relations:** None")
                    
                    with col2:
                        st.write("**🇺🇸 English:**")
                        st.write(f"**ID:** {pair['english_id']}")
                        st.write(f"**Name:** {pair.get('english_name', 'N/A')}")
                        st.write(f"**POS:** {pair.get('english_pos', 'N/A')}")
                        st.write(f"**Lemmas:** {', '.join(pair['english_lemmas'])}")
                        st.write(f"**Definition:** {pair['english_definition']}")
                        if pair.get('english_examples'):
                            st.write(f"**Examples:** {'; '.join(pair['english_examples'])}")
                        
                        # English Relations Summary
                        english_relations = pair.get('english_relations', {})
                        if english_relations:
                            total_eng_relations = 0
                            for rel_type, rel_list in english_relations.items():
                                if rel_type != 'lemma_relations' and rel_list:
                                    total_eng_relations += len(rel_list)
                            
                            # Count lemma relations
                            if english_relations.get('lemma_relations'):
                                for lemma_data in english_relations['lemma_relations'].values():
                                    for rel_list in lemma_data.values():
                                        total_eng_relations += len(rel_list)
                            
                            st.write(f"**Princeton WordNet Relations:** {total_eng_relations} total")
                            
                            # Show relation types with counts
                            for rel_type, rel_list in english_relations.items():
                                if rel_type != 'lemma_relations' and rel_list:
                                    st.write(f"  • {rel_type.replace('_', ' ').title()}: {len(rel_list)}")
                        else:
                            st.write("**Princeton WordNet Relations:** None")
                    
                    # Expandable sections for detailed relations
                    if serbian_relations.get('available_relations') or english_relations:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if serbian_relations.get('available_relations'):
                                with st.expander(f"🔗 Serbian Relations Details ({len(serbian_relations['available_relations'])})"):
                                    for rel in serbian_relations['available_relations']:
                                        st.write(f"**{rel['type'].title()}:** {rel['target_id']}")
                                        if rel.get('target_synonyms'):
                                            st.write(f"  Synonyms: {', '.join(rel['target_synonyms'][:3])}")
                                        if rel.get('target_definition'):
                                            st.write(f"  Definition: {rel['target_definition'][:100]}...")
                                        st.write("---")
                        
                        with col2:
                            if english_relations:
                                with st.expander(f"🔗 English Relations Details ({sum(len(v) for k, v in english_relations.items() if k != 'lemma_relations' and v)})"):
                                    for rel_type, rel_list in english_relations.items():
                                        if rel_type != 'lemma_relations' and rel_list:
                                            st.write(f"**{rel_type.replace('_', ' ').title()}:**")
                                            for rel in rel_list[:3]:  # Show first 3
                                                if isinstance(rel, dict):
                                                    st.write(f"  • {rel.get('name', 'N/A')}")
                                                    st.write(f"    {rel.get('definition', 'N/A')[:80]}...")
                                                else:
                                                    st.write(f"  • {rel}")
                                            if len(rel_list) > 3:
                                                st.write(f"  ... and {len(rel_list) - 3} more")
                                            st.write("---")
                    
                    if st.button(f"🗑️ Remove Pair {i+1}", key=f"remove_{i}"):
                        st.session_state[SESSION_SELECTED_PAIRS].pop(i)
                        st.success("Pair removed!")
                        st.rerun()
    
    def _extract_english_id(self, synset_id: str) -> Optional[str]:
        """Extract English WordNet ID if present."""
        if synset_id.startswith('ENG30-'):
            # Normalize Serbian adverb POS '-b' to English '-r' for lookups
            if synset_id.endswith('-b'):
                return synset_id[:-1] + 'r'
            return synset_id
        return None
    
    def _generate_serbian_id_from_english(self, english_synset_name: str) -> str:
        """
        Generate Serbian WordNet ID format from English synset name.
        
        Args:
            english_synset_name: English synset name like 'dog.n.01'
            
        Returns:
            Serbian WordNet ID format like 'ENG30-{offset}-{pos}'
        """
        if not english_synset_name or english_synset_name == 'N/A':
            return 'N/A'
        
        try:
            # Parse the English synset name (e.g., 'dog.n.01')
            parts = english_synset_name.split('.')
            if len(parts) >= 2:
                word = parts[0]
                pos = parts[1]
                sense = parts[2] if len(parts) > 2 else '01'
                
                # Try to get the synset to extract its offset
                try:
                    from nltk.corpus import wordnet as wn
                    synset = wn.synset(english_synset_name)
                    offset = synset.offset()
                    
                    # Format as Serbian WordNet ID
                    serbian_id = f"ENG30-{offset:08d}-{pos}"
                    return serbian_id
                except:
                    # If we can't get the synset, try to construct from the name
                    return f"ENG30-????????-{pos}"
            else:
                return 'Invalid format'
        except Exception as e:
            return f'Error: {str(e)[:20]}...'
    
    def _check_serbian_synset_exists(self, serbian_id: str) -> str:
        """
        Check if a Serbian synset ID exists in the loaded data.
        
        Args:
            serbian_id: Serbian WordNet ID to check
            
        Returns:
            Status emoji and text
        """
        if serbian_id in ['N/A', 'Invalid format'] or serbian_id.startswith('Error:'):
            return ''
        
        # Ensure parser is synced
        self._ensure_parser_synced()
        
        # Check if the synset exists in loaded data
        if serbian_id in self.parser.synsets:
            return '✅'
        else:
            return '❌'
    
    def _extract_serbian_relations(self, synset: 'Synset') -> Dict:
        """
        Extract Serbian WordNet relations in a format useful for translators.
        
        Args:
            synset: Serbian synset object
            
        Returns:
            Dictionary with relation information for translation context
        """
        relations_info = {
            'total_relations': len(synset.ilr) if synset.ilr else 0,
            'relations_by_type': {},
            'available_relations': [],
            'external_relations': []
        }
        
        if not synset.ilr:
            return relations_info
        
        # Ensure parser is synced
        self._ensure_parser_synced()
        
        # Group relations by type and extract useful information
        for relation in synset.ilr:
            rel_type = relation['type']
            target_id = relation['target']
            
            if rel_type not in relations_info['relations_by_type']:
                relations_info['relations_by_type'][rel_type] = []
            
            # Try to get target synset information
            target_synset = self.parser.get_synset_by_id(target_id)
            
            relation_info = {
                'type': rel_type,
                'target_id': target_id,
                'available': target_synset is not None
            }
            
            if target_synset:
                # Add detailed information for available relations
                relation_info.update({
                    'target_synonyms': [s.get('literal', '') for s in target_synset.synonyms] if target_synset.synonyms else [],
                    'target_definition': target_synset.definition,
                    'target_usage': target_synset.usage,
                    'target_pos': target_synset.pos,
                    'target_domain': target_synset.domain
                })
                relations_info['available_relations'].append(relation_info)
            else:
                relations_info['external_relations'].append(relation_info)
            
            relations_info['relations_by_type'][rel_type].append(relation_info)
        
        return relations_info
    
    def _display_english_relations(self, english_synset: Dict):
        """Display Princeton WordNet relations for an English synset."""
        relations = english_synset.get('relations', {})
        
        if not relations:
            st.write("**Princeton WordNet Relations:** No relations found")
            return
        
        # Count total relations
        total_relations = 0
        for rel_type, rel_list in relations.items():
            if rel_type != 'lemma_relations' and rel_list:
                total_relations += len(rel_list)
        
        # Count lemma relations
        lemma_relations_count = 0
        if relations.get('lemma_relations'):
            for lemma_data in relations['lemma_relations'].values():
                for rel_list in lemma_data.values():
                    lemma_relations_count += len(rel_list)
        
        total_relations += lemma_relations_count
        
        if total_relations == 0:
            st.write("**Princeton WordNet Relations:** No relations available")
            return
        
        st.write(f"**🔗 Princeton WordNet Relations** ({total_relations} total):")
        
        # Create relation data for display
        relation_data = []
        
        # Add synset-level relations
        for rel_type, rel_list in relations.items():
            if rel_type != 'lemma_relations' and rel_list:
                for rel in rel_list:
                    if isinstance(rel, dict):
                        # Generate Serbian WordNet equivalent ID and check if it exists
                        serbian_equivalent = self._generate_serbian_id_from_english(rel.get('name', ''))
                        exists_status = self._check_serbian_synset_exists(serbian_equivalent)
                        
                        relation_data.append({
                            'Type': rel_type.replace('_', ' ').title(),
                            'Target': rel.get('name', 'N/A'),
                            'Serbian ID': f"{serbian_equivalent} {exists_status}",
                            'Definition': rel.get('definition', 'N/A')[:80] + ('...' if len(rel.get('definition', '')) > 80 else '')
                        })
                    else:
                        # Generate Serbian WordNet equivalent ID and check if it exists
                        serbian_equivalent = self._generate_serbian_id_from_english(str(rel))
                        exists_status = self._check_serbian_synset_exists(serbian_equivalent)
                        
                        relation_data.append({
                            'Type': rel_type.replace('_', ' ').title(),
                            'Target': str(rel),
                            'Serbian ID': f"{serbian_equivalent} {exists_status}",
                            'Definition': 'N/A'
                        })
        
        # Add lemma-level relations
        if relations.get('lemma_relations'):
            for lemma, lemma_rels in relations['lemma_relations'].items():
                for rel_type, rel_list in lemma_rels.items():
                    for rel in rel_list:
                        if isinstance(rel, dict):
                            # Generate Serbian WordNet equivalent ID and check if it exists
                            serbian_equivalent = self._generate_serbian_id_from_english(rel.get('name', ''))
                            exists_status = self._check_serbian_synset_exists(serbian_equivalent)
                            
                            relation_data.append({
                                'Type': f"Lemma {rel_type.replace('_', ' ').title()}",
                                'Target': f"{rel.get('lemma', 'N/A')} ({rel.get('name', 'N/A')})",
                                'Serbian ID': f"{serbian_equivalent} {exists_status}",
                                'Definition': rel.get('definition', 'N/A')[:80] + ('...' if len(rel.get('definition', '')) > 80 else '')
                            })
        
        # Display relations table if we have data
        if relation_data:
            _require_pandas()
            df_relations = pd.DataFrame(relation_data)
            st.dataframe(df_relations, use_container_width=True, hide_index=True)
        else:
            st.write("No displayable relations found")
    
    def _export_pairs(self):
        """Export selected pairs to JSON."""
        if st.session_state[SESSION_SELECTED_PAIRS]:
            _require_pandas()
            data = {
                'pairs': st.session_state[SESSION_SELECTED_PAIRS],
                'metadata': {
                    'total_pairs': len(st.session_state[SESSION_SELECTED_PAIRS]),
                    'created_by': 'Serbian WordNet Synset Browser',
                    'format_version': EXPORT_FORMAT_VERSION,
                    'export_timestamp': pd.Timestamp.now().isoformat(),
                    'includes_relations': True,
                    'includes_metadata': True,
                    'description': 'Enhanced export with Serbian and English relations for translation context'
                }
            }
            
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📥 Download Enhanced Pairs (JSON)",
                data=json_str,
                file_name="serbian_english_synset_pairs_enhanced.json",
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