"""Integration modules for different WordNet providers."""

from .dspy_integration import DSPyIntegration
from .princeton_integration import PrincetonWordNetIntegration

__all__ = [
    "DSPyIntegration",
    "PrincetonWordNetIntegration",
]