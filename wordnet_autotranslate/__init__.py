"""WordNet AutoTranslate package with NWO format support.

This package provides automatic translation capabilities with integrated
WordNet support for both DSPy and Princeton WordNet, using the new
NWO (namespace-with-owner) format.
"""

__version__ = "0.1.0"
__author__ = "WordNet AutoTranslate Team"

from .core import WordNetAutoTranslator
from .config import Config, NWOProvider
from .integrations import DSPyIntegration, PrincetonWordNetIntegration

__all__ = [
    "WordNetAutoTranslator",
    "Config", 
    "NWOProvider",
    "DSPyIntegration",
    "PrincetonWordNetIntegration",
]