import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_repo_translation_batch.py"

_spec = importlib.util.spec_from_file_location("run_repo_translation_batch", SCRIPT_PATH)
cli = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cli)


def test_cli_conflicting_reasoning_flags_return_1(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "fake-run", "--disable-reasoning", "--reasoning", "low"],
    )

    assert cli.main() == 1
    assert "Use either --disable-reasoning or --reasoning, not both." in capsys.readouterr().err
