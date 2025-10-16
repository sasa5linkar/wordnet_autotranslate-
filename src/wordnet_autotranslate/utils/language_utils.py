"""
Language utilities for WordNet auto-translation.
"""

from typing import List, Dict, Set
from pathlib import Path
import re


class LanguageUtils:
    """Utility functions for language processing."""
    
    # Common language codes and names
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Spanish', 
        'fr': 'French',
        'de': 'German',
        'pt': 'Portuguese',
        'it': 'Italian',
        'ru': 'Russian',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean'
    }
    
    @staticmethod
    def is_supported_language(lang_code: str) -> bool:
        """Check if language code is supported."""
        return lang_code.lower() in LanguageUtils.SUPPORTED_LANGUAGES
    
    @staticmethod
    def get_language_name(lang_code: str) -> str:
        """Get full language name from code."""
        return LanguageUtils.SUPPORTED_LANGUAGES.get(
            lang_code.lower(), 
            f"Unknown ({lang_code})"
        )
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\']', '', text)
        
        return text
    
    @staticmethod
    def extract_words(text: str) -> List[str]:
        """Extract words from text."""
        # Simple word extraction
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    # --- POS normalization helpers ---
    # Serbian WordNet XML uses 'b' to denote adverbs (prilog),
    # while Princeton WordNet (NLTK) uses 'r' for adverbs.
    # We normalize when crossing the EN<->SR boundary so lookups work.

    _POS_SRP_TO_ENG = {
        'b': 'r',  # adverb: Serbian 'b' -> English 'r'
        'n': 'n',
        'v': 'v',
        'a': 'a',
        # keep any other tag as-is by default
    }

    _POS_ENG_TO_SRP = {
        'r': 'b',  # adverb: English 'r' -> Serbian 'b'
        'n': 'n',
        'v': 'v',
        'a': 'a',
    }

    @staticmethod
    def normalize_pos_for_english(pos: str) -> str:
        """Map Serbian POS tags to English/Princeton ones (b->r for adverbs).

        Returns a lowercased single-letter POS expected by NLTK WordNet.
        """
        if not pos:
            return pos
        p = pos.lower()
        return LanguageUtils._POS_SRP_TO_ENG.get(p, p)

    @staticmethod
    def normalize_pos_for_serbian(pos: str) -> str:
        """Map English/Princeton POS to Serbian XML ones (r->b for adverbs).

        Returns a lowercased single-letter POS used in Serbian WordNet XML.
        """
        if not pos:
            return pos
        p = pos.lower()
        return LanguageUtils._POS_ENG_TO_SRP.get(p, p)
    @staticmethod
    def load_stopwords(lang_code: str) -> Set[str]:
        """Load stopwords for a language."""
        # Basic English stopwords as fallback
        english_stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'this', 'that', 'these', 'those'
        }
        
        # TODO: Add language-specific stopwords
        if lang_code == 'en':
            return english_stopwords
        elif lang_code == 'es':
            return {'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 
                   'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con',
                   'para', 'al', 'del', 'los', 'las', 'una', 'pero', 'sus'}
        elif lang_code == 'fr':
            return {'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 
                   'avoir', 'que', 'pour', 'dans', 'ce', 'son', 'une', 'sur',
                   'avec', 'ne', 'se', 'pas', 'tout', 'plus', 'par', 'grand'}
        else:
            return english_stopwords
    
    @staticmethod
    def validate_examples_directory(examples_path: Path, lang_code: str) -> Dict[str, bool]:
        """Validate examples directory structure for a language."""
        lang_path = examples_path / lang_code
        
        validation = {
            'directory_exists': lang_path.exists(),
            'words_file_exists': (lang_path / 'words.txt').exists(),
            'sentences_file_exists': (lang_path / 'sentences.txt').exists(),
            'has_content': False
        }
        
        if validation['words_file_exists']:
            words_file = lang_path / 'words.txt'
            try:
                with open(words_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    validation['has_content'] = len(content) > 0
            except Exception:
                validation['has_content'] = False
        
        return validation
    
    @staticmethod
    def get_available_languages(examples_path: Path) -> List[str]:
        """Get list of available languages in examples directory."""
        if not examples_path.exists():
            return []
        
        languages = []
        for item in examples_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it has the required files
                if (item / 'words.txt').exists() or (item / 'sentences.txt').exists():
                    languages.append(item.name)
        
        return sorted(languages)