"""Stage-focused building blocks for pipeline execution."""

from .schema_validation import BASE_STAGE_SCHEMA_MAP, validate_stage_payload

__all__ = ["BASE_STAGE_SCHEMA_MAP", "validate_stage_payload"]
