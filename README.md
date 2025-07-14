# WordNet AutoTranslate

Automatic translation system with WordNet integration supporting NWO (namespace-with-owner) format for DSPy and Princeton WordNet.

## Features

- **NWO Format Support**: Use namespace-with-owner format for provider specification (e.g., `@dspy/wordnet`, `@princeton/wordnet`)
- **DSPy Integration**: Advanced language model integration with WordNet enhancement
- **Princeton WordNet Integration**: Direct integration with the Princeton WordNet database
- **Backward Compatibility**: Supports legacy provider formats alongside NWO format
- **Multi-Provider Support**: Use multiple providers simultaneously with intelligent routing

## Installation

```bash
pip install wordnet_autotranslate
```

Or install from source:

```bash
git clone https://github.com/sasa5linkar/wordnet_autotranslate-.git
cd wordnet_autotranslate-
pip install -e .
```

## Quick Start

### Basic Usage

```python
from wordnet_autotranslate import WordNetAutoTranslator

# Initialize with default configuration
translator = WordNetAutoTranslator()

# Translate text
result = translator.translate("Hello world", source_lang="en", target_lang="es")
print(result)  # "hola mundo"
```

### Using NWO Format Providers

```python
from wordnet_autotranslate import WordNetAutoTranslator, Config

# Configure with NWO format providers
config_data = {
    'providers': {
        'dspy_wordnet': '@dspy/wordnet@2.0.0',
        'princeton_wordnet': '@princeton/wordnet@3.0',
        'legacy_wordnet': 'wordnet'  # Backward compatibility
    }
}

translator = WordNetAutoTranslator(config_data)

# Use specific provider with NWO format
result = translator.translate(
    "The cat is sleeping", 
    source_lang="en", 
    target_lang="es",
    provider="@dspy/wordnet"
)

# Use Princeton WordNet provider
result = translator.translate(
    "Artificial intelligence",
    source_lang="en",
    target_lang="fr", 
    provider="@princeton/wordnet@3.0"
)
```

### Configuration File

Create a `config.yaml` file:

```yaml
# NWO format providers
providers:
  dspy_wordnet:
    nwo: "@dspy/wordnet@2.0.0"
    model: "gpt-3.5-turbo"
    temperature: 0.3
    
  princeton_wordnet:
    nwo: "@princeton/wordnet@3.0"
    data_path: "~/nltk_data/corpora/wordnet"
    
  # Legacy format for backward compatibility
  legacy_wordnet: "wordnet"

# Provider-specific configuration
dspy:
  default_model: "gpt-3.5-turbo"
  temperature: 0.3
  wordnet_enhancement: true
  
princeton:
  enable_multilingual: true
  download_missing: true

wordnet:
  default_language: "en"
  cache_synsets: true
```

Load and use the configuration:

```python
from wordnet_autotranslate import Config, WordNetAutoTranslator

config = Config.from_file("config.yaml")
translator = WordNetAutoTranslator(config)

# Translate using configured providers
result = translator.translate("Hello", provider="@dspy/wordnet")
```

## NWO Format Specification

The NWO (namespace-with-owner) format follows this pattern:

```
[@namespace/]name[@version]
```

### Examples

- `@dspy/wordnet` - DSPy WordNet provider
- `@princeton/wordnet@3.0` - Princeton WordNet version 3.0
- `@dspy/wordnet@latest` - DSPy WordNet latest version
- `wordnet` - Legacy format (no namespace)

### Supported Namespaces

- `@dspy/*` - DSPy framework integrations
- `@princeton/*` - Princeton WordNet integrations
- No namespace - Legacy format for backward compatibility

## API Reference

### WordNetAutoTranslator

Main translator class with NWO format support.

```python
translator = WordNetAutoTranslator(config=None)
```

#### Methods

- `translate(text, source_lang="en", target_lang="es", provider=None)` - Translate text
- `get_supported_languages(provider=None)` - Get supported languages
- `get_wordnet_synsets(word, lang="en", provider=None)` - Get WordNet synsets
- `get_available_providers()` - Get all configured providers

### Config

Configuration management with NWO format support.

```python
config = Config(config_data)
config = Config.from_file("config.yaml")
```

#### Methods

- `get_provider(name)` - Get provider by name or NWO string
- `supports_nwo_format()` - Check if NWO format is supported
- `get_nwo_providers()` - Get providers using NWO format
- `get_legacy_providers()` - Get providers using legacy format

### NWOProvider

Represents a provider in NWO format.

```python
provider = NWOProvider.parse("@dspy/wordnet@2.0.0")
```

#### Properties

- `namespace` - Provider namespace (e.g., "dspy")
- `name` - Provider name (e.g., "wordnet") 
- `version` - Provider version (e.g., "2.0.0")

#### Methods

- `parse(nwo_string)` - Parse NWO format string
- `to_string()` - Convert back to NWO format string
- `is_legacy_format()` - Check if legacy format

## WordNet Integration

### DSPy Integration

Uses DSPy framework for enhanced language model translation with WordNet semantic understanding.

```python
# DSPy provider with NWO format
result = translator.translate(
    "The quick brown fox", 
    provider="@dspy/wordnet@2.0.0"
)

# Get synsets via DSPy
synsets = translator.get_wordnet_synsets("fox", provider="@dspy/wordnet")
```

### Princeton WordNet Integration

Direct integration with Princeton WordNet database via NLTK.

```python
# Princeton provider with NWO format
result = translator.translate(
    "Semantic similarity", 
    provider="@princeton/wordnet@3.0"
)

# Search Princeton WordNet synsets
synsets = translator.get_wordnet_synsets("semantic", provider="@princeton/wordnet")
```

## Backward Compatibility

The package maintains full backward compatibility with existing formats:

```python
# Old format still works
translator = WordNetAutoTranslator({
    'providers': {
        'old_wordnet': 'wordnet',
        'new_dspy': '@dspy/wordnet'  # Can mix formats
    }
})

# Both work
result1 = translator.translate("test", provider="wordnet")  # Legacy
result2 = translator.translate("test", provider="@dspy/wordnet")  # NWO
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run specific test files
pytest tests/test_nwo_support.py
pytest tests/test_integrations.py
pytest tests/test_integration.py
```

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Code formatting:

```bash
black wordnet_autotranslate/ tests/
flake8 wordnet_autotranslate/ tests/
mypy wordnet_autotranslate/
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## Changelog

### v0.1.0

- Initial release with NWO format support
- DSPy integration with WordNet enhancement
- Princeton WordNet integration
- Backward compatibility with legacy formats
- Comprehensive test suite
- Configuration file support