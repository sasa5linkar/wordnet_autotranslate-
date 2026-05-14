import importlib.util
import sys
import types
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_repo_translation_batch.py"


def _load_cli():
    package = types.ModuleType("wordnet_autotranslate")
    package.__path__ = []
    utils_package = types.ModuleType("wordnet_autotranslate.utils")
    utils_package.__path__ = []
    workflows_package = types.ModuleType("wordnet_autotranslate.workflows")
    workflows_package.__path__ = []

    llm_factory = types.ModuleType("wordnet_autotranslate.utils.llm_factory")
    llm_factory.load_project_env = lambda: None
    llm_factory.normalize_provider = lambda provider: provider or "ollama"
    llm_factory.resolve_base_url_for_provider = lambda provider, base_url: base_url
    llm_factory.resolve_model_for_provider = (
        lambda provider, model: model or f"{provider}-model"
    )

    native_queue = types.ModuleType("wordnet_autotranslate.workflows.native_translation_queue")
    native_queue.claim_next_native_work_item = lambda run_dir: None
    native_queue.complete_native_work_item = lambda *args, **kwargs: {}
    native_queue.fail_native_work_item = lambda *args, **kwargs: {}
    native_queue.requeue_in_progress_native_work_items = lambda run_dir: {"count": 0}
    native_queue.summarize_native_batch_run = (
        lambda run_dir: {
            "work_item_counts": {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
            },
            "all_finished": True,
        }
    )

    workflow = types.ModuleType("wordnet_autotranslate.workflows.synset_translation_workflow")

    class WorkflowConfig:
        def __init__(self, **kwargs):
            self.reasoning = kwargs.get("reasoning")
            self.temperature = kwargs.get("temperature")
            self.timeout = kwargs.get("timeout")

    workflow.WorkflowConfig = WorkflowConfig
    workflow.run_translation_workflow = lambda *args, **kwargs: {}

    injected_modules = {
        "wordnet_autotranslate": package,
        "wordnet_autotranslate.utils": utils_package,
        "wordnet_autotranslate.utils.llm_factory": llm_factory,
        "wordnet_autotranslate.workflows": workflows_package,
        "wordnet_autotranslate.workflows.native_translation_queue": native_queue,
        "wordnet_autotranslate.workflows.synset_translation_workflow": workflow,
    }
    original_modules = {name: sys.modules.get(name) for name in injected_modules}
    sys.modules.update(injected_modules)

    try:
        spec = importlib.util.spec_from_file_location("run_repo_translation_batch", SCRIPT_PATH)
        cli = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cli)
        return cli
    finally:
        for name, original in original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_cli_conflicting_reasoning_flags_return_1(monkeypatch, capsys):
    cli = _load_cli()
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "fake-run", "--disable-reasoning", "--reasoning", "low"],
    )

    assert cli.main() == 1
    assert "Use either --disable-reasoning or --reasoning, not both." in capsys.readouterr().err


def test_cli_keyboard_interrupt_during_setup_returns_130(monkeypatch):
    cli = _load_cli()
    monkeypatch.setattr("sys.argv", ["prog", "fake-run"])

    def _raise_interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "load_project_env", _raise_interrupt)

    assert cli.main() == 130
