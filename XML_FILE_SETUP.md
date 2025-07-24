# Working with Serbian WordNet XML Files

## File Security and Privacy

The `wnsrp30.xml` file (Serbian WordNet) should NOT be included in the git repository for the following reasons:

1. **Copyright/Licensing**: WordNet datasets often have specific licensing terms
2. **File Size**: Large XML files can bloat the repository
3. **Privacy**: May contain sensitive or proprietary linguistic data

## Recommended Setup

### 1. Place XML files in the `data` directory:
```
wordnet_autotranslate/
├── data/
│   ├── wnsrp30.xml          # Your Serbian WordNet file
│   ├── other_wordnet.xml    # Other XML files
│   └── README.md            # Instructions
├── src/
└── ...
```

### 2. The `data` directory is automatically ignored by git:
- Files here won't be committed to version control
- Safe for sensitive/copyrighted content
- Keeps your repository clean

### 3. Using the GUI:
1. Start the application: `python launch_gui.py`
2. In the sidebar, look for "Load Local XML File"
3. Select your XML file from the dropdown
4. Click "Load Selected XML File"

## Alternative Methods

### Environment Variable (Advanced):
You can also set an environment variable to point to your XML file location:

```bash
# Windows PowerShell
$env:WORDNET_XML_PATH = "C:\path\to\your\wnsrp30.xml"

# Then run the app
python launch_gui.py
```

### Direct File Upload:
Use the "Upload XML file" option in the sidebar to upload files directly through the web interface.

## File Format
The XML file should contain Serbian synsets in this format:
- `<SYNSET>` elements with ID, POS, SYNONYM, DEF, and ILR relations
- IDs in format like `ENG30-03574555-n` for English WordNet links
- Inter-lingual relations for hypernym/hyponym navigation
