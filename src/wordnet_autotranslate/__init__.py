"""
WordNet Auto-Translation Package

A core tool for automatic expansion of WordNet in less-resourced languages.
Uses DSPy pipelines and prompt optimization for translation tasks.
"""

__version__ = "0.1.0"
__author__ = "WordNet Auto-Translation Contributors"

from .pipelines.translation_pipeline import TranslationPipeline
from .pipelines.langchain_base_pipeline import LangChainBasePipeline
from .pipelines.serbian_wordnet_pipeline import SerbianWordnetPipeline
from .models.synset_handler import SynsetHandler
from .models.xml_synset_parser import XmlSynsetParser, Synset
from .utils.language_utils import LanguageUtils

__all__ = [
    "TranslationPipeline",
    "LangChainBasePipeline",
    "SerbianWordnetPipeline",
    "SynsetHandler", 
    "XmlSynsetParser",
    "Synset",
    "LanguageUtils"
]

try:  # pragma: no cover - optional dependency path
    from .pipelines.langgraph_translation_pipeline import LangGraphTranslationPipeline

except ModuleNotFoundError:  # pragma: no cover - executed when optional deps missing
    LangGraphTranslationPipeline = None  # type: ignore[assignment]
else:
    __all__.append("LangGraphTranslationPipeline")