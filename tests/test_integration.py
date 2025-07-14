"""Integration tests to verify the complete system works."""

import pytest
import tempfile
import yaml
from pathlib import Path

from wordnet_autotranslate import WordNetAutoTranslator, Config, NWOProvider


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def test_complete_nwo_workflow(self):
        """Test complete workflow with NWO format providers."""
        # Create test configuration
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet@2.0.0',
                'princeton_wordnet': '@princeton/wordnet@3.0',
                'legacy_wordnet': 'wordnet'
            },
            'dspy': {
                'model': 'gpt-3.5-turbo',
                'temperature': 0.3
            },
            'princeton': {
                'enable_multilingual': True
            },
            'wordnet': {
                'default_language': 'en',
                'max_synsets_per_word': 5
            }
        }
        
        # Initialize translator
        translator = WordNetAutoTranslator(config_data)
        
        # Test with different providers
        test_text = "The cat is sleeping"
        
        # Test DSPy provider
        result_dspy = translator.translate(
            test_text, 
            source_lang="en", 
            target_lang="es",
            provider="@dspy/wordnet"
        )
        assert result_dspy is not None
        assert len(result_dspy) > 0
        
        # Test Princeton provider
        result_princeton = translator.translate(
            test_text,
            source_lang="en",
            target_lang="es", 
            provider="@princeton/wordnet"
        )
        assert result_princeton is not None
        assert len(result_princeton) > 0
        
        # Test legacy provider
        result_legacy = translator.translate(
            test_text,
            source_lang="en",
            target_lang="es",
            provider="wordnet"
        )
        assert result_legacy is not None
        assert len(result_legacy) > 0
    
    def test_config_file_workflow(self):
        """Test workflow using configuration file."""
        config_data = {
            'providers': {
                'main_dspy': '@dspy/wordnet@latest',
                'backup_princeton': '@princeton/wordnet@3.0'
            },
            'translation': {
                'default_source_lang': 'en',
                'default_target_lang': 'es',
                'enhance_with_synsets': True
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Load config from file
            config = Config.from_file(temp_path)
            translator = WordNetAutoTranslator(config)
            
            # Test translation
            result = translator.translate("Hello world", provider="@dspy/wordnet")
            assert result is not None
            
            # Test synset retrieval
            synsets = translator.get_wordnet_synsets("hello", provider="@dspy/wordnet")
            assert len(synsets) > 0
            assert synsets[0]['provider'] == '@dspy/wordnet'
            
        finally:
            Path(temp_path).unlink()
    
    def test_backward_compatibility_workflow(self):
        """Test complete backward compatibility with legacy formats."""
        # Configuration mixing NWO and legacy formats
        config_data = {
            'providers': {
                'new_dspy': '@dspy/wordnet',
                'new_princeton': '@princeton/wordnet',
                'old_wordnet': 'wordnet',
                'old_provider': 'legacy_provider'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test that both formats work
        test_text = "test translation"
        
        # NWO format
        result_nwo = translator.translate(test_text, provider="@dspy/wordnet")
        assert result_nwo is not None
        
        # Legacy format
        result_legacy = translator.translate(test_text, provider="wordnet")
        assert result_legacy is not None
        
        # Verify provider lists include both types
        providers = translator.get_available_providers()
        nwo_count = sum(1 for p in providers.values() if not p.is_legacy_format())
        legacy_count = sum(1 for p in providers.values() if p.is_legacy_format())
        
        assert nwo_count >= 2  # At least DSPy and Princeton
        assert legacy_count >= 2  # At least 2 legacy providers
    
    def test_language_support_integration(self):
        """Test language support across integrations."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test language support for each provider
        dspy_langs = translator.get_supported_languages("@dspy/wordnet")
        princeton_langs = translator.get_supported_languages("@princeton/wordnet")
        all_langs = translator.get_supported_languages()
        
        # Basic assertions
        assert 'en' in dspy_langs
        assert 'en' in princeton_langs
        assert 'en' in all_langs
        
        # All languages should be the union of individual providers
        assert len(all_langs) >= max(len(dspy_langs), len(princeton_langs))
    
    def test_synset_integration(self):
        """Test WordNet synset functionality across providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        test_word = "cat"
        
        # Test synsets from DSPy provider
        dspy_synsets = translator.get_wordnet_synsets(test_word, provider="@dspy/wordnet")
        assert len(dspy_synsets) > 0
        assert dspy_synsets[0]['provider'] == '@dspy/wordnet'
        # Word might be cleaned, so check if it contains the original word
        assert test_word in dspy_synsets[0]['word'] or dspy_synsets[0]['word'] in test_word
        
        # Test synsets from Princeton provider
        princeton_synsets = translator.get_wordnet_synsets(test_word, provider="@princeton/wordnet")
        assert len(princeton_synsets) > 0
        assert princeton_synsets[0]['provider'] == '@princeton/wordnet'
        # Word might be cleaned, so check if it contains the original word
        assert test_word in princeton_synsets[0]['word'] or princeton_synsets[0]['word'] in test_word
        
        # Test default synsets (no provider specified)
        default_synsets = translator.get_wordnet_synsets(test_word)
        assert len(default_synsets) > 0
    
    def test_error_handling_integration(self):
        """Test error handling in integrated system."""
        config_data = {
            'providers': {
                'valid_provider': '@dspy/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test invalid provider
        with pytest.raises(ValueError, match="Unknown provider"):
            translator.translate("test", provider="@invalid/provider")
        
        # Test invalid NWO format
        with pytest.raises(ValueError):
            NWOProvider.parse("invalid_format")
        
        # Test missing provider configuration
        empty_translator = WordNetAutoTranslator({})
        with pytest.raises(RuntimeError):
            empty_translator.translate("test", provider="@dspy/wordnet")


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""
    
    def test_multi_provider_translation(self):
        """Test using multiple providers for better translation."""
        config_data = {
            'providers': {
                'primary': '@dspy/wordnet@2.0.0',
                'fallback': '@princeton/wordnet@3.0',
                'legacy': 'wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        test_sentences = [
            "The quick brown fox jumps over the lazy dog",
            "Artificial intelligence is transforming technology",
            "The cat sat on the mat"
        ]
        
        for sentence in test_sentences:
            # Try primary provider
            result_primary = translator.translate(sentence, provider="@dspy/wordnet")
            assert result_primary is not None
            
            # Try fallback provider
            result_fallback = translator.translate(sentence, provider="@princeton/wordnet")
            assert result_fallback is not None
            
            # Try legacy provider
            result_legacy = translator.translate(sentence, provider="wordnet")
            assert result_legacy is not None
    
    def test_configuration_variations(self):
        """Test different configuration variations."""
        # Minimal configuration
        minimal_config = {
            'providers': {
                'simple': '@dspy/wordnet'
            }
        }
        translator_minimal = WordNetAutoTranslator(minimal_config)
        assert len(translator_minimal.integrations) > 0
        
        # Full configuration
        full_config = {
            'providers': {
                'dspy_latest': '@dspy/wordnet@latest',
                'princeton_stable': '@princeton/wordnet@3.0',
                'legacy_backup': 'wordnet'
            },
            'dspy': {
                'model': 'gpt-4',
                'temperature': 0.1,
                'max_tokens': 2000
            },
            'princeton': {
                'data_path': '~/custom_wordnet',
                'enable_multilingual': True,
                'download_missing': False
            },
            'wordnet': {
                'default_language': 'en',
                'cache_synsets': True,
                'max_synsets_per_word': 10
            }
        }
        translator_full = WordNetAutoTranslator(full_config)
        assert len(translator_full.integrations) > 0
        assert translator_full.config.supports_nwo_format()
    
    def test_version_compatibility(self):
        """Test version compatibility in NWO format."""
        config_data = {
            'providers': {
                'dspy_v1': '@dspy/wordnet@1.0.0',
                'dspy_v2': '@dspy/wordnet@2.0.0', 
                'princeton_v3': '@princeton/wordnet@3.0',
                'princeton_latest': '@princeton/wordnet@latest'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # All providers should be recognized
        providers = translator.get_available_providers()
        assert len(providers) == 4
        
        # Each should have correct version information
        assert providers['dspy_v1'].version == '1.0.0'
        assert providers['dspy_v2'].version == '2.0.0'
        assert providers['princeton_v3'].version == '3.0'
        assert providers['princeton_latest'].version == 'latest'
        
        # All should work for translation
        test_text = "version test"
        for provider_name in providers:
            provider_nwo = providers[provider_name].to_string()
            result = translator.translate(test_text, provider=provider_nwo)
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])