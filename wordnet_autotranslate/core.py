"""Core WordNet AutoTranslator implementation."""

import logging
from typing import Dict, List, Optional, Union, Any
from .config import Config, NWOProvider
from .integrations import DSPyIntegration, PrincetonWordNetIntegration

logger = logging.getLogger(__name__)


class WordNetAutoTranslator:
    """Main class for WordNet-based automatic translation with NWO format support."""
    
    def __init__(self, config: Optional[Union[Config, Dict[str, Any]]] = None):
        """Initialize the translator.
        
        Args:
            config: Configuration object or dictionary
        """
        if isinstance(config, dict):
            self.config = Config(config)
        elif isinstance(config, Config):
            self.config = config
        else:
            self.config = Config()
        
        self.integrations = {}
        self._setup_integrations()
    
    def _setup_integrations(self) -> None:
        """Set up integrations based on configuration."""
        # Initialize DSPy integration if configured
        dspy_config = self.config.get_dspy_config()
        if dspy_config or self._has_dspy_providers():
            self.integrations['dspy'] = DSPyIntegration(self.config)
        
        # Initialize Princeton WordNet integration if configured
        princeton_config = self.config.get_princeton_config()
        if princeton_config or self._has_princeton_providers():
            self.integrations['princeton'] = PrincetonWordNetIntegration(self.config)
    
    def _has_dspy_providers(self) -> bool:
        """Check if any DSPy providers are configured."""
        return any(
            provider.namespace == 'dspy'
            for provider in self.config.providers.values()
        )
    
    def _has_princeton_providers(self) -> bool:
        """Check if any Princeton providers are configured."""
        return any(
            provider.namespace == 'princeton'
            for provider in self.config.providers.values()
        )
    
    def translate(
        self, 
        text: str, 
        source_lang: str = 'en', 
        target_lang: str = 'es',
        provider: Optional[str] = None
    ) -> str:
        """Translate text using WordNet-enhanced translation.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code  
            provider: Specific provider to use (supports NWO format)
            
        Returns:
            Translated text
        """
        # Parse provider if specified
        if provider:
            nwo_provider = self.config.get_provider(provider)
            if not nwo_provider:
                # Try to parse as direct NWO string
                try:
                    nwo_provider = NWOProvider.parse(provider)
                except ValueError:
                    raise ValueError(f"Unknown provider: {provider}")
            
            # Route to specific integration based on namespace
            if nwo_provider.namespace == 'dspy':
                return self._translate_with_dspy(text, source_lang, target_lang, nwo_provider)
            elif nwo_provider.namespace == 'princeton':
                return self._translate_with_princeton(text, source_lang, target_lang, nwo_provider)
            elif nwo_provider.is_legacy_format():
                # Handle legacy format - try both integrations
                return self._translate_with_legacy(text, source_lang, target_lang, nwo_provider)
        
        # Default translation using available integrations
        return self._translate_default(text, source_lang, target_lang)
    
    def _translate_with_dspy(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        provider: NWOProvider
    ) -> str:
        """Translate using DSPy integration."""
        if 'dspy' not in self.integrations:
            raise RuntimeError("DSPy integration not available")
        
        return self.integrations['dspy'].translate(text, source_lang, target_lang, provider)
    
    def _translate_with_princeton(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        provider: NWOProvider
    ) -> str:
        """Translate using Princeton WordNet integration."""
        if 'princeton' not in self.integrations:
            raise RuntimeError("Princeton WordNet integration not available")
        
        return self.integrations['princeton'].translate(text, source_lang, target_lang, provider)
    
    def _translate_with_legacy(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        provider: NWOProvider
    ) -> str:
        """Translate using legacy provider format."""
        # Try DSPy first, then Princeton for backward compatibility
        for integration_name in ['dspy', 'princeton']:
            if integration_name in self.integrations:
                try:
                    return self.integrations[integration_name].translate(
                        text, source_lang, target_lang, provider
                    )
                except Exception as e:
                    logger.warning(f"Legacy translation failed with {integration_name}: {e}")
                    continue
        
        # If no integrations available, try default translation
        if self.integrations:
            integration = next(iter(self.integrations.values()))
            return integration.translate(text, source_lang, target_lang, provider)
        
        raise RuntimeError(f"No integration available for legacy provider: {provider.name}")
    
    def _translate_default(self, text: str, source_lang: str, target_lang: str) -> str:
        """Default translation using first available integration."""
        if not self.integrations:
            raise RuntimeError("No integrations configured")
        
        # Use first available integration
        integration = next(iter(self.integrations.values()))
        return integration.translate(text, source_lang, target_lang)
    
    def get_supported_languages(self, provider: Optional[str] = None) -> List[str]:
        """Get list of supported languages.
        
        Args:
            provider: Specific provider to query (supports NWO format)
            
        Returns:
            List of supported language codes
        """
        if provider:
            nwo_provider = self.config.get_provider(provider)
            if not nwo_provider:
                raise ValueError(f"Unknown provider: {provider}")
            
            if nwo_provider.namespace == 'dspy' and 'dspy' in self.integrations:
                return self.integrations['dspy'].get_supported_languages()
            elif nwo_provider.namespace == 'princeton' and 'princeton' in self.integrations:
                return self.integrations['princeton'].get_supported_languages()
        
        # Return union of all supported languages
        languages = set()
        for integration in self.integrations.values():
            languages.update(integration.get_supported_languages())
        
        return sorted(list(languages))
    
    def get_available_providers(self) -> Dict[str, NWOProvider]:
        """Get all available providers."""
        return self.config.providers.copy()
    
    def get_wordnet_synsets(
        self, 
        word: str, 
        lang: str = 'en',
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get WordNet synsets for a word.
        
        Args:
            word: Word to look up
            lang: Language code
            provider: Specific provider to use (supports NWO format)
            
        Returns:
            List of synset information
        """
        if provider:
            nwo_provider = self.config.get_provider(provider)
            if not nwo_provider:
                raise ValueError(f"Unknown provider: {provider}")
            
            if nwo_provider.namespace == 'dspy' and 'dspy' in self.integrations:
                return self.integrations['dspy'].get_synsets(word, lang)
            elif nwo_provider.namespace == 'princeton' and 'princeton' in self.integrations:
                return self.integrations['princeton'].get_synsets(word, lang)
        
        # Use first available integration
        if self.integrations:
            integration = next(iter(self.integrations.values()))
            return integration.get_synsets(word, lang)
        
        return []