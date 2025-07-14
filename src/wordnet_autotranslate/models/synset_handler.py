"""
Synset Handler for WordNet operations.
"""

from typing import List, Dict, Optional

try:
    import nltk
    from nltk.corpus import wordnet as wn
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


class SynsetHandler:
    """Handles WordNet synset operations."""
    
    def __init__(self, language: str = 'en'):
        """
        Initialize synset handler.
        
        Args:
            language: Language code for WordNet operations
        """
        self.language = language
        self._ensure_wordnet_data()
    
    def _ensure_wordnet_data(self):
        """Ensure WordNet data is downloaded."""
        if not NLTK_AVAILABLE:
            print("NLTK not available. Please install with: pip install nltk")
            return
            
        try:
            wn.synsets('test')
        except LookupError:
            print("Downloading WordNet data...")
            nltk.download('wordnet')
            nltk.download('omw-1.4')
    
    def get_synsets(self, word: str) -> List[Dict]:
        """
        Get synsets for a word.
        
        Args:
            word: Word to get synsets for
            
        Returns:
            List of synset dictionaries
        """
        if not NLTK_AVAILABLE:
            print("NLTK not available. Please install with: pip install nltk")
            return []
            
        synsets = wn.synsets(word)
        result = []
        
        for synset in synsets:
            synset_data = {
                'name': synset.name(),
                'definition': synset.definition(),
                'examples': synset.examples(),
                'lemmas': [lemma.name() for lemma in synset.lemmas()],
                'pos': synset.pos(),
                'hypernyms': [h.name() for h in synset.hypernyms()],
                'hyponyms': [h.name() for h in synset.hyponyms()]
            }
            result.append(synset_data)
        
        return result
    
    def get_all_synsets(self, pos: Optional[str] = None) -> List[Dict]:
        """
        Get all synsets, optionally filtered by part of speech.
        
        Args:
            pos: Part of speech filter ('n', 'v', 'a', 'r')
            
        Returns:
            List of all synsets
        """
        all_synsets = wn.all_synsets(pos=pos) if pos else wn.all_synsets()
        result = []
        
        for synset in all_synsets:
            synset_data = {
                'name': synset.name(),
                'definition': synset.definition(),
                'examples': synset.examples(),
                'lemmas': [lemma.name() for lemma in synset.lemmas()],
                'pos': synset.pos()
            }
            result.append(synset_data)
        
        return result
    
    def search_synsets(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search synsets by query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching synsets
        """
        synsets = wn.synsets(query)[:limit]
        result = []
        
        for synset in synsets:
            synset_data = {
                'name': synset.name(),
                'definition': synset.definition(),
                'examples': synset.examples(),
                'lemmas': [lemma.name() for lemma in synset.lemmas()],
                'pos': synset.pos()
            }
            result.append(synset_data)
        
        return result