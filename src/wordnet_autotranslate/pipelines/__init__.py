"""Translation pipelines for WordNet auto-translation."""

from .translation_pipeline import TranslationPipeline
from .langchain_base_pipeline import LangChainBasePipeline
from .serbian_wordnet_pipeline import SerbianWordnetPipeline

__all__ = ["TranslationPipeline", "LangChainBasePipeline", "SerbianWordnetPipeline"]

try:  # pragma: no cover - optional dependency path
    from .langgraph_translation_pipeline import LangGraphTranslationPipeline

except ModuleNotFoundError:  # pragma: no cover - missing optional deps
    LangGraphTranslationPipeline = None  # type: ignore[assignment]
else:  # pragma: no cover - executed when deps available
    __all__.append("LangGraphTranslationPipeline")