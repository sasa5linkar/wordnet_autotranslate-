"""
Tests for import/export functionality in synset browser.
"""

import json
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wordnet_autotranslate.gui.synset_browser import SynsetBrowserApp


def test_validate_import_data_valid():
    """Test validation with valid import data."""
    app = SynsetBrowserApp()
    
    valid_data = {
        'pairs': [
            {
                'serbian_id': 'ENG30-03574555-n',
                'english_id': 'ENG30-03574555-n',
                'serbian_synonyms': ['ustanova'],
                'serbian_definition': 'test definition',
                'english_definition': 'test english definition',
                'english_lemmas': ['institution']
            }
        ],
        'metadata': {
            'total_pairs': 1,
            'format_version': '2.0',
            'created_by': 'Serbian WordNet Synset Browser'
        }
    }
    
    result = app._validate_import_data(valid_data)
    assert result['valid'] is True
    assert result['error'] is None


def test_validate_import_data_missing_pairs():
    """Test validation with missing pairs field."""
    app = SynsetBrowserApp()
    
    invalid_data = {
        'metadata': {
            'total_pairs': 0,
            'format_version': '2.0'
        }
    }
    
    result = app._validate_import_data(invalid_data)
    assert result['valid'] is False
    assert 'Missing required "pairs" field' in result['error']


def test_validate_import_data_invalid_pairs():
    """Test validation with invalid pairs structure."""
    app = SynsetBrowserApp()
    
    invalid_data = {
        'pairs': 'not a list'
    }
    
    result = app._validate_import_data(invalid_data)
    assert result['valid'] is False
    assert '"pairs" field must be a list' in result['error']


def test_validate_import_data_missing_required_fields():
    """Test validation with missing required fields in pairs."""
    app = SynsetBrowserApp()
    
    invalid_data = {
        'pairs': [
            {
                'serbian_id': 'ENG30-03574555-n'
                # missing english_id
            }
        ]
    }
    
    result = app._validate_import_data(invalid_data)
    assert result['valid'] is False
    assert 'missing required field: english_id' in result['error']


def test_validate_import_data_unsupported_version():
    """Test validation with unsupported format version."""
    app = SynsetBrowserApp()
    
    invalid_data = {
        'pairs': [
            {
                'serbian_id': 'ENG30-03574555-n',
                'english_id': 'ENG30-03574555-n'
            }
        ],
        'metadata': {
            'format_version': '3.0'  # unsupported version
        }
    }
    
    result = app._validate_import_data(invalid_data)
    assert result['valid'] is False
    assert 'Unsupported format version 3.0' in result['error']


def test_validate_import_data_old_version():
    """Test validation with supported old format version."""
    app = SynsetBrowserApp()
    
    valid_data = {
        'pairs': [
            {
                'serbian_id': 'ENG30-03574555-n',
                'english_id': 'ENG30-03574555-n'
            }
        ],
        'metadata': {
            'format_version': '1.0'  # supported old version
        }
    }
    
    result = app._validate_import_data(valid_data)
    assert result['valid'] is True
    assert result['error'] is None


def test_validate_import_data_not_dict():
    """Test validation with non-dictionary root element."""
    app = SynsetBrowserApp()
    
    invalid_data = []  # should be a dict
    
    result = app._validate_import_data(invalid_data)
    assert result['valid'] is False
    assert 'Root element must be a JSON object' in result['error']


def test_export_format_matches_import():
    """Test that exported data can be imported successfully."""
    app = SynsetBrowserApp()
    
    # Create sample pair data that matches export format
    sample_pair = {
        'serbian_id': 'ENG30-03574555-n',
        'serbian_synonyms': ['ustanova'],
        'serbian_definition': 'zgrada u kojoj se nalazi organizaciona jedinica',
        'serbian_usage': 'Nova ustanova će biti otvorena sledeće godine.',
        'serbian_pos': 'n',
        'serbian_domain': 'factotum',
        'serbian_relations': {
            'total_relations': 2,
            'relations_by_type': {},
            'available_relations': [],
            'external_relations': []
        },
        'english_id': 'ENG30-03574555-n',
        'english_definition': 'a building that houses an administrative unit',
        'english_lemmas': ['institution', 'establishment'],
        'english_examples': ['The new institution will open next year'],
        'english_pos': 'n',
        'english_name': 'institution.n.01',
        'english_relations': {},
        'pairing_metadata': {
            'pair_type': 'automatic',
            'quality_score': 2.0,
            'translator': 'Cvetana',
            'translation_date': '20.7.2006. 00.00.00'
        }
    }
    
    # Create export-style data
    export_data = {
        'pairs': [sample_pair],
        'metadata': {
            'total_pairs': 1,
            'created_by': 'Serbian WordNet Synset Browser',
            'format_version': '2.0',
            'export_timestamp': '2023-12-01T10:00:00',
            'includes_relations': True,
            'includes_metadata': True,
            'description': 'Enhanced export with Serbian and English relations for translation context'
        }
    }
    
    # Validate that this export format can be imported
    result = app._validate_import_data(export_data)
    assert result['valid'] is True
    assert result['error'] is None


if __name__ == "__main__":
    pytest.main([__file__])