import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "translate_synset_workflow.py"
)

_spec = importlib.util.spec_from_file_location("translate_synset_workflow", SCRIPT_PATH)
cli = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cli)


def test_cli_requires_pos_with_lemma(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prog", "--lemma", "entity"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


def test_cli_keyboard_interrupt_returns_130(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prog", "--english-id", "ENG30-00001740-n"])

    def _raise_interrupt(**kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "resolve_wordnet_synset", _raise_interrupt)
    assert cli.main() == 130


def test_cli_rejects_multiple_selector_families(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--english-id", "ENG30-00001740-n", "--synset-name", "entity.n.01"],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
