from pathlib import Path


def test_adverb_pos_gloss_prompt_includes_serbian_examples():
    langgraph_source = Path(
        "src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py"
    ).read_text(encoding="utf-8")
    langchain_source = Path(
        "src/wordnet_autotranslate/pipelines/langchain_base_pipeline.py"
    ).read_text(encoding="utf-8")

    for source in (langgraph_source, langchain_source):
        assert "Do not force every adverb gloss into the pattern" in source
        assert "formalno" in source
        assert "na formalan način" in source
        assert "žalosno" in source
        assert "na žalostan način" in source
        assert "bestraga" in source
        assert "neznano kud" in source
        assert "veoma daleko" in source
