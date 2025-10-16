"""Tests for optional GUI dependencies (pandas/streamlit)."""

import sys
from pathlib import Path

import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wordnet_autotranslate.gui import synset_browser as sb


def test_export_pairs_requires_pandas(monkeypatch):
    """_export_pairs should raise ImportError when pandas is unavailable."""
    monkeypatch.setattr(sb, "pd", None)
    app = sb.SynsetBrowserApp()
    sb.st.session_state[sb.SESSION_SELECTED_PAIRS] = [{"dummy": 1}]
    with pytest.raises(ImportError):
        app._export_pairs()
