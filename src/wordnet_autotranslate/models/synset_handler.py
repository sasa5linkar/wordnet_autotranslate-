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
    
    def get_synset_by_offset(self, offset: str, pos: str) -> Optional[Dict]:
        """
        Get synset by WordNet offset and part of speech.
        
        Args:
            offset: WordNet offset (e.g., '03574555')
            pos: Part of speech ('n', 'v', 'a', 'r')
            
        Returns:
            Synset dictionary or None if not found
        """
        if not NLTK_AVAILABLE:
            print("NLTK not available. Please install with: pip install nltk")
            return None
            
        try:
            # Convert offset to integer and find synset
            offset_int = int(offset)
            synset = wn.synset_from_pos_and_offset(pos, offset_int)
            
            if synset:
                return {
                    'name': synset.name(),
                    'definition': synset.definition(),
                    'examples': synset.examples(),
                    'lemmas': [lemma.name() for lemma in synset.lemmas()],
                    'pos': synset.pos(),
                    'offset': synset.offset(),
                    'relations': self._extract_all_relations(synset)
                }
        except Exception as e:
            print(f"Error looking up synset with offset {offset}, pos {pos}: {e}")
        
        return None

    def _extract_all_relations(self, synset) -> Dict:
        """
        Extract all available relations from Princeton WordNet synset.
        
        Args:
            synset: NLTK synset object
            
        Returns:
            Dictionary containing all relations
        """
        relations = {}
        
        # Hierarchical relations (is-a relationships)
        try:
            relations['hypernyms'] = [{'name': h.name(), 'definition': h.definition()} for h in synset.hypernyms()]
        except AttributeError:
            relations['hypernyms'] = []
        
        try:
            relations['hyponyms'] = [{'name': h.name(), 'definition': h.definition()} for h in synset.hyponyms()]
        except AttributeError:
            relations['hyponyms'] = []
        
        try:
            relations['instance_hypernyms'] = [{'name': h.name(), 'definition': h.definition()} for h in synset.instance_hypernyms()]
        except AttributeError:
            relations['instance_hypernyms'] = []
        
        try:
            relations['instance_hyponyms'] = [{'name': h.name(), 'definition': h.definition()} for h in synset.instance_hyponyms()]
        except AttributeError:
            relations['instance_hyponyms'] = []
        
        # Part-whole relations (meronymy/holonymy)
        try:
            relations['part_meronyms'] = [{'name': m.name(), 'definition': m.definition()} for m in synset.part_meronyms()]
        except AttributeError:
            relations['part_meronyms'] = []
        
        try:
            relations['part_holonyms'] = [{'name': h.name(), 'definition': h.definition()} for h in synset.part_holonyms()]
        except AttributeError:
            relations['part_holonyms'] = []
        
        try:
            relations['member_meronyms'] = [{'name': m.name(), 'definition': m.definition()} for m in synset.member_meronyms()]
        except AttributeError:
            relations['member_meronyms'] = []
        
        try:
            relations['member_holonyms'] = [{'name': h.name(), 'definition': h.definition()} for h in synset.member_holonyms()]
        except AttributeError:
            relations['member_holonyms'] = []
        
        try:
            relations['substance_meronyms'] = [{'name': m.name(), 'definition': m.definition()} for m in synset.substance_meronyms()]
        except AttributeError:
            relations['substance_meronyms'] = []
        
        try:
            relations['substance_holonyms'] = [{'name': h.name(), 'definition': h.definition()} for h in synset.substance_holonyms()]
        except AttributeError:
            relations['substance_holonyms'] = []
        
        # Similarity and other semantic relations
        try:
            relations['similar_tos'] = [{'name': s.name(), 'definition': s.definition()} for s in synset.similar_tos()]
        except AttributeError:
            relations['similar_tos'] = []
        
        try:
            relations['also'] = [{'name': a.name(), 'definition': a.definition()} for a in synset.also()]
        except AttributeError:
            relations['also'] = []
        
        # Verb-specific relations
        if synset.pos() == 'v':
            try:
                relations['entailments'] = [{'name': e.name(), 'definition': e.definition()} for e in synset.entailments()]
            except AttributeError:
                relations['entailments'] = []
            
            try:
                relations['causes'] = [{'name': c.name(), 'definition': c.definition()} for c in synset.causes()]
            except AttributeError:
                relations['causes'] = []
            
            try:
                relations['verb_groups'] = [{'name': v.name(), 'definition': v.definition()} for v in synset.verb_groups()]
            except AttributeError:
                relations['verb_groups'] = []
        
        # Adjective-specific relations
        if synset.pos() in ['a', 's']:
            try:
                relations['attributes'] = [{'name': a.name(), 'definition': a.definition()} for a in synset.attributes()]
            except AttributeError:
                relations['attributes'] = []
        
        # Lemma-level relations (antonyms, derivational forms, etc.)
        relations['lemma_relations'] = self._extract_lemma_relations(synset)
        
        return relations
    
    def _extract_lemma_relations(self, synset) -> Dict:
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
            
            # Antonym relations
            antonyms = [{'name': ant.synset().name(), 'definition': ant.synset().definition(), 'lemma': ant.name()} 
                       for ant in lemma.antonyms()]
            if antonyms:
                lemma_relations[lemma_name]['antonyms'] = antonyms
            
            # Pertainym relations (for adjectives - "of or pertaining to")
            try:
                pertainyms = [{'name': p.synset().name(), 'definition': p.synset().definition(), 'lemma': p.name()} 
                             for p in lemma.pertainyms()]
                if pertainyms:
                    lemma_relations[lemma_name]['pertainyms'] = pertainyms
            except AttributeError:
                pass
            
            # Derivationally related forms
            try:
                derivations = [{'name': d.synset().name(), 'definition': d.synset().definition(), 'lemma': d.name()} 
                              for d in lemma.derivationally_related_forms()]
                if derivations:
                    lemma_relations[lemma_name]['derivationally_related'] = derivations
            except AttributeError:
                pass
        
        return lemma_relations

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
                'offset': synset.offset(),
                'relations': self._extract_all_relations(synset)
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
        if not NLTK_AVAILABLE:
            print("NLTK not available. Please install with: pip install nltk")
            return []
        all_synsets = wn.all_synsets(pos=pos) if pos else wn.all_synsets()
        result = []
        
        for synset in all_synsets:
            synset_data = {
                'name': synset.name(),
                'definition': synset.definition(),
                'examples': synset.examples(),
                'lemmas': [lemma.name() for lemma in synset.lemmas()],
                'pos': synset.pos(),
                'offset': synset.offset(),
                'relations': self._extract_all_relations(synset)
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
                'pos': synset.pos(),
                'offset': synset.offset(),
                'relations': self._extract_all_relations(synset)
            }
            result.append(synset_data)
        
        return result

    def get_relation_comparison_data(self, synset_name: str) -> Dict:
        """
        Get structured relation data for comparison with Serbian WordNet.
        
        Args:
            synset_name: Name of synset (e.g., 'dog.n.01')
            
        Returns:
            Dictionary with organized relation data for comparison
        """
        if not NLTK_AVAILABLE:
            return {}
        
        try:
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
            
        except Exception as e:
            print(f"Error getting comparison data for {synset_name}: {e}")
            return {}

    def get_relation_summary(self, synset_name: str) -> Dict:
        """
        Get a summary of all relations for a specific synset.
        
        Args:
            synset_name: Name of synset (e.g., 'dog.n.01')
            
        Returns:
            Dictionary with relation counts and examples
        """
        if not NLTK_AVAILABLE:
            return {}
        
        try:
            synset = wn.synset(synset_name)
            relations = self._extract_all_relations(synset)
            
            summary = {
                'synset': synset_name,
                'definition': synset.definition(),
                'relation_counts': {},
                'sample_relations': {}
            }
            
            for rel_type, rel_list in relations.items():
                if rel_type != 'lemma_relations' and rel_list:
                    summary['relation_counts'][rel_type] = len(rel_list)
                    summary['sample_relations'][rel_type] = rel_list[:3]  # First 3 examples
            
            # Handle lemma relations separately
            if relations.get('lemma_relations'):
                lemma_counts = {}
                for lemma, lemma_rels in relations['lemma_relations'].items():
                    for rel_type, rel_list in lemma_rels.items():
                        lemma_counts[f'lemma_{rel_type}'] = lemma_counts.get(f'lemma_{rel_type}', 0) + len(rel_list)
                
                summary['relation_counts'].update(lemma_counts)
            
            return summary
            
        except Exception as e:
            print(f"Error getting relation summary for {synset_name}: {e}")
            return {}

    def get_relation_types(self) -> List[str]:
        """
        Get all available relation types in WordNet.
        
        Returns:
            List of relation type names
        """
        return [
            'hypernyms', 'hyponyms', 'instance_hypernyms', 'instance_hyponyms',
            'part_meronyms', 'part_holonyms', 'member_meronyms', 'member_holonyms',
            'substance_meronyms', 'substance_holonyms', 'similar_tos', 'also',
            'entailments', 'causes', 'verb_groups', 'attributes',
            'antonyms', 'pertainyms', 'derivationally_related'
        ]

    def get_synsets_by_relation(self, synset_name: str, relation_type: str) -> List[Dict]:
        """
        Get synsets related to a given synset by a specific relation type.
        
        Args:
            synset_name: Name of the source synset (e.g., 'dog.n.01')
            relation_type: Type of relation to follow
            
        Returns:
            List of related synsets
        """
        if not NLTK_AVAILABLE:
            return []
        
        try:
            synset = wn.synset(synset_name)
            related_synsets = []
            
            # Get related synsets based on relation type
            if hasattr(synset, relation_type):
                related = getattr(synset, relation_type)()
                for rel_synset in related:
                    synset_data = {
                        'name': rel_synset.name(),
                        'definition': rel_synset.definition(),
                        'pos': rel_synset.pos(),
                        'offset': rel_synset.offset()
                    }
                    related_synsets.append(synset_data)
            
            return related_synsets
            
        except Exception as e:
            print(f"Error getting {relation_type} for {synset_name}: {e}")
            return []