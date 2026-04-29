import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "translate_synset_sheet.py"

_spec = importlib.util.spec_from_file_location("translate_synset_sheet", SCRIPT_PATH)
cli = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cli)


def test_cli_pipeline_default_is_all():
    parser = cli.build_parser()
    pipeline_action = next(action for action in parser._actions if action.dest == "pipeline")

    assert pipeline_action.default == "all"


def test_cli_provider_choices_include_openai():
    parser = cli.build_parser()
    provider_action = next(action for action in parser._actions if action.dest == "provider")
    assert "openai" in provider_action.choices


def test_cli_keyboard_interrupt_returns_130(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prog", "input.csv"])

    def _raise_interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "run_sheet_translation_batch", _raise_interrupt)

    assert cli.main() == 130
