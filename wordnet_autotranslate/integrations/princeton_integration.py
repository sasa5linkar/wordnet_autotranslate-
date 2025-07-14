"""Princeton WordNet integration with NWO format support."""

import logging
from typing import Dict, List, Optional, Any
from ..config import Config, NWOProvider

logger = logging.getLogger(__name__)


class PrincetonWordNetIntegration:
    """Integration with Princeton WordNet supporting NWO format."""
    
    def __init__(self, config: Config):
        """Initialize Princeton WordNet integration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.princeton_config = config.get_princeton_config()
        self._setup_wordnet()
    
    def _setup_wordnet(self) -> None:
        """Set up Princeton WordNet."""
        try:
            import nltk
            from nltk.corpus import wordnet as wn
            
            self.nltk = nltk
            self.wn = wn
            
            # Ensure WordNet data is available
            try:
                self.wn.synsets('test')
            except LookupError:
                logger.info("Downloading WordNet data...")
                nltk.download('wordnet')
                nltk.download('omw-1.4')
            
            # Configure based on NWO providers
            nwo_providers = {
                name: provider 
                for name, provider in self.config.providers.items()
                if provider.namespace == 'princeton'
            }
            
            logger.info(f"Initialized Princeton WordNet with {len(nwo_providers)} NWO providers")
            
        except ImportError:
            logger.warning("NLTK not available - install with: pip install nltk")
            self.nltk = None
            self.wn = None
    
    def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        provider: Optional[NWOProvider] = None
    ) -> str:
        """Translate text using Princeton WordNet.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            provider: NWO provider specification
            
        Returns:
            Translated text
        """
        if not self.wn:
            raise RuntimeError("Princeton WordNet not available")
        
        # Get WordNet synsets for semantic understanding
        words = text.split()
        synsets = self.get_synsets(words, source_lang)
        
        # Translate using WordNet semantic relationships
        translated = self._wordnet_translate(text, synsets, source_lang, target_lang, provider)
        
        return translated
    
    def _wordnet_translate(
        self, 
        text: str, 
        synsets: List[Dict[str, Any]], 
        source_lang: str, 
        target_lang: str,
        provider: Optional[NWOProvider]
    ) -> str:
        """Perform translation using WordNet semantic relationships.
        
        Args:
            text: Original text
            synsets: WordNet synsets for semantic context
            source_lang: Source language
            target_lang: Target language
            provider: NWO provider specification
            
        Returns:
            Translated text
        """
        provider_info = f" via {provider.to_string()}" if provider else ""
        logger.info(f"Princeton WordNet translating '{text}' from {source_lang} to {target_lang}{provider_info}")
        
        # Mock translation using WordNet relationships
        # In a real implementation, this would use multilingual WordNet
        # or semantic similarity for translation
        
        words = text.split()
        translated_words = []
        
        for i, word in enumerate(words):
            clean_word = ''.join(c for c in word if c.isalnum()).lower()
            
            # Use synset information for better translation
            word_synsets = synsets[i]['synsets'] if i < len(synsets) else []
            
            if word_synsets and target_lang == 'es':
                # Mock Spanish translation based on semantic categories
                translated = self._get_semantic_translation(clean_word, word_synsets, target_lang)
                # Preserve original case and punctuation
                if translated != clean_word:
                    translated_word = word.replace(clean_word, translated)
                    translated_words.append(translated_word)
                else:
                    translated_words.append(word)
            else:
                translated_words.append(word)
        
        result = ' '.join(translated_words)
        return result if result != text else f"[{target_lang}] {text}"
    
    def _get_semantic_translation(
        self, 
        word: str, 
        synsets: List[Dict[str, Any]], 
        target_lang: str
    ) -> str:
        """Get translation based on semantic category.
        
        Args:
            word: Word to translate
            synsets: WordNet synsets for the word
            target_lang: Target language
            
        Returns:
            Translated word or original if no translation found
        """
        # Mock semantic-based translation
        # In reality, this would use multilingual WordNet or cross-lingual embeddings
        
        semantic_translations = {
            'es': {
                # Animals
                'cat': 'gato',
                'dog': 'perro',
                'bird': 'pájaro',
                'fish': 'pez',
                
                # Objects
                'house': 'casa',
                'book': 'libro',
                'car': 'coche',
                'table': 'mesa',
                
                # Actions
                'run': 'correr',
                'walk': 'caminar',
                'eat': 'comer',
                'sleep': 'dormir',
                
                # Adjectives
                'big': 'grande',
                'small': 'pequeño',
                'good': 'bueno',
                'bad': 'malo',
                
                # Common words
                'hello': 'hola',
                'world': 'mundo',
                'water': 'agua',
                'fire': 'fuego',
            }
        }
        
        if target_lang in semantic_translations:
            return semantic_translations[target_lang].get(word, word)
        
        return word
    
    def get_synsets(self, words: List[str], lang: str = 'en') -> List[Dict[str, Any]]:
        """Get Princeton WordNet synsets for words.
        
        Args:
            words: List of words to look up
            lang: Language code
            
        Returns:
            List of synset information
        """
        if not self.wn:
            return []
        
        synsets = []
        
        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum()).lower()
            
            try:
                # Get synsets from Princeton WordNet
                word_synsets = self.wn.synsets(clean_word)
                
                synset_data = {
                    'word': word,
                    'lang': lang,
                    'synsets': [],
                    'provider': '@princeton/wordnet'
                }
                
                for synset in word_synsets:
                    synset_info = {
                        'name': synset.name(),
                        'definition': synset.definition(),
                        'examples': synset.examples(),
                        'hypernyms': [h.name() for h in synset.hypernyms()],
                        'hyponyms': [h.name() for h in synset.hyponyms()],
                        'synonyms': [lemma.name() for lemma in synset.lemmas()],
                        'pos': synset.pos(),  # Part of speech
                    }
                    synset_data['synsets'].append(synset_info)
                
                synsets.append(synset_data)
                
            except Exception as e:
                logger.warning(f"Error getting synsets for '{word}': {e}")
                # Return empty synset data for failed lookups
                synsets.append({
                    'word': word,
                    'lang': lang,
                    'synsets': [],
                    'provider': '@princeton/wordnet',
                    'error': str(e)
                })
        
        logger.debug(f"Retrieved synsets for {len(words)} words via Princeton WordNet")
        return synsets
    
    def get_supported_languages(self) -> List[str]:
        """Get list of languages supported by Princeton WordNet.
        
        Returns:
            List of language codes
        """
        # Princeton WordNet primarily supports English, but has some multilingual data
        return ['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'zh']
    
    def get_wordnet_version(self) -> str:
        """Get Princeton WordNet version information.
        
        Returns:
            Version string
        """
        try:
            if self.wn:
                # Try to get version from a test synset
                synsets = self.wn.synsets('test')
                return "Princeton WordNet 3.0+"  # Default version
            else:
                return "unavailable"
        except:
            return "unknown"
    
    def search_synsets(
        self, 
        query: str, 
        pos: Optional[str] = None,
        provider: Optional[NWOProvider] = None
    ) -> List[Dict[str, Any]]:
        """Search for synsets matching a query.
        
        Args:
            query: Search query
            pos: Part of speech filter (n, v, a, r)
            provider: NWO provider specification
            
        Returns:
            List of matching synsets
        """
        if not self.wn:
            return []
        
        try:
            synsets = self.wn.synsets(query, pos=pos)
            
            results = []
            for synset in synsets:
                result = {
                    'name': synset.name(),
                    'definition': synset.definition(),
                    'examples': synset.examples(),
                    'pos': synset.pos(),
                    'provider': provider.to_string() if provider else '@princeton/wordnet'
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching synsets for '{query}': {e}")
            return []