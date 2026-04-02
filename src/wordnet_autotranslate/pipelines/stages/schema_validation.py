"""Centralized request/response schema validation for translation stages."""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from pydantic import BaseModel, Field, ValidationError
from pydantic_core import PydanticUndefined


class SenseAnalysisSchema(BaseModel):
    sense_summary: str = Field(..., min_length=3)
    contrastive_note: Optional[str] = None
    key_features: List[str] = Field(default_factory=list)
    domain_tags: Optional[List[str]] = Field(default_factory=list)
    confidence: str


class DefinitionTranslationSchema(BaseModel):
    definition_translation: str
    notes: Optional[str] = None
    examples: Optional[List[str]] = Field(default_factory=list)


class LemmaTranslationSchema(BaseModel):
    initial_translations: List[Optional[str]]
    alignment: Dict[str, Optional[str]]


class ExpansionSchema(BaseModel):
    expanded_synonyms: List[str]
    rationale: Optional[Dict[str, str]] = Field(default_factory=dict)


class FilteringSchema(BaseModel):
    filtered_synonyms: List[str]
    removed: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    confidence: str


BASE_STAGE_SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "sense_analysis": SenseAnalysisSchema,
    "definition_translation": DefinitionTranslationSchema,
    "initial_translation": LemmaTranslationSchema,
    "synonym_expansion": ExpansionSchema,
    "synonym_filtering": FilteringSchema,
}


def validate_stage_payload(
    payload: dict, schema_cls: type[BaseModel], stage_name: str
) -> dict:
    """Validate LLM JSON payload against the expected schema."""
    try:
        model = schema_cls(**payload)
        return model.model_dump()
    except ValidationError:
        fallback = {}
        for field_name, field_info in schema_cls.model_fields.items():
            if field_info.is_required():
                fallback[field_name] = ""
            elif field_info.default is not PydanticUndefined:
                fallback[field_name] = field_info.default
            elif field_info.default_factory is not None:
                fallback[field_name] = field_info.default_factory()
            else:
                fallback[field_name] = None
        return {**fallback, **payload, "_validation_error_stage": stage_name}
