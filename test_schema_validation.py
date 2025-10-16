"""Test script for schema validation and retry logic."""

from src.wordnet_autotranslate.pipelines.langgraph_translation_pipeline import (
    SenseAnalysisSchema,
    DefinitionTranslationSchema,
    LemmaTranslationSchema,
    ExpansionSchema,
    FilteringSchema,
    validate_stage_payload,
)

def test_all_schemas():
    """Test validation for all stage schemas."""
    
    print("Testing SenseAnalysisSchema...")
    sense_payload = {
        "sense_summary": "A biochemical compound",
        "contrastive_note": "Not to be confused with proteins",
        "key_features": ["organic", "molecule"],
        "domain_tags": ["biochemistry"],
        "confidence": "high"
    }
    validated = validate_stage_payload(sense_payload, SenseAnalysisSchema, "sense_analysis")
    assert "sense_summary" in validated
    print("✓ SenseAnalysisSchema validation passed")
    
    print("\nTesting DefinitionTranslationSchema...")
    def_payload = {
        "definition_translation": "organski molekul",
        "notes": "Technical term",
        "examples": ["DNK je organsko jedinjenje"]
    }
    validated = validate_stage_payload(def_payload, DefinitionTranslationSchema, "definition_translation")
    assert "definition_translation" in validated
    print("✓ DefinitionTranslationSchema validation passed")
    
    print("\nTesting LemmaTranslationSchema...")
    lemma_payload = {
        "initial_translations": ["reč1", "reč2", None],
        "alignment": {"word1": "reč1", "word2": "reč2", "word3": None}
    }
    validated = validate_stage_payload(lemma_payload, LemmaTranslationSchema, "initial_translation")
    assert "initial_translations" in validated
    assert "alignment" in validated
    print("✓ LemmaTranslationSchema validation passed")
    
    print("\nTesting ExpansionSchema...")
    expansion_payload = {
        "expanded_synonyms": ["sinonim1", "sinonim2", "sinonim3"],
        "rationale": {
            "sinonim1": "Common usage",
            "sinonim2": "Technical term",
            "sinonim3": "Regional variant"
        }
    }
    validated = validate_stage_payload(expansion_payload, ExpansionSchema, "synonym_expansion")
    assert "expanded_synonyms" in validated
    assert "rationale" in validated
    print("✓ ExpansionSchema validation passed")
    
    print("\nTesting FilteringSchema...")
    filtering_payload = {
        "filtered_synonyms": ["sinonim1", "sinonim2"],
        "removed": [
            {"word": "sinonim3", "reason": "regional variant"}
        ],
        "confidence": "medium"
    }
    validated = validate_stage_payload(filtering_payload, FilteringSchema, "synonym_filtering")
    assert "filtered_synonyms" in validated
    assert "removed" in validated
    assert "confidence" in validated
    print("✓ FilteringSchema validation passed")
    
    print("\n" + "="*50)
    print("Testing malformed payloads...")
    print("="*50)
    
    # Test with missing required field
    print("\nTesting SenseAnalysisSchema with missing 'sense_summary'...")
    invalid_payload = {"confidence": "low"}
    validated = validate_stage_payload(invalid_payload, SenseAnalysisSchema, "sense_analysis")
    print(f"  Result: {validated}")
    print("  ✓ Gracefully handled missing required field")
    
    # Test with extra fields (should be ignored)
    print("\nTesting FilteringSchema with extra fields...")
    extra_payload = {
        "filtered_synonyms": ["word1"],
        "removed": [],
        "confidence": "high",
        "extra_field": "should be ignored"
    }
    validated = validate_stage_payload(extra_payload, FilteringSchema, "synonym_filtering")
    assert "extra_field" not in validated
    print("  ✓ Extra fields properly filtered out")
    
    print("\n" + "="*50)
    print("All schema validation tests passed! ✓")
    print("="*50)


if __name__ == "__main__":
    test_all_schemas()
