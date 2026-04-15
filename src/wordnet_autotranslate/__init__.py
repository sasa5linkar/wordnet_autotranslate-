"""
WordNet Auto-Translation Package

A core tool for automatic expansion of WordNet in less-resourced languages.
Provides baseline, multi-phase, and concept-oriented translation workflows.
"""

__version__ = "0.1.0"
__author__ = "WordNet Auto-Translation Contributors"

from .pipelines.translation_pipeline import BaselineTranslationPipeline, TranslationPipeline
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

__all__ = [
    "BaselineTranslationPipeline",
    "TranslationPipeline",
    "LangGraphTranslationPipeline",
    "ConceptualLangGraphTranslationPipeline",
    "SerbianWordnetPipeline",
    "SynsetHandler",
    "XmlSynsetParser",
    "Synset",
    "LanguageUtils",
    "WorkflowConfig",
    "resolve_wordnet_synset",
    "run_translation_workflow",
]
