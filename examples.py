"""Example scripts demonstrating NWO format usage."""

from wordnet_autotranslate import WordNetAutoTranslator, Config, NWOProvider


def example_basic_usage():
    """Basic usage example."""
    print("=== Basic Usage Example ===")
    
    # Simple initialization
    translator = WordNetAutoTranslator()
    
    # Basic translation
    result = translator.translate("Hello world", target_lang="es")
    print(f"Translation: {result}")
    
    print()


def example_nwo_providers():
    """NWO format providers example."""
    print("=== NWO Format Providers Example ===")
    
    # Configure with NWO format providers
    config_data = {
        'providers': {
            'dspy_main': '@dspy/wordnet@2.0.0',
            'princeton_backup': '@princeton/wordnet@3.0',
            'legacy_fallback': 'wordnet'
        }
    }
    
    translator = WordNetAutoTranslator(config_data)
    
    test_text = "The cat is sleeping on the warm mat"
    
    # Test each provider
    providers_to_test = [
        ("@dspy/wordnet", "DSPy WordNet"),
        ("@princeton/wordnet", "Princeton WordNet"),
        ("wordnet", "Legacy WordNet")
    ]
    
    for provider_nwo, description in providers_to_test:
        try:
            result = translator.translate(
                test_text,
                source_lang="en",
                target_lang="es", 
                provider=provider_nwo
            )
            print(f"{description}: {result}")
        except Exception as e:
            print(f"{description}: Error - {e}")
    
    print()


def example_configuration_file():
    """Configuration file example."""
    print("=== Configuration File Example ===")
    
    # Load from the example config file
    try:
        config = Config.from_file("config.yaml")
        translator = WordNetAutoTranslator(config)
        
        print("Loaded configuration:")
        print(f"- Supports NWO format: {config.supports_nwo_format()}")
        print(f"- Number of providers: {len(config.providers)}")
        
        # Show provider types
        nwo_providers = config.get_nwo_providers()
        legacy_providers = config.get_legacy_providers()
        
        print(f"- NWO providers: {len(nwo_providers)}")
        for name, provider in nwo_providers.items():
            print(f"  {name}: {provider.to_string()}")
            
        print(f"- Legacy providers: {len(legacy_providers)}")
        for name, provider in legacy_providers.items():
            print(f"  {name}: {provider.to_string()}")
        
        # Test translation with configured provider
        result = translator.translate(
            "Configuration example",
            provider="@dspy/wordnet"
        )
        print(f"Translation result: {result}")
        
    except FileNotFoundError:
        print("config.yaml not found - skipping this example")
    except Exception as e:
        print(f"Error loading configuration: {e}")
    
    print()


def example_synset_exploration():
    """WordNet synset exploration example."""
    print("=== WordNet Synset Exploration Example ===")
    
    config_data = {
        'providers': {
            'dspy_wordnet': '@dspy/wordnet',
            'princeton_wordnet': '@princeton/wordnet'
        }
    }
    
    translator = WordNetAutoTranslator(config_data)
    
    test_words = ["cat", "intelligence", "translate"]
    
    for word in test_words:
        print(f"\nSynsets for '{word}':")
        
        # Get synsets from different providers
        for provider in ["@dspy/wordnet", "@princeton/wordnet"]:
            try:
                synsets = translator.get_wordnet_synsets(word, provider=provider)
                
                print(f"  Provider: {provider}")
                if synsets and synsets[0]['synsets']:
                    for synset in synsets[0]['synsets'][:2]:  # Show first 2
                        print(f"    {synset['name']}: {synset['definition']}")
                else:
                    print(f"    No synsets found")
                    
            except Exception as e:
                print(f"    Error: {e}")
    
    print()


def example_language_support():
    """Language support example."""
    print("=== Language Support Example ===")
    
    config_data = {
        'providers': {
            'dspy_wordnet': '@dspy/wordnet',
            'princeton_wordnet': '@princeton/wordnet'
        }
    }
    
    translator = WordNetAutoTranslator(config_data)
    
    # Show supported languages for each provider
    providers = ["@dspy/wordnet", "@princeton/wordnet"]
    
    for provider in providers:
        try:
            languages = translator.get_supported_languages(provider)
            print(f"Provider {provider} supports {len(languages)} languages:")
            print(f"  {', '.join(languages[:10])}{'...' if len(languages) > 10 else ''}")
        except Exception as e:
            print(f"Provider {provider}: Error - {e}")
    
    # Show all supported languages
    all_languages = translator.get_supported_languages()
    print(f"\nAll providers combined support {len(all_languages)} languages:")
    print(f"  {', '.join(all_languages[:15])}{'...' if len(all_languages) > 15 else ''}")
    
    print()


def example_version_handling():
    """Version handling example."""
    print("=== Version Handling Example ===")
    
    # Parse different version formats
    version_examples = [
        "@dspy/wordnet@2.0.0",
        "@princeton/wordnet@3.0", 
        "@dspy/wordnet@latest",
        "@princeton/wordnet",
        "wordnet@1.0",
        "wordnet"
    ]
    
    print("Parsing NWO format examples:")
    for example in version_examples:
        try:
            provider = NWOProvider.parse(example)
            print(f"  '{example}' -> namespace='{provider.namespace}', name='{provider.name}', version='{provider.version}'")
            print(f"    Legacy format: {provider.is_legacy_format()}")
            print(f"    Back to string: '{provider.to_string()}'")
        except Exception as e:
            print(f"  '{example}' -> Error: {e}")
    
    print()


def example_backward_compatibility():
    """Backward compatibility example."""
    print("=== Backward Compatibility Example ===")
    
    # Configuration mixing old and new formats
    config_data = {
        'providers': {
            'modern_dspy': '@dspy/wordnet@2.0.0',
            'modern_princeton': '@princeton/wordnet@3.0',
            'old_wordnet': 'wordnet',
            'old_provider': 'legacy_translation'
        }
    }
    
    translator = WordNetAutoTranslator(config_data)
    
    test_text = "backward compatibility test"
    
    print("Testing mixed provider formats:")
    
    # Test modern NWO format
    try:
        result = translator.translate(test_text, provider="@dspy/wordnet")
        print(f"NWO format (@dspy/wordnet): {result}")
    except Exception as e:
        print(f"NWO format error: {e}")
    
    # Test legacy format
    try:
        result = translator.translate(test_text, provider="wordnet")
        print(f"Legacy format (wordnet): {result}")
    except Exception as e:
        print(f"Legacy format error: {e}")
    
    # Show provider analysis
    providers = translator.get_available_providers()
    nwo_count = sum(1 for p in providers.values() if not p.is_legacy_format())
    legacy_count = sum(1 for p in providers.values() if p.is_legacy_format())
    
    print(f"Provider analysis: {nwo_count} NWO, {legacy_count} legacy")
    
    print()


def main():
    """Run all examples."""
    print("WordNet AutoTranslate - NWO Format Examples")
    print("=" * 50)
    print()
    
    examples = [
        example_basic_usage,
        example_nwo_providers,
        example_configuration_file,
        example_synset_exploration,
        example_language_support,
        example_version_handling,
        example_backward_compatibility
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"Error in {example_func.__name__}: {e}")
            print()


if __name__ == "__main__":
    main()