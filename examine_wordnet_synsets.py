"""
Script to examine NLTK WordNet synsets in detail.

This script analyzes several sample synsets from different parts of speech,
extracts all features including relations, and generates data for a comprehensive
report on how to use synset information in prompts.

Usage:
    python examine_wordnet_synsets.py

Output:
    - Prints summary statistics to console
    - Saves detailed analysis data to output/synset_analysis_data.json
    
The analysis includes:
    - Basic synset features (lemmas, definition, examples, POS)
    - All relation types (hierarchical, meronymy, semantic, lexical)
    - Relation statistics and richness scores
    - Prompt engineering suggestions for each synset
"""

import json
import logging
from typing import Dict, List, Any
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    from src.wordnet_autotranslate.models.synset_handler import SynsetHandler
except ImportError:
    logger.error("Could not import SynsetHandler. Make sure the package is installed.")
    raise


def select_sample_synsets() -> List[str]:
    """
    Select diverse sample synsets for analysis.
    
    Returns:
        List of synset names representing different POS and relation types
    """
    return [
        # Nouns with rich hierarchical relations
        'dog.n.01',           # domestic animal
        'car.n.01',           # vehicle with parts
        'tree.n.01',          # plant with parts and substance
        'university.n.01',    # institution with members
        'water.n.01',         # substance
        
        # Verbs with various relations
        'run.v.01',           # motion verb with entailments
        'eat.v.01',           # consumption verb
        'think.v.01',         # cognitive verb
        'break.v.01',         # verb with causative relation
        
        # Adjectives with similarity and attributes
        'good.a.01',          # quality adjective
        'large.a.01',         # size adjective with antonyms
        'happy.a.01',         # emotion adjective
        
        # Adverbs
        'quickly.r.01',       # manner adverb
        'very.r.01',          # degree adverb
    ]


def analyze_synset(handler: SynsetHandler, synset_name: str) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of a single synset.
    
    Args:
        handler: SynsetHandler instance
        synset_name: Name of synset to analyze
        
    Returns:
        Dictionary containing all synset features and analysis
    """
    logger.info(f"Analyzing synset: {synset_name}")
    
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        
        synset = wn.synset(synset_name)
        
        # Use the handler's public interface to get synset data with relations
        # Note: We access the private method here as this script is tightly coupled
        # with the SynsetHandler implementation for detailed analysis purposes
        synset_data = handler._create_synset_data(synset, include_relations=True)
        
        analysis = {
            'synset_name': synset_name,
            'basic_info': {
                'lemmas': synset_data['lemmas'],
                'definition': synset_data['definition'],
                'examples': synset_data['examples'],
                'pos': synset_data['pos'],
                'pos_full_name': _get_pos_full_name(synset_data['pos']),
                'offset': synset_data['offset'],
                'lexname': synset.lexname(),  # Lexicographer file name
            },
            'relations': synset_data.get('relations', {}),
            'statistics': {},
            'analysis': {}
        }
        
        # Calculate relation statistics
        analysis['statistics'] = _calculate_relation_statistics(analysis['relations'])
        
        # Add textual analysis
        analysis['analysis'] = _generate_synset_analysis(analysis)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing synset {synset_name}: {e}")
        return {'synset_name': synset_name, 'error': str(e)}


def _get_pos_full_name(pos: str) -> str:
    """Get full name for part of speech."""
    pos_names = {
        'n': 'noun',
        'v': 'verb',
        'a': 'adjective',
        's': 'adjective satellite',
        'r': 'adverb'
    }
    return pos_names.get(pos, pos)


def _calculate_relation_statistics(relations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate statistics about relations.
    
    Args:
        relations: Relations dictionary from synset
        
    Returns:
        Statistics about relation counts and types
    """
    stats = {
        'total_synset_relations': 0,
        'relation_counts': {},
        'has_hierarchical': False,
        'has_meronymy': False,
        'has_semantic': False,
        'has_lexical': False,
        'total_lemma_relations': 0
    }
    
    # Count synset-level relations
    for rel_type, rel_list in relations.items():
        if rel_type == 'lemma_relations':
            # Handle lemma relations separately
            lemma_count = 0
            for lemma_name, lemma_rels in rel_list.items():
                for sub_rel_type, sub_rel_list in lemma_rels.items():
                    count = len(sub_rel_list)
                    lemma_count += count
                    # Accumulate counts instead of overwriting
                    key = f'lemma_{sub_rel_type}'
                    stats['relation_counts'][key] = stats['relation_counts'].get(key, 0) + count
            stats['total_lemma_relations'] = lemma_count
            if lemma_count > 0:
                stats['has_lexical'] = True
        elif isinstance(rel_list, list):
            count = len(rel_list)
            if count > 0:
                stats['relation_counts'][rel_type] = count
                stats['total_synset_relations'] += count
                
                # Categorize relation types
                if rel_type in ['hypernyms', 'hyponyms', 'instance_hypernyms', 'instance_hyponyms']:
                    stats['has_hierarchical'] = True
                elif 'meronym' in rel_type or 'holonym' in rel_type:
                    stats['has_meronymy'] = True
                elif rel_type in ['similar_tos', 'also', 'entailments', 'causes', 'verb_groups', 'attributes']:
                    stats['has_semantic'] = True
    
    return stats


def _generate_synset_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate textual analysis of the synset.
    
    Args:
        analysis: Synset analysis dictionary
        
    Returns:
        Dictionary with analysis insights
    """
    info = analysis['basic_info']
    relations = analysis['relations']
    stats = analysis['statistics']
    
    insights = {
        'description': f"The synset '{analysis['synset_name']}' represents {info['pos_full_name']} concept.",
        'richness_score': 0,
        'relation_diversity': [],
        'key_relations': [],
        'prompt_suggestions': []
    }
    
    # Calculate richness score (0-10)
    richness = 0
    richness += min(len(info['lemmas']), 3)  # Up to 3 points for lemmas
    richness += min(len(info['examples']), 2)  # Up to 2 points for examples
    richness += min(stats['total_synset_relations'], 3)  # Up to 3 points for relations
    richness += min(stats['total_lemma_relations'], 2)  # Up to 2 points for lemma relations
    insights['richness_score'] = richness
    
    # Identify relation diversity
    if stats['has_hierarchical']:
        insights['relation_diversity'].append('hierarchical')
    if stats['has_meronymy']:
        insights['relation_diversity'].append('meronymy')
    if stats['has_semantic']:
        insights['relation_diversity'].append('semantic')
    if stats['has_lexical']:
        insights['relation_diversity'].append('lexical')
    
    # Identify key relations (those with most connections)
    for rel_type, count in sorted(stats['relation_counts'].items(), 
                                   key=lambda x: x[1], reverse=True)[:3]:
        insights['key_relations'].append({
            'type': rel_type,
            'count': count
        })
    
    # Generate prompt suggestions based on available data
    _generate_prompt_suggestions(insights, info, relations, stats)
    
    return insights


def _generate_prompt_suggestions(insights: Dict[str, Any], info: Dict[str, Any], 
                                 relations: Dict[str, Any], stats: Dict[str, Any]) -> None:
    """Generate suggestions for using synset data in prompts."""
    
    suggestions = []
    
    # Determine a safe primary lemma (if available)
    lemmas = info.get('lemmas') or []
    primary_lemma = lemmas[0] if lemmas else "this concept"
    
    # Basic definition usage
    suggestions.append({
        'category': 'definition',
        'suggestion': 'Use the synset definition as the core meaning',
        'example': f"Define '{primary_lemma}' as: {info['definition']}"
    })
    
    # Examples usage
    if info['examples']:
        suggestions.append({
            'category': 'examples',
            'suggestion': 'Include usage examples to provide context',
            'example': f"Used in context: {info['examples'][0]}"
        })
    
    # Synonym usage
    if len(info['lemmas']) > 1:
        suggestions.append({
            'category': 'synonyms',
            'suggestion': 'Present alternative words (lemmas) that share the same meaning',
            'example': f"Synonyms: {', '.join(info['lemmas'][1:])}"
        })
    
    # Hierarchical relations
    if relations.get('hypernyms') and len(relations['hypernyms']) > 0:
        suggestions.append({
            'category': 'hypernyms',
            'suggestion': 'Use hypernyms to show broader categories (is-a relation)',
            'example': f"A type of: {relations['hypernyms'][0]['name'].split('.')[0]}"
        })
    
    if relations.get('hyponyms') and len(relations['hyponyms']) > 0:
        suggestions.append({
            'category': 'hyponyms',
            'suggestion': 'Use hyponyms to show specific types',
            'example': f"Specific types include: {[h['name'].split('.')[0] for h in relations['hyponyms'][:3]]}"
        })
    
    # Meronymy relations
    if relations.get('part_meronyms') and len(relations['part_meronyms']) > 0:
        suggestions.append({
            'category': 'parts',
            'suggestion': 'Use part meronyms to describe component parts',
            'example': f"Has parts: {[p['name'].split('.')[0] for p in relations['part_meronyms'][:3]]}"
        })
    
    # Antonyms
    lemma_rels = relations.get('lemma_relations', {})
    for lemma_name, lemma_data in lemma_rels.items():
        if lemma_data.get('antonyms') and len(lemma_data['antonyms']) > 0:
            suggestions.append({
                'category': 'antonyms',
                'suggestion': 'Use antonyms to contrast meaning',
                'example': f"Opposite of: {lemma_data['antonyms'][0]['lemma']}"
            })
            break
    
    # Similar concepts
    if relations.get('similar_tos') and len(relations['similar_tos']) > 0:
        suggestions.append({
            'category': 'similarity',
            'suggestion': 'Use similar synsets to clarify meaning',
            'example': f"Similar to: {relations['similar_tos'][0]['name'].split('.')[0]}"
        })
    
    insights['prompt_suggestions'] = suggestions


def generate_summary_statistics(all_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics across all analyzed synsets.
    
    Args:
        all_analyses: List of synset analyses
        
    Returns:
        Summary statistics
    """
    summary = {
        'total_synsets_analyzed': len(all_analyses),
        'by_pos': {},
        'relation_type_usage': {},
        'average_richness_score': 0,
        'most_connected': [],
        'relation_coverage': {}
    }
    
    # Count by POS
    pos_counts = {}
    richness_scores = []
    relation_type_counts = {}
    
    for analysis in all_analyses:
        if 'error' in analysis:
            continue
            
        pos = analysis['basic_info']['pos_full_name']
        pos_counts[pos] = pos_counts.get(pos, 0) + 1
        
        richness = analysis['analysis']['richness_score']
        richness_scores.append(richness)
        
        # Track which relation types are used
        for rel_type in analysis['statistics']['relation_counts'].keys():
            relation_type_counts[rel_type] = relation_type_counts.get(rel_type, 0) + 1
    
    summary['by_pos'] = pos_counts
    summary['average_richness_score'] = sum(richness_scores) / len(richness_scores) if richness_scores else 0
    summary['relation_type_usage'] = relation_type_counts
    
    # Find most connected synsets
    sorted_by_relations = sorted(
        [a for a in all_analyses if 'error' not in a],
        key=lambda x: x['statistics']['total_synset_relations'] + x['statistics']['total_lemma_relations'],
        reverse=True
    )
    summary['most_connected'] = [
        {
            'synset': s['synset_name'],
            'total_relations': s['statistics']['total_synset_relations'] + s['statistics']['total_lemma_relations']
        }
        for s in sorted_by_relations[:5]
    ]
    
    # Calculate relation coverage (what % of synsets have each relation type)
    total = len([a for a in all_analyses if 'error' not in a])
    if total > 0:
        summary['relation_coverage'] = {
            rel_type: f"{(count/total)*100:.1f}%"
            for rel_type, count in relation_type_counts.items()
        }
    else:
        summary['relation_coverage'] = {}
    
    return summary


def main():
    """Main execution function."""
    logger.info("Starting WordNet synset examination...")
    
    # Initialize handler
    handler = SynsetHandler()
    
    # Select sample synsets
    sample_synsets = select_sample_synsets()
    logger.info(f"Selected {len(sample_synsets)} synsets for analysis")
    
    # Analyze each synset
    all_analyses = []
    for synset_name in sample_synsets:
        analysis = analyze_synset(handler, synset_name)
        all_analyses.append(analysis)
    
    # Generate summary statistics
    summary = generate_summary_statistics(all_analyses)
    
    # Save results
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / 'synset_analysis_data.json'
    output_data = {
        'analyses': all_analyses,
        'summary': summary
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Analysis complete! Data saved to {output_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("SYNSET ANALYSIS SUMMARY")
    print("="*70)
    print(f"\nTotal synsets analyzed: {summary['total_synsets_analyzed']}")
    print(f"Average richness score: {summary['average_richness_score']:.2f}/10")
    print(f"\nBy Part of Speech:")
    for pos, count in summary['by_pos'].items():
        print(f"  - {pos}: {count}")
    print(f"\nMost connected synsets:")
    for item in summary['most_connected']:
        print(f"  - {item['synset']}: {item['total_relations']} relations")
    print("\n" + "="*70)
    
    return output_data


if __name__ == '__main__':
    main()
