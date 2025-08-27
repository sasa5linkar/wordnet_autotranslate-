import sys
from pathlib import Path

import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wordnet_autotranslate.models.synset_handler import (
    SynsetHandler,
    WordNetNotAvailableError,
)
import wordnet_autotranslate.models.synset_handler as synset_module


def test_get_synset_by_offset_returns_expected():
    """SynsetHandler retrieves known synset by offset and POS."""
    handler = SynsetHandler()
    synset = handler.get_synset_by_offset("03574555", "n")
    assert synset is not None
    assert synset["name"] == "institution.n.02"
    assert isinstance(synset["definition"], str) and synset["definition"]


def test_get_synsets_by_relation_hypernyms():
    """SynsetHandler returns hypernyms for a known synset."""
    handler = SynsetHandler()
    related = handler.get_synsets_by_relation("dog.n.01", "hypernyms")
    names = {r["name"] for r in related}
    assert "canine.n.02" in names or "domestic_animal.n.01" in names


def test_get_relation_summary_counts():
    """Summary includes counts for relations like hypernyms."""
    handler = SynsetHandler()
    summary = handler.get_relation_summary("dog.n.01")
    assert summary["synset"] == "dog.n.01"
    assert summary["relation_counts"]["hypernyms"] > 0


def test_wordnet_not_available(monkeypatch):
    """Raises WordNetNotAvailableError when NLTK is missing."""
    monkeypatch.setattr(synset_module, "NLTK_AVAILABLE", False)
    with pytest.raises(WordNetNotAvailableError):
        SynsetHandler()
