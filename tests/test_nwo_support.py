"""Test suite for WordNet AutoTranslate with NWO format support."""

import pytest
import tempfile
import yaml
from pathlib import Path

from wordnet_autotranslate.config import Config, NWOProvider
from wordnet_autotranslate.core import WordNetAutoTranslator


class TestNWOProvider:
    """Test NWO (namespace-with-owner) provider functionality."""
    
    def test_parse_nwo_format(self):
        """Test parsing NWO format strings."""
        # Test standard NWO format
        provider = NWOProvider.parse("@dspy/wordnet")
        assert provider.namespace == "dspy"
        assert provider.name == "wordnet"
        assert provider.version is None
        
        # Test NWO format with version
        provider = NWOProvider.parse("@princeton/wordnet@3.0")
        assert provider.namespace == "princeton"
        assert provider.name == "wordnet"
        assert provider.version == "3.0"
        
        # Test legacy format (no namespace)
        provider = NWOProvider.parse("wordnet")
        assert provider.namespace is None
        assert provider.name == "wordnet"
        assert provider.version is None
        
        # Test name with version but no namespace
        provider = NWOProvider.parse("wordnet@2.1")
        assert provider.namespace is None
        assert provider.name == "wordnet"
        assert provider.version == "2.1"
    
    def test_invalid_nwo_format(self):
        """Test invalid NWO format strings."""
        with pytest.raises(ValueError):
            NWOProvider.parse("@/wordnet")  # Empty namespace
            
        with pytest.raises(ValueError):
            NWOProvider.parse("@namespace/")  # Empty name
            
        with pytest.raises(ValueError):
            NWOProvider.parse("")  # Empty string
    
    def test_to_string(self):
        """Test converting provider back to string format."""
        # Test NWO format
        provider = NWOProvider(namespace="dspy", name="wordnet")
        assert provider.to_string() == "@dspy/wordnet"
        
        # Test NWO format with version
        provider = NWOProvider(namespace="princeton", name="wordnet", version="3.0")
        assert provider.to_string() == "@princeton/wordnet@3.0"
        
        # Test legacy format
        provider = NWOProvider(name="wordnet")
        assert provider.to_string() == "wordnet"
    
    def test_is_legacy_format(self):
        """Test legacy format detection."""
        # NWO format should not be legacy
        provider = NWOProvider.parse("@dspy/wordnet")
        assert not provider.is_legacy_format()
        
        # Legacy format should be detected
        provider = NWOProvider.parse("wordnet")
        assert provider.is_legacy_format()


class TestConfig:
    """Test configuration system with NWO support."""
    
    def test_config_with_nwo_providers(self):
        """Test configuration with NWO format providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet@2.0.0',
                'princeton_wordnet': '@princeton/wordnet@3.0',
                'legacy_wordnet': 'wordnet'
            }
        }
        
        config = Config(config_data)
        
        # Test NWO providers
        dspy_provider = config.get_provider('dspy_wordnet')
        assert dspy_provider.namespace == 'dspy'
        assert dspy_provider.name == 'wordnet'
        assert dspy_provider.version == '2.0.0'
        
        princeton_provider = config.get_provider('princeton_wordnet')
        assert princeton_provider.namespace == 'princeton'
        assert princeton_provider.name == 'wordnet'
        
        # Test legacy provider
        legacy_provider = config.get_provider('legacy_wordnet')
        assert legacy_provider.is_legacy_format()
        assert legacy_provider.name == 'wordnet'
    
    def test_supports_nwo_format(self):
        """Test NWO format support detection."""
        # Configuration with NWO providers
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'legacy_wordnet': 'wordnet'
            }
        }
        config = Config(config_data)
        assert config.supports_nwo_format()
        
        # Configuration with only legacy providers
        config_data = {
            'providers': {
                'legacy_wordnet': 'wordnet'
            }
        }
        config = Config(config_data)
        assert not config.supports_nwo_format()
    
    def test_get_nwo_providers(self):
        """Test getting only NWO format providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet',
                'legacy_wordnet': 'wordnet'
            }
        }
        config = Config(config_data)
        
        nwo_providers = config.get_nwo_providers()
        assert len(nwo_providers) == 2
        assert 'dspy_wordnet' in nwo_providers
        assert 'princeton_wordnet' in nwo_providers
        assert 'legacy_wordnet' not in nwo_providers
    
    def test_get_legacy_providers(self):
        """Test getting only legacy format providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'legacy_wordnet': 'wordnet'
            }
        }
        config = Config(config_data)
        
        legacy_providers = config.get_legacy_providers()
        assert len(legacy_providers) == 1
        assert 'legacy_wordnet' in legacy_providers
        assert 'dspy_wordnet' not in legacy_providers
    
    def test_config_from_file(self):
        """Test loading configuration from YAML file."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet@2.0.0',
                'princeton_wordnet': '@princeton/wordnet'
            },
            'dspy': {
                'model': 'gpt-3.5-turbo'
            },
            'princeton': {
                'data_path': '~/nltk_data'
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.from_file(temp_path)
            
            # Test providers were loaded correctly
            assert len(config.providers) == 2
            assert config.get_provider('dspy_wordnet').namespace == 'dspy'
            
            # Test specific configurations were loaded
            assert config.get_dspy_config()['model'] == 'gpt-3.5-turbo'
            assert config.get_princeton_config()['data_path'] == '~/nltk_data'
            
        finally:
            Path(temp_path).unlink()


class TestWordNetAutoTranslator:
    """Test main translator class with NWO support."""
    
    def test_translator_initialization(self):
        """Test translator initialization with NWO providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Should have both integrations
        assert 'dspy' in translator.integrations
        assert 'princeton' in translator.integrations
        
        # Should recognize NWO providers
        assert translator.config.supports_nwo_format()
    
    def test_translate_with_nwo_provider(self):
        """Test translation using specific NWO provider."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test translation with DSPy provider
        result = translator.translate("hello world", provider="@dspy/wordnet")
        assert result is not None
        assert len(result) > 0
        
        # Test translation with Princeton provider
        result = translator.translate("hello world", provider="@princeton/wordnet")
        assert result is not None
        assert len(result) > 0
    
    def test_translate_with_legacy_provider(self):
        """Test translation with legacy provider format."""
        config_data = {
            'providers': {
                'legacy_wordnet': 'wordnet',
                'dspy_wordnet': '@dspy/wordnet',  # Ensure we have a working provider
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test translation with legacy provider - should work with available integrations
        result = translator.translate("hello world", provider="wordnet")
        assert result is not None
        assert len(result) > 0
    
    def test_get_supported_languages(self):
        """Test getting supported languages for NWO providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test languages for specific providers
        dspy_langs = translator.get_supported_languages("@dspy/wordnet")
        assert 'en' in dspy_langs
        assert 'es' in dspy_langs
        
        princeton_langs = translator.get_supported_languages("@princeton/wordnet")
        assert 'en' in princeton_langs
        
        # Test all supported languages
        all_langs = translator.get_supported_languages()
        assert len(all_langs) > 0
        assert 'en' in all_langs
    
    def test_get_wordnet_synsets(self):
        """Test getting WordNet synsets with NWO providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test synsets with DSPy provider
        synsets = translator.get_wordnet_synsets("cat", provider="@dspy/wordnet")
        assert len(synsets) > 0
        assert synsets[0]['provider'] == '@dspy/wordnet'
        
        # Test synsets with Princeton provider
        synsets = translator.get_wordnet_synsets("cat", provider="@princeton/wordnet")
        assert len(synsets) > 0
        assert synsets[0]['provider'] == '@princeton/wordnet'
    
    def test_get_available_providers(self):
        """Test getting all available providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet',
                'legacy_wordnet': 'wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        providers = translator.get_available_providers()
        
        assert len(providers) == 3
        assert 'dspy_wordnet' in providers
        assert 'princeton_wordnet' in providers
        assert 'legacy_wordnet' in providers
        
        # Check NWO vs legacy providers
        assert not providers['dspy_wordnet'].is_legacy_format()
        assert not providers['princeton_wordnet'].is_legacy_format()
        assert providers['legacy_wordnet'].is_legacy_format()


class TestBackwardCompatibility:
    """Test backward compatibility with existing formats."""
    
    def test_mixed_provider_formats(self):
        """Test using both NWO and legacy formats together."""
        config_data = {
            'providers': {
                'new_dspy': '@dspy/wordnet@2.0.0',
                'new_princeton': '@princeton/wordnet@3.0',
                'old_wordnet': 'wordnet',
                'old_format': 'legacy_provider'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Should support both formats
        assert translator.config.supports_nwo_format()
        
        # Test translation with each format
        result_nwo = translator.translate("test", provider="@dspy/wordnet")
        result_legacy = translator.translate("test", provider="wordnet")
        
        assert result_nwo is not None
        assert result_legacy is not None
    
    def test_provider_fallback(self):
        """Test fallback behavior for unknown providers."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet'
            }
        }
        
        translator = WordNetAutoTranslator(config_data)
        
        # Test with completely invalid provider format - should raise error  
        with pytest.raises(ValueError):
            translator.translate("test", provider="@invalid@format@too@many@at@symbols")