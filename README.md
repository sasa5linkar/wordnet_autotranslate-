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
- **Jupyter Notebook Support**: Interactive development and experimentation environment
- **Extensible Architecture**: Modular design for easy addition of new languages and models

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sasa5linkar/wordnet_autotranslate-.git
cd wordnet_autotranslate-
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Jupyter environment (optional):
```bash
jupyter notebook
```

## Usage

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
│   └── utils/             # Utility functions
├── examples/              # Target language examples
├── notebooks/             # Jupyter notebooks
├── tests/                 # Unit tests
├── requirements.txt       # Python dependencies
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