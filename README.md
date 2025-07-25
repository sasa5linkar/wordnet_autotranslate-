# WordNet Auto-Translation

A core tool for automatic expansion of WordNet in less-resourced languages, using precision words and examples from target languages. This project leverages DSPy Pipelines & Prompt Optimization to load synsets in both English and target languages, utilizing a trained translation pipeline.

## Overview

This project aims to bridge the gap in WordNet coverage for less-resourced languages by:
- Loading existing synsets from both English and target languages
- Using DSPy pipelines for optimized prompt-based translation
- Leveraging precision words and contextual examples for accurate translations
- Providing tools for automatic WordNet expansion

## Features

- **DSPy Integration**: Uses DSPy pipelines and prompt optimization for robust translation
- **Multi-language Support**: Handles English as source and various target languages
- **Example-based Learning**: Utilizes examples from target languages for better context
- **Serbian WordNet GUI**: Interactive browser for Serbian synsets with English pairing functionality
- **Jupyter Notebook Support**: Interactive development and experimentation environment
- **Extensible Architecture**: Modular design for easy addition of new languages and models

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sasa5linkar/wordnet_autotranslate-.git
cd wordnet_autotranslate-
```

2. Install the package with dependencies:
```bash
# Basic installation
pip install -e .

# Or with optional dependencies
pip install -e ".[notebooks,gui,dev]"
```

3. Set up Jupyter environment (optional):
```bash
# Install with notebook dependencies
pip install -e ".[notebooks]"
jupyter notebook
```

## Usage

### Serbian WordNet Synset Browser (GUI)

Launch the interactive GUI for browsing and pairing Serbian synsets:

```bash
# Using the launcher script
python launch_gui.py

# Or directly with Streamlit
streamlit run src/wordnet_autotranslate/gui/synset_browser.py
```

The GUI provides:
- Interactive browsing of Serbian synsets from XML files
- Hyperlink navigation between related synsets
- Automatic and manual pairing with English synsets
- Export functionality for training data

See [GUI_README.md](GUI_README.md) for detailed usage instructions.

### Basic Translation Pipeline

```python
from wordnet_autotranslate import TranslationPipeline

# Initialize pipeline for target language
pipeline = TranslationPipeline(
    source_lang='en',
    target_lang='your_target_language'
)

# Load synsets
english_synsets = pipeline.load_english_synsets()
target_synsets = pipeline.load_target_synsets()

# Run translation
translated_synsets = pipeline.translate(english_synsets)
```

### Serbian WordNet Expansion

For Serbian-specific experiments, use `SerbianWordnetPipeline` which bundles
English synset loading, placeholder generation and XML export:

```python
from pathlib import Path
from wordnet_autotranslate import SerbianWordnetPipeline

pipeline = SerbianWordnetPipeline(pilot_limit=100)
pipeline.run(Path("./output/srpwn_generated.xml"))

### Serbian Synset Parsing

```python
from wordnet_autotranslate import XmlSynsetParser

# Parse Serbian synsets from XML
parser = XmlSynsetParser()
synsets = parser.parse_xml_file('serbian_synsets.xml')

# Search and browse synsets
results = parser.search_synsets('ustanova')
related = parser.get_related_synsets(synsets[0])
```

### Using Examples

Place your target language examples in the `examples/` folder:
```
examples/
├── spanish/
│   ├── words.txt
│   └── sentences.txt
├── french/
│   ├── words.txt
│   └── sentences.txt
└── your_language/
    ├── words.txt
    └── sentences.txt
```

### Jupyter Notebooks

Explore the interactive notebooks in the `notebooks/` directory for:
- Language analysis
- Translation pipeline experimentation
- WordNet expansion workflows

## Project Structure

```
wordnet_autotranslate/
├── src/                    # Core source code
│   ├── pipelines/         # DSPy translation pipelines
│   ├── models/            # Language models and synset handlers
│   │   ├── synset_handler.py      # English WordNet interface
│   │   └── xml_synset_parser.py   # Serbian synset XML parser
│   ├── gui/               # Graphical user interface
│   │   └── synset_browser.py      # Streamlit browser app
│   └── utils/             # Utility functions
├── examples/              # Target language examples
├── notebooks/             # Jupyter notebooks
├── tests/                 # Unit tests
├── launch_gui.py          # GUI launcher script
├── GUI_README.md          # GUI documentation
├── pyproject.toml         # Project configuration and dependencies
└── README.md             # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your target language examples to `examples/your_language/`
4. Test your changes
5. Submit a pull request

## Target Languages

This project supports expansion to any language. Current examples include:
- Spanish
- French
- German
- Portuguese
- Add your language!

## Requirements

- Python 3.8+
- DSPy framework
- Jupyter (for interactive development)
- NLTK (for WordNet access)
- Transformers (for language models)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- WordNet project for the foundational lexical database
- DSPy team for the optimization framework
- Contributors to less-resourced language resources