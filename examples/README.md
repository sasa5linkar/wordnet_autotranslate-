# Examples Directory

This directory contains precision words and sentence examples for various target languages used in WordNet auto-translation.

## Directory Structure

Each language should have its own subdirectory with the following files:
- `words.txt`: Precision words in the target language
- `sentences.txt`: Example sentences providing context for translations

## Supported Languages

Currently included examples:
- **Spanish** (`spanish/`): Comprehensive word lists and sentence examples
- **French** (`french/`): Basic vocabulary and contextual sentences
- **German** (`german/`): Ready for your contributions
- **Portuguese** (`portuguese/`): Ready for your contributions

## Adding New Languages

To add a new target language:

1. Create a new directory: `examples/your_language/`
2. Add `words.txt` with precision words
3. Add `sentences.txt` with contextual examples
4. Follow the format of existing examples

## File Formats

### words.txt
```
# Language WordNet Examples

## Precision Words
word1
word2
word3

## Context Examples
Short example sentence 1.
Short example sentence 2.
```

### sentences.txt
```
# Language Sentence Examples for WordNet Translation

Longer contextual sentence demonstrating word usage.
Another sentence with multiple target words for translation.
```

## Usage in Translation Pipeline

These examples are used by the DSPy pipeline to:
- Provide context for better translations
- Validate translation quality
- Fine-tune prompt optimization
- Generate training data for models

## Contributing

Please contribute examples for additional languages by following the established format and creating pull requests.