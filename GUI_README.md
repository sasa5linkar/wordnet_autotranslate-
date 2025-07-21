# Serbian WordNet Synset Browser

A GUI application for browsing Serbian WordNet synsets and pairing them with English synsets for translation training.

## Features

- **XML Synset Loading**: Load Serbian synsets from XML files in the format specified
- **Interactive Browsing**: Navigate between synsets using hyperlinks for ILR relations
- **Search Functionality**: Search synsets by definition or synonyms
- **English-Serbian Pairing**: Automatically link Serbian synsets with English WordNet synsets
- **Manual Pairing**: Manually select English synsets to pair with Serbian ones
- **Export Capability**: Export selected pairs as JSON for machine learning training

## Usage

### Starting the Application

1. **Using the launcher script**:
   ```bash
   python launch_gui.py
   ```

2. **Direct Streamlit launch**:
   ```bash
   streamlit run src/wordnet_autotranslate/gui/synset_browser.py
   ```

3. **Using Python module**:
   ```bash
   python -m streamlit run src/wordnet_autotranslate/gui/synset_browser.py
   ```

The application will open in your web browser at `http://localhost:8501`.

### Loading Synsets

1. **Upload XML File**: Use the file uploader in the sidebar to load your Serbian synset XML file
2. **Use Sample Data**: Click "Load Sample Serbian Synsets" to load example data for testing

### XML Format

The application expects XML files with Serbian synsets in this format:

```xml
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
```

### Browsing Synsets

1. **List View**: Browse all loaded synsets in a table format
2. **Detail View**: Click on any synset to view detailed information
3. **Hyperlink Navigation**: Click on ILR relation buttons to navigate to related synsets
4. **Search**: Use the sidebar search to find specific synsets

### Creating Translation Pairs

1. **Automatic Pairing**: 
   - When viewing a Serbian synset with an English ID (ENG30-xxxxxxxx-x), the app automatically attempts to find the corresponding English synset
   - Click "Add to Pairs" to create the pair

2. **Manual Pairing**:
   - For synsets without automatic English links, use the English synset search
   - Enter an English word and select from the search results
   - Click "Pair with this synset" to create the pair

3. **Managing Pairs**:
   - View all selected pairs in the right panel
   - Remove individual pairs using the "Remove" button
   - Export all pairs as JSON using the "Export Pairs" button

### Exported Data Format

The exported JSON file contains:

```json
{
  "pairs": [
    {
      "serbian_id": "ENG30-03574555-n",
      "serbian_synonyms": ["ustanova"],
      "serbian_definition": "zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja",
      "english_id": "ENG30-03574555-n",
      "english_definition": "a building that houses an administrative unit of some government",
      "english_lemmas": ["institution", "establishment"]
    }
  ],
  "metadata": {
    "total_pairs": 1,
    "created_by": "Serbian WordNet Synset Browser",
    "format_version": "1.0"
  }
}
```

## Technical Details

### Components

- **XmlSynsetParser**: Parses Serbian synsets from XML format
- **SynsetHandler**: Interfaces with English WordNet via NLTK
- **SynsetBrowserApp**: Main Streamlit application

### Dependencies

- Streamlit (web interface)
- NLTK (English WordNet access)
- Pandas (data display)
- XML ElementTree (XML parsing)

### ID Format

Serbian synset IDs in the format `ENG30-xxxxxxxx-x` indicate:
- `ENG30`: WordNet linkage code
- `xxxxxxxx`: WordNet offset
- `x`: Part of speech (n=noun, v=verb, a=adjective, r=adverb)

## Development

To extend the application:

1. **Add New Features**: Modify `synset_browser.py`
2. **Enhance XML Parsing**: Update `xml_synset_parser.py`
3. **Add Tests**: Create test files in the `tests/` directory

## Troubleshooting

1. **XML Parsing Errors**: Ensure XML files are well-formed and contain valid SYNSET elements
2. **English WordNet Not Found**: The application will download WordNet data automatically on first run
3. **Performance Issues**: Large XML files may take time to load; consider splitting into smaller files
4. **Browser Issues**: Ensure JavaScript is enabled and try refreshing the page

## License

This application is part of the WordNet Auto-Translation project and follows the same MIT license.