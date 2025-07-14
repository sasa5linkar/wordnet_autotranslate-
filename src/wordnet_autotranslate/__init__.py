"""
WordNet Auto-Translation Package

A core tool for automatic expansion of WordNet in less-resourced languages.
Uses DSPy pipelines and prompt optimization for translation tasks.
"""

__version__ = "0.1.0"
__author__ = "WordNet Auto-Translation Contributors"

from .pipelines.translation_pipeline import TranslationPipeline
from .models.synset_handler import SynsetHandler
from .utils.language_utils import LanguageUtils

__all__ = [
    "TranslationPipeline",
    "SynsetHandler", 
    "LanguageUtils"
]