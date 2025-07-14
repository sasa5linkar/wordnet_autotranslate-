"""Additional tests for DSPy and Princeton WordNet integrations."""

import pytest
from unittest.mock import Mock, patch

from wordnet_autotranslate.config import Config, NWOProvider
from wordnet_autotranslate.integrations import DSPyIntegration, PrincetonWordNetIntegration


class TestDSPyIntegration:
    """Test DSPy integration with NWO format."""
    
    def test_dspy_initialization(self):
        """Test DSPy integration initialization."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet@2.0.0'
            },
            'dspy': {
                'model': 'gpt-3.5-turbo'
            }
        }
        config = Config(config_data)
        
        # Mock DSPy import
        with patch('wordnet_autotranslate.integrations.dspy_integration.dspy') as mock_dspy:
            integration = DSPyIntegration(config)
            assert integration.config == config
            assert integration.dspy_config == config.get_dspy_config()
    
    def test_dspy_translation(self):
        """Test DSPy translation functionality."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet'
            }
        }
        config = Config(config_data)
        
        with patch('dspy') as mock_dspy:
            integration = DSPyIntegration(config)
            
            provider = NWOProvider.parse("@dspy/wordnet")
            result = integration.translate("hello world", "en", "es", provider)
            
            assert result is not None
            # Should contain Spanish translations for basic words
            assert "hola" in result.lower() or "mundo" in result.lower()
    
    def test_dspy_synsets(self):
        """Test DSPy synset retrieval."""
        config = Config()
        
        with patch('dspy') as mock_dspy:
            integration = DSPyIntegration(config)
            
            synsets = integration.get_synsets(["cat", "dog"])
            
            assert len(synsets) == 2
            assert synsets[0]['word'] == "cat"
            assert synsets[1]['word'] == "dog"
            assert all(s['provider'] == '@dspy/wordnet' for s in synsets)
    
    def test_dspy_supported_languages(self):
        """Test DSPy supported languages."""
        config = Config()
        
        with patch('dspy') as mock_dspy:
            integration = DSPyIntegration(config)
            
            languages = integration.get_supported_languages()
            
            assert isinstance(languages, list)
            assert 'en' in languages
            assert 'es' in languages
            assert len(languages) > 5


class TestPrincetonWordNetIntegration:
    """Test Princeton WordNet integration with NWO format."""
    
    def test_princeton_initialization(self):
        """Test Princeton WordNet integration initialization."""
        config_data = {
            'providers': {
                'princeton_wordnet': '@princeton/wordnet@3.0'
            },
            'princeton': {
                'data_path': '~/nltk_data'
            }
        }
        config = Config(config_data)
        
        # Mock NLTK import
        with patch('nltk') as mock_nltk:
            with patch('wordnet_autotranslate.integrations.princeton_integration.wn') as mock_wn:
                mock_wn.synsets.return_value = []  # Mock successful test
                
                integration = PrincetonWordNetIntegration(config)
                assert integration.config == config
                assert integration.princeton_config == config.get_princeton_config()
    
    def test_princeton_translation(self):
        """Test Princeton WordNet translation functionality."""
        config_data = {
            'providers': {
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        config = Config(config_data)
        
        with patch('nltk') as mock_nltk:
            with patch('wordnet_autotranslate.integrations.princeton_integration.wn') as mock_wn:
                # Mock WordNet synsets
                mock_synset = Mock()
                mock_synset.name.return_value = "cat.n.01"
                mock_synset.definition.return_value = "a small domesticated carnivorous mammal"
                mock_synset.examples.return_value = ["the cat sat on the mat"]
                mock_synset.hypernyms.return_value = []
                mock_synset.hyponyms.return_value = []
                mock_synset.lemmas.return_value = []
                mock_synset.pos.return_value = 'n'
                
                mock_wn.synsets.side_effect = lambda word: [mock_synset] if word == 'cat' else []
                
                integration = PrincetonWordNetIntegration(config)
                
                provider = NWOProvider.parse("@princeton/wordnet")
                result = integration.translate("cat", "en", "es", provider)
                
                assert result is not None
                # Should contain Spanish translation for cat
                assert "gato" in result.lower() or "[es]" in result
    
    def test_princeton_synsets(self):
        """Test Princeton WordNet synset retrieval."""
        config = Config()
        
        with patch('nltk') as mock_nltk:
            with patch('wordnet_autotranslate.integrations.princeton_integration.wn') as mock_wn:
                # Mock WordNet synset
                mock_synset = Mock()
                mock_synset.name.return_value = "cat.n.01"
                mock_synset.definition.return_value = "a small domesticated carnivorous mammal"
                mock_synset.examples.return_value = ["the cat sat on the mat"]
                mock_synset.hypernyms.return_value = []
                mock_synset.hyponyms.return_value = []
                mock_synset.lemmas.return_value = []
                mock_synset.pos.return_value = 'n'
                
                mock_wn.synsets.return_value = [mock_synset]
                
                integration = PrincetonWordNetIntegration(config)
                
                synsets = integration.get_synsets(["cat"])
                
                assert len(synsets) == 1
                assert synsets[0]['word'] == "cat"
                assert synsets[0]['provider'] == '@princeton/wordnet'
                assert len(synsets[0]['synsets']) == 1
                assert synsets[0]['synsets'][0]['name'] == "cat.n.01"
    
    def test_princeton_search_synsets(self):
        """Test Princeton WordNet synset search functionality."""
        config = Config()
        
        with patch('nltk') as mock_nltk:
            with patch('wordnet_autotranslate.integrations.princeton_integration.wn') as mock_wn:
                # Mock WordNet synset
                mock_synset = Mock()
                mock_synset.name.return_value = "cat.n.01"
                mock_synset.definition.return_value = "a small domesticated carnivorous mammal"
                mock_synset.examples.return_value = ["the cat sat on the mat"]
                mock_synset.pos.return_value = 'n'
                
                mock_wn.synsets.return_value = [mock_synset]
                
                integration = PrincetonWordNetIntegration(config)
                
                provider = NWOProvider.parse("@princeton/wordnet")
                results = integration.search_synsets("cat", pos="n", provider=provider)
                
                assert len(results) == 1
                assert results[0]['name'] == "cat.n.01"
                assert results[0]['provider'] == "@princeton/wordnet"


class TestIntegrationInteraction:
    """Test interaction between different integrations."""
    
    def test_nwo_provider_routing(self):
        """Test that NWO providers are routed to correct integrations."""
        config_data = {
            'providers': {
                'dspy_wordnet': '@dspy/wordnet',
                'princeton_wordnet': '@princeton/wordnet'
            }
        }
        
        config = Config(config_data)
        
        # Test provider routing
        dspy_provider = config.get_provider('dspy_wordnet')
        assert dspy_provider.namespace == 'dspy'
        
        princeton_provider = config.get_provider('princeton_wordnet')
        assert princeton_provider.namespace == 'princeton'
    
    def test_version_handling(self):
        """Test handling of provider versions in NWO format."""
        config_data = {
            'providers': {
                'dspy_v2': '@dspy/wordnet@2.0.0',
                'princeton_v3': '@princeton/wordnet@3.0'
            }
        }
        
        config = Config(config_data)
        
        dspy_provider = config.get_provider('dspy_v2')
        assert dspy_provider.version == '2.0.0'
        
        princeton_provider = config.get_provider('princeton_v3')
        assert princeton_provider.version == '3.0'


if __name__ == "__main__":
    pytest.main([__file__])