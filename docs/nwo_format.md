# NWO Format Specification

This document describes the NWO (Namespace-With-Owner) format used in WordNet AutoTranslate.

## Format

The NWO format follows this pattern:

```
[@namespace/]name[@version]
```

Where:
- `namespace` (optional): The namespace or owner of the provider
- `name` (required): The name of the provider  
- `version` (optional): The version specification

## Examples

### NWO Format Examples

```
@dspy/wordnet              # DSPy WordNet provider, latest version
@dspy/wordnet@2.0.0        # DSPy WordNet provider, version 2.0.0
@princeton/wordnet         # Princeton WordNet provider, latest version
@princeton/wordnet@3.0     # Princeton WordNet provider, version 3.0
@dspy/wordnet@latest       # DSPy WordNet provider, explicit latest version
```

### Legacy Format Examples (Backward Compatibility)

```
wordnet                    # Legacy format, no namespace
wordnet@1.0                # Legacy format with version
legacy_provider            # Legacy format, custom name
```

## Supported Namespaces

### @dspy/*

Providers in the `dspy` namespace use the DSPy framework for language model integration with WordNet enhancement.

- **@dspy/wordnet**: Main DSPy WordNet provider
- **@dspy/wordnet@2.0.0**: Specific version of DSPy WordNet provider

### @princeton/*

Providers in the `princeton` namespace use Princeton WordNet directly via NLTK.

- **@princeton/wordnet**: Main Princeton WordNet provider  
- **@princeton/wordnet@3.0**: Specific version of Princeton WordNet

## Configuration

### YAML Configuration

```yaml
providers:
  # NWO format providers
  dspy_main:
    nwo: "@dspy/wordnet@2.0.0"
    model: "gpt-3.5-turbo"
    temperature: 0.3
    
  princeton_backup:
    nwo: "@princeton/wordnet@3.0"
    data_path: "~/nltk_data"
    
  # Simple string format
  dspy_simple: "@dspy/wordnet"
  princeton_simple: "@princeton/wordnet"
  
  # Legacy format for backward compatibility
  legacy_wordnet: "wordnet"
```

### Python Configuration

```python
from wordnet_autotranslate import Config, NWOProvider

# Parse NWO strings
provider = NWOProvider.parse("@dspy/wordnet@2.0.0")
print(f"Namespace: {provider.namespace}")  # "dspy"
print(f"Name: {provider.name}")            # "wordnet"  
print(f"Version: {provider.version}")      # "2.0.0"

# Configuration with NWO providers
config_data = {
    'providers': {
        'dspy_wordnet': '@dspy/wordnet@2.0.0',
        'princeton_wordnet': '@princeton/wordnet@3.0',
        'legacy_wordnet': 'wordnet'
    }
}

config = Config(config_data)
```

## Usage

### Direct Provider Specification

```python
from wordnet_autotranslate import WordNetAutoTranslator

translator = WordNetAutoTranslator()

# Use specific NWO provider
result = translator.translate(
    "Hello world", 
    provider="@dspy/wordnet@2.0.0"
)

# Use Princeton WordNet
result = translator.translate(
    "Hello world",
    provider="@princeton/wordnet"
)

# Use legacy format
result = translator.translate(
    "Hello world",
    provider="wordnet"
)
```

### CLI Usage

```bash
# Use NWO format provider
wordnet-autotranslate "Hello world" --provider "@dspy/wordnet@2.0.0"

# Use Princeton WordNet
wordnet-autotranslate "Hello world" --provider "@princeton/wordnet"

# Use legacy format
wordnet-autotranslate "Hello world" --provider "wordnet"
```

## Version Handling

### Version Specification

- `@dspy/wordnet@2.0.0`: Specific semantic version
- `@dspy/wordnet@latest`: Explicit latest version
- `@dspy/wordnet`: Implicit latest version (no version specified)

### Version Comparison

The system treats version specifications as strings. For semantic version comparison, implement custom logic based on your needs.

## Provider Resolution

### Resolution Order

1. Check configured providers by name
2. Try to parse as direct NWO format string
3. Route to appropriate integration based on namespace
4. For legacy format, try integrations in order: DSPy, Princeton

### Example Resolution

```python
# These are equivalent if "dspy_main" is configured as "@dspy/wordnet"
translator.translate("text", provider="dspy_main")
translator.translate("text", provider="@dspy/wordnet")
```

## Backward Compatibility

### Mixed Format Support

You can use both NWO and legacy formats in the same configuration:

```yaml
providers:
  # New NWO format
  modern_dspy: "@dspy/wordnet@2.0.0"
  modern_princeton: "@princeton/wordnet@3.0"
  
  # Legacy format
  old_wordnet: "wordnet"
  old_provider: "legacy_translation"
```

### Migration Guide

To migrate from legacy format to NWO format:

1. **Identify current providers**: List all provider names in your configuration
2. **Map to namespaces**: Determine which providers should use which namespaces
3. **Add version information**: Specify versions if needed
4. **Update configuration**: Replace simple strings with NWO format
5. **Test compatibility**: Ensure both formats work during transition

Before:
```yaml
providers:
  main_wordnet: "wordnet"
  backup_wordnet: "wordnet_backup"
```

After:
```yaml
providers:
  main_wordnet: "@dspy/wordnet@2.0.0"
  backup_wordnet: "@princeton/wordnet@3.0"
  
  # Keep legacy for compatibility during transition
  legacy_wordnet: "wordnet"
```

## Error Handling

### Invalid Format Errors

```python
from wordnet_autotranslate import NWOProvider

# These will raise ValueError
NWOProvider.parse("@/wordnet")      # Empty namespace
NWOProvider.parse("@namespace/")    # Empty name
NWOProvider.parse("")               # Empty string
```

### Unknown Provider Errors

```python
# This will raise ValueError if provider not found
translator.translate("text", provider="@unknown/provider")
```

### Integration Errors

If an integration is not available, the system will:
1. Log a warning
2. Try fallback integrations for legacy providers
3. Raise RuntimeError if no integrations are available

## Best Practices

### Naming Conventions

- Use lowercase for namespaces: `@dspy/`, `@princeton/`
- Use descriptive names: `wordnet`, `translation`, `nlp`
- Use semantic versioning: `@dspy/wordnet@2.0.0`

### Configuration Organization

```yaml
# Group by functionality
providers:
  # Primary providers
  primary_dspy: "@dspy/wordnet@2.0.0"
  primary_princeton: "@princeton/wordnet@3.0"
  
  # Backup providers  
  backup_dspy: "@dspy/wordnet@1.0.0"
  backup_princeton: "@princeton/wordnet@2.0"
  
  # Legacy compatibility
  legacy_wordnet: "wordnet"
```

### Version Management

- Pin versions in production: `@dspy/wordnet@2.0.0`
- Use latest in development: `@dspy/wordnet`
- Document version requirements in your project

### Performance Considerations

- NWO parsing is fast but happens on every provider lookup
- Cache provider objects when making many calls with the same provider
- Configure providers in configuration files rather than parsing strings repeatedly