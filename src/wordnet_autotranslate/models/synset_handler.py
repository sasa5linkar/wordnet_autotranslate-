"""
Synset Handler for WordNet operations.
"""

import logging
from typing import List, Dict, Optional, Any, Union

try:
    import nltk
    from nltk.corpus import wordnet as wn
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

logger = logging.getLogger(__name__)


class WordNetNotAvailableError(Exception):
    """Raised when NLTK WordNet is not available."""
    pass


class SynsetHandler:
    """Handles WordNet synset operations."""
    
    # Relation type constants
    HIERARCHICAL_RELATIONS = [
        'hypernyms', 'hyponyms', 'instance_hypernyms', 'instance_hyponyms'
    ]
    
    MERONYMY_RELATIONS = [
        'part_meronyms', 'part_holonyms', 'member_meronyms', 'member_holonyms',
        'substance_meronyms', 'substance_holonyms'
    ]
    
    SEMANTIC_RELATIONS = [
        'similar_tos', 'also', 'entailments', 'causes', 'verb_groups', 'attributes'
    ]
    
    LEMMA_RELATIONS = [
        'antonyms', 'pertainyms', 'derivationally_related'
    ]
    
    ALL_RELATION_TYPES = (
        HIERARCHICAL_RELATIONS + MERONYMY_RELATIONS + 
        SEMANTIC_RELATIONS + LEMMA_RELATIONS
    )
    
    def __init__(self, language: str = 'en'):
        """
        Initialize synset handler.
        
        Args:
            language: Language code for WordNet operations
        """
        self.language = language
        self._ensure_wordnet_data()
        # Cache for relation extraction
        self._relation_cache: Dict[str, Dict[str, Any]] = {}
    
    def _check_nltk_availability(self) -> None:
        """Check if NLTK is available and raise exception if not."""
        if not NLTK_AVAILABLE:
            error_msg = "NLTK not available. Please install with: pip install nltk"
            logger.error(error_msg)
            raise WordNetNotAvailableError(error_msg)
    
    def _ensure_wordnet_data(self) -> None:
        """Ensure WordNet data is downloaded."""
        self._check_nltk_availability()
            
        try:
            wn.synsets('test')
        except LookupError:
            logger.info("Downloading WordNet data...")
            nltk.download('wordnet')
            nltk.download('omw-1.4')
    
    def _create_synset_data(self, synset: Any, include_relations: bool = True) -> Dict[str, Any]:
        """
        Create standardized synset data dictionary.
        
        Args:
            synset: NLTK synset object
            include_relations: Whether to include relation data
            
        Returns:
            Dictionary containing synset data
        """
        synset_data = {
            'name': synset.name(),
            'definition': synset.definition(),
            'examples': synset.examples(),
            'lemmas': [lemma.name() for lemma in synset.lemmas()],
            'pos': synset.pos(),
            'offset': synset.offset()
        }
        
        if include_relations:
            synset_data['relations'] = self._extract_all_relations(synset)
            
        return synset_data
    
    def _extract_relation_safely(self, synset: Any, relation_method: str) -> List[Dict[str, str]]:
        """
        Safely extract relations from a synset.
        
        Args:
            synset: NLTK synset object
            relation_method: Name of the relation method to call
            
        Returns:
            List of related synsets with name and definition
        """
        try:
            if hasattr(synset, relation_method):
                related_synsets = getattr(synset, relation_method)()
                return [
                    {'name': rel.name(), 'definition': rel.definition()} 
                    for rel in related_synsets
                ]
        except AttributeError:
            pass
        return []
    
    def get_synset_by_offset(self, offset: str, pos: str) -> Optional[Dict[str, Any]]:
        """
        Get synset by WordNet offset and part of speech.
        
        Args:
            offset: WordNet offset (e.g., '03574555')
            pos: Part of speech ('n', 'v', 'a', 'r')
            
        Returns:
            Synset dictionary or None if not found
        """
        try:
            self._check_nltk_availability()
            
            # Normalize POS: Serbian 'b' (adverb) -> English 'r'
            pos_norm = pos.lower()
            if pos_norm == 'b':
                pos_norm = 'r'

            # Convert offset to integer and find synset
            offset_int = int(offset)
            synset = wn.synset_from_pos_and_offset(pos_norm, offset_int)
            
            if synset:
                return self._create_synset_data(synset)
                
        except WordNetNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error looking up synset with offset {offset}, pos {pos}: {e}")
        
        return None

    def _extract_all_relations(self, synset: Any) -> Dict[str, Any]:
        """
        Extract all available relations from Princeton WordNet synset with caching.
        
        Args:
            synset: NLTK synset object
            
        Returns:
            Dictionary containing all relations
        """
        # Use synset name as cache key
        synset_name = synset.name()
        
        # Check cache first
        if synset_name in self._relation_cache:
            return self._relation_cache[synset_name]
        
        relations = {}
        
        # Extract different types of relations
        relations.update(self._extract_hierarchical_relations(synset))
        relations.update(self._extract_meronymy_relations(synset))
        relations.update(self._extract_semantic_relations(synset))
        relations.update(self._extract_pos_specific_relations(synset))
        
        # Lemma-level relations
        relations['lemma_relations'] = self._extract_lemma_relations(synset)
        
        # Cache the result
        self._relation_cache[synset_name] = relations
        
        return relations
    
    def _extract_hierarchical_relations(self, synset: Any) -> Dict[str, List[Dict[str, str]]]:
        """Extract hierarchical relations (is-a relationships)."""
        return {
            'hypernyms': self._extract_relation_safely(synset, 'hypernyms'),
            'hyponyms': self._extract_relation_safely(synset, 'hyponyms'),
            'instance_hypernyms': self._extract_relation_safely(synset, 'instance_hypernyms'),
            'instance_hyponyms': self._extract_relation_safely(synset, 'instance_hyponyms')
        }
    
    def _extract_meronymy_relations(self, synset: Any) -> Dict[str, List[Dict[str, str]]]:
        """Extract part-whole relations (meronymy/holonymy)."""
        return {
            'part_meronyms': self._extract_relation_safely(synset, 'part_meronyms'),
            'part_holonyms': self._extract_relation_safely(synset, 'part_holonyms'),
            'member_meronyms': self._extract_relation_safely(synset, 'member_meronyms'),
            'member_holonyms': self._extract_relation_safely(synset, 'member_holonyms'),
            'substance_meronyms': self._extract_relation_safely(synset, 'substance_meronyms'),
            'substance_holonyms': self._extract_relation_safely(synset, 'substance_holonyms')
        }
    
    def _extract_semantic_relations(self, synset: Any) -> Dict[str, List[Dict[str, str]]]:
        """Extract similarity and other semantic relations."""
        return {
            'similar_tos': self._extract_relation_safely(synset, 'similar_tos'),
            'also': self._extract_relation_safely(synset, 'also')
        }
    
    def _extract_pos_specific_relations(self, synset: Any) -> Dict[str, List[Dict[str, str]]]:
        """Extract part-of-speech specific relations."""
        relations = {}
        pos = synset.pos()
        
        # Verb-specific relations
        if pos == 'v':
            relations.update({
                'entailments': self._extract_relation_safely(synset, 'entailments'),
                'causes': self._extract_relation_safely(synset, 'causes'),
                'verb_groups': self._extract_relation_safely(synset, 'verb_groups')
            })
        
        # Adjective-specific relations
        if pos in ['a', 's']:
            relations['attributes'] = self._extract_relation_safely(synset, 'attributes')
        
        return relations
    
    def _extract_lemma_relations(self, synset: Any) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """
        Extract lemma-level relations from Princeton WordNet.
        
        Args:
            synset: NLTK synset object
            
        Returns:
            Dictionary containing lemma relations
        """
        lemma_relations = {}
        
        for lemma in synset.lemmas():
            lemma_name = lemma.name()
            lemma_relations[lemma_name] = {}
            
            # Extract different types of lemma relations
            self._extract_antonyms(lemma, lemma_relations[lemma_name])
            self._extract_pertainyms(lemma, lemma_relations[lemma_name])
            self._extract_derivational_forms(lemma, lemma_relations[lemma_name])
        
        return lemma_relations
    
    def _extract_antonyms(self, lemma: Any, lemma_data: Dict[str, List[Dict[str, str]]]) -> None:
        """Extract antonym relations for a lemma."""
        antonyms = [
            {
                'name': ant.synset().name(), 
                'definition': ant.synset().definition(), 
                'lemma': ant.name()
            } 
            for ant in lemma.antonyms()
        ]
        if antonyms:
            lemma_data['antonyms'] = antonyms
    
    def _extract_pertainyms(self, lemma: Any, lemma_data: Dict[str, List[Dict[str, str]]]) -> None:
        """Extract pertainym relations for a lemma (for adjectives - 'of or pertaining to')."""
        try:
            pertainyms = [
                {
                    'name': p.synset().name(), 
                    'definition': p.synset().definition(), 
                    'lemma': p.name()
                } 
                for p in lemma.pertainyms()
            ]
            if pertainyms:
                lemma_data['pertainyms'] = pertainyms
        except AttributeError:
            pass
    
    def _extract_derivational_forms(self, lemma: Any, lemma_data: Dict[str, List[Dict[str, str]]]) -> None:
        """Extract derivationally related forms for a lemma."""
        try:
            derivations = [
                {
                    'name': d.synset().name(), 
                    'definition': d.synset().definition(), 
                    'lemma': d.name()
                } 
                for d in lemma.derivationally_related_forms()
            ]
            if derivations:
                lemma_data['derivationally_related'] = derivations
        except AttributeError:
            pass

    def get_synsets(self, word: str) -> List[Dict[str, Any]]:
        """
        Get synsets for a word.
        
        Args:
            word: Word to get synsets for
            
        Returns:
            List of synset dictionaries
        """
        try:
            self._check_nltk_availability()
            
            synsets = wn.synsets(word)
            return [self._create_synset_data(synset) for synset in synsets]
            
        except WordNetNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error getting synsets for word '{word}': {e}")
            return []
    
    def get_all_synsets(self, pos: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all synsets, optionally filtered by part of speech.
        
        Args:
            pos: Part of speech filter ('n', 'v', 'a', 'r')
            
        Returns:
            List of all synsets
        """
        try:
            self._check_nltk_availability()
            
            all_synsets = wn.all_synsets(pos=pos) if pos else wn.all_synsets()
            return [self._create_synset_data(synset) for synset in all_synsets]
            
        except WordNetNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error getting all synsets (pos={pos}): {e}")
            return []
    
    def search_synsets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search synsets by query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching synsets
        """
        try:
            self._check_nltk_availability()
            
            synsets = wn.synsets(query)[:limit]
            return [self._create_synset_data(synset) for synset in synsets]
            
        except WordNetNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error searching synsets for query '{query}': {e}")
            return []

    def get_relation_comparison_data(self, synset_name: str) -> Dict[str, Any]:
        """
        Get structured relation data for comparison with Serbian WordNet.
        
        Args:
            synset_name: Name of synset (e.g., 'dog.n.01')
            
        Returns:
            Dictionary with organized relation data for comparison
        """
        try:
            self._check_nltk_availability()
            
            synset = wn.synset(synset_name)
            relations = self._extract_all_relations(synset)
            
            # Organize relations by type for easier comparison
            comparison_data = {
                'synset_info': {
                    'name': synset.name(),
                    'definition': synset.definition(),
                    'pos': synset.pos(),
                    'offset': synset.offset(),
                    'lemmas': [lemma.name() for lemma in synset.lemmas()]
                },
                'hierarchical_relations': {
                    'hypernyms': relations.get('hypernyms', []),
                    'hyponyms': relations.get('hyponyms', []),
                    'instance_hypernyms': relations.get('instance_hypernyms', []),
                    'instance_hyponyms': relations.get('instance_hyponyms', [])
                },
                'meronymy_relations': {
                    'part_meronyms': relations.get('part_meronyms', []),
                    'part_holonyms': relations.get('part_holonyms', []),
                    'member_meronyms': relations.get('member_meronyms', []),
                    'member_holonyms': relations.get('member_holonyms', []),
                    'substance_meronyms': relations.get('substance_meronyms', []),
                    'substance_holonyms': relations.get('substance_holonyms', [])
                },
                'semantic_relations': {
                    'similar_tos': relations.get('similar_tos', []),
                    'also': relations.get('also', []),
                    'entailments': relations.get('entailments', []),
                    'causes': relations.get('causes', []),
                    'verb_groups': relations.get('verb_groups', []),
                    'attributes': relations.get('attributes', [])
                },
                'lexical_relations': relations.get('lemma_relations', {})
            }
            
            return comparison_data
            
        except WordNetNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error getting comparison data for {synset_name}: {e}")
            return {}

    def get_relation_summary(self, synset_name: str) -> Dict[str, Any]:
        """
        Get a summary of all relations for a specific synset.
        
        Args:
            synset_name: Name of synset (e.g., 'dog.n.01')
            
        Returns:
            Dictionary with relation counts and examples
        """
        try:
            self._check_nltk_availability()
            
            synset = wn.synset(synset_name)
            relations = self._extract_all_relations(synset)
            
            summary = {
                'synset': synset_name,
                'definition': synset.definition(),
                'relation_counts': {},
                'sample_relations': {}
            }
            
            # Process non-lemma relations
            for rel_type, rel_list in relations.items():
                if rel_type != 'lemma_relations' and rel_list:
                    summary['relation_counts'][rel_type] = len(rel_list)
                    summary['sample_relations'][rel_type] = rel_list[:3]  # First 3 examples
            
            # Handle lemma relations separately
            self._process_lemma_relations_summary(relations.get('lemma_relations', {}), summary)
            
            return summary
            
        except WordNetNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error getting relation summary for {synset_name}: {e}")
            return {}
    
    def _process_lemma_relations_summary(self, lemma_relations: Dict[str, Any], summary: Dict[str, Any]) -> None:
        """Process lemma relations for summary."""
        if not lemma_relations:
            return
            
        lemma_counts = {}
        for lemma, lemma_rels in lemma_relations.items():
            for rel_type, rel_list in lemma_rels.items():
                key = f'lemma_{rel_type}'
                lemma_counts[key] = lemma_counts.get(key, 0) + len(rel_list)
        
        summary['relation_counts'].update(lemma_counts)

    def get_relation_types(self) -> List[str]:
        """
        Get all available relation types in WordNet.
        
        Returns:
            List of relation type names
        """
        return self.ALL_RELATION_TYPES.copy()

    def get_synsets_by_relation(self, synset_name: str, relation_type: str) -> List[Dict[str, Any]]:
        """
        Get synsets related to a given synset by a specific relation type.
        
        Args:
            synset_name: Name of the source synset (e.g., 'dog.n.01')
            relation_type: Type of relation to follow
            
        Returns:
            List of related synsets
        """
        try:
            self._check_nltk_availability()
            
            synset = wn.synset(synset_name)
            related_synsets = []
            
            # Get related synsets based on relation type
            if hasattr(synset, relation_type):
                related = getattr(synset, relation_type)()
                related_synsets = [
                    {
                        'name': rel_synset.name(),
                        'definition': rel_synset.definition(),
                        'pos': rel_synset.pos(),
                        'offset': rel_synset.offset()
                    }
                    for rel_synset in related
                ]
            
            return related_synsets
            
        except WordNetNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error getting {relation_type} for {synset_name}: {e}")
            return []