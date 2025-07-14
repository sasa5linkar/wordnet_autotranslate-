"""
Tests for WordNet Auto-Translation package.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that main modules can be imported."""
    try:
        from wordnet_autotranslate import TranslationPipeline, SynsetHandler, LanguageUtils
        assert TranslationPipeline is not None
        assert SynsetHandler is not None
        assert LanguageUtils is not None
    except ImportError as e:
        pytest.fail(f"Failed to import main modules: {e}")


def test_translation_pipeline_init():
    """Test TranslationPipeline initialization."""
    from wordnet_autotranslate import TranslationPipeline
    
    pipeline = TranslationPipeline()
    assert pipeline.source_lang == 'en'
    assert pipeline.target_lang == 'es'
    
    pipeline_custom = TranslationPipeline(source_lang='en', target_lang='fr')
    assert pipeline_custom.source_lang == 'en'
    assert pipeline_custom.target_lang == 'fr'


def test_language_utils():
    """Test LanguageUtils functions."""
    from wordnet_autotranslate import LanguageUtils
    
    # Test language support
    assert LanguageUtils.is_supported_language('en')
    assert LanguageUtils.is_supported_language('es')
    assert not LanguageUtils.is_supported_language('xyz')
    
    # Test language names
    assert LanguageUtils.get_language_name('en') == 'English'
    assert LanguageUtils.get_language_name('es') == 'Spanish'
    
    # Test text cleaning
    test_text = "  Hello,   world!  "
    cleaned = LanguageUtils.clean_text(test_text)
    assert cleaned == "Hello, world!"
    
    # Test word extraction
    words = LanguageUtils.extract_words("Hello world!")
    assert words == ['hello', 'world']


def test_examples_loading():
    """Test loading examples from files."""
    from wordnet_autotranslate import TranslationPipeline
    
    # Test Spanish examples
    pipeline = TranslationPipeline(target_lang='spanish')
    examples = pipeline.load_examples()
    
    assert 'words' in examples
    assert 'sentences' in examples
    assert isinstance(examples['words'], list)
    assert isinstance(examples['sentences'], list)
    
    # Should have some content if spanish examples exist
    if examples['words']:
        assert len(examples['words']) > 0
        assert all(isinstance(word, str) for word in examples['words'])


if __name__ == "__main__":
    pytest.main([__file__])