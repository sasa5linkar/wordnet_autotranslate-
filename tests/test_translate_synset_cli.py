import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "translate_synset_workflow.py"

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


def test_cli_pipeline_choices_include_baseline():
    parser = cli.build_parser()
    pipeline_action = next(action for action in parser._actions if action.dest == "pipeline")
    assert "baseline" in pipeline_action.choices


def test_cli_resolve_only_prints_resolved_payload_without_running_pipeline(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--english-id", "ENG30-00001740-n", "--resolve-only"],
    )

    expected_payload = {
        "id": "ENG30-00001740-n",
        "english_id": "ENG30-00001740-n",
        "name": "entity.n.01",
        "lemmas": ["entity"],
        "definition": "something that exists",
        "examples": [],
        "pos": "n",
    }

    monkeypatch.setattr(cli, "resolve_wordnet_synset", lambda **kwargs: expected_payload)

    def _unexpected_run(*args, **kwargs):
        raise AssertionError("run_translation_workflow should not be called in resolve-only mode")

    monkeypatch.setattr(cli, "run_translation_workflow", _unexpected_run)

    assert cli.main() == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["mode"] == "resolve-only"
    assert result["selector_id"] == "ENG30-00001740-n"
    assert result["source_synset"] == expected_payload
    assert result["pipelines"] == {}


def test_cli_parser_includes_resolve_only_flag():
    parser = cli.build_parser()
    resolve_action = next(action for action in parser._actions if action.dest == "resolve_only")
    assert resolve_action.option_strings == ["--resolve-only"]
