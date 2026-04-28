"""
WordNet Auto-Translation Package

A core tool for automatic expansion of WordNet in less-resourced languages.
Provides baseline, multi-phase, and concept-oriented translation workflows.
"""

__version__ = "0.1.0"
__author__ = "WordNet Auto-Translation Contributors"

from .pipelines.translation_pipeline import BaselineTranslationPipeline, TranslationPipeline
from .pipelines.langchain_base_pipeline import LangChainBasePipeline
from .pipelines.langgraph_translation_pipeline import LangGraphTranslationPipeline
from .pipelines.conceptual_langgraph_pipeline import (
    ConceptualLangGraphTranslationPipeline,
)
from .pipelines.serbian_wordnet_pipeline import SerbianWordnetPipeline
from .models.synset_handler import SynsetHandler
from .models.xml_synset_parser import XmlSynsetParser, Synset
from .utils.language_utils import LanguageUtils
from .workflows.synset_translation_workflow import (
    WorkflowConfig,
    resolve_wordnet_synset,
    run_translation_workflow,
)
from .workflows.sheet_translation_workflow import (
    SheetBatchConfig,
    SheetColumnMapping,
    SheetColumnOverrides,
    build_google_sheet_csv_export_url,
    detect_column_mapping,
    group_candidate_records_by_sheet_header,
    render_grouped_candidate_text,
    run_sheet_translation_batch,
    sort_candidate_records_by_sheet_column,
    validate_sheet_row,
)

__all__ = [
    "BaselineTranslationPipeline",
    "TranslationPipeline",
    "LangChainBasePipeline",
    "LangGraphTranslationPipeline",
    "ConceptualLangGraphTranslationPipeline",
    "SerbianWordnetPipeline",
    "SynsetHandler",
    "XmlSynsetParser",
    "Synset",
    "LanguageUtils",
    "SheetBatchConfig",
    "SheetColumnMapping",
    "SheetColumnOverrides",
    "WorkflowConfig",
    "build_google_sheet_csv_export_url",
    "detect_column_mapping",
    "group_candidate_records_by_sheet_header",
    "render_grouped_candidate_text",
    "resolve_wordnet_synset",
    "run_sheet_translation_batch",
    "run_translation_workflow",
    "sort_candidate_records_by_sheet_column",
    "validate_sheet_row",
]
