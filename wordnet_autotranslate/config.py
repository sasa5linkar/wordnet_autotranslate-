"""Configuration system with NWO format support."""

import re
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class NWOProvider:
    """Represents a provider in NWO (namespace-with-owner) format.
    
    Supports formats like:
    - @dspy/wordnet
    - @princeton/wordnet
    - wordnet (legacy format)
    """
    namespace: Optional[str] = None
    name: str = ""
    version: Optional[str] = None
    
    @classmethod
    def parse(cls, nwo_string: str) -> "NWOProvider":
        """Parse NWO format string into components.
        
        Args:
            nwo_string: String in format [@namespace/]name[@version]
            
        Returns:
            NWOProvider instance
            
        Examples:
            >>> NWOProvider.parse("@dspy/wordnet")
            NWOProvider(namespace="dspy", name="wordnet", version=None)
            >>> NWOProvider.parse("@princeton/wordnet@1.2.0")
            NWOProvider(namespace="princeton", name="wordnet", version="1.2.0")
            >>> NWOProvider.parse("wordnet")
            NWOProvider(namespace=None, name="wordnet", version=None)
        """
        # Pattern for NWO format: [@namespace/]name[@version]
        pattern = r"^(?:@([^/]+)/)?([^@]+)(?:@(.+))?$"
        match = re.match(pattern, nwo_string.strip())
        
        if not match:
            raise ValueError(f"Invalid NWO format: {nwo_string}")
            
        namespace, name, version = match.groups()
        return cls(namespace=namespace, name=name, version=version)
    
    def to_string(self) -> str:
        """Convert back to NWO format string."""
        result = self.name
        if self.namespace:
            result = f"@{self.namespace}/{result}"
        if self.version:
            result = f"{result}@{self.version}"
        return result
    
    def is_legacy_format(self) -> bool:
        """Check if this is a legacy format (no namespace)."""
        return self.namespace is None


class Config:
    """Configuration manager supporting NWO format."""
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """Initialize configuration.
        
        Args:
            config_data: Dictionary with configuration data
        """
        self.data = config_data or {}
        self.providers: Dict[str, NWOProvider] = {}
        self._parse_providers()
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Config instance
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        return cls(data)
    
    def _parse_providers(self) -> None:
        """Parse providers from configuration data."""
        providers_config = self.data.get('providers', {})
        
        for key, provider_config in providers_config.items():
            if isinstance(provider_config, str):
                # Simple string format
                self.providers[key] = NWOProvider.parse(provider_config)
            elif isinstance(provider_config, dict):
                # Detailed configuration format
                nwo_string = provider_config.get('nwo', key)
                provider = NWOProvider.parse(nwo_string)
                # Store additional configuration
                provider.config = provider_config
                self.providers[key] = provider
    
    def get_provider(self, name: str) -> Optional[NWOProvider]:
        """Get provider by name or NWO string.
        
        Args:
            name: Provider name or NWO format string
            
        Returns:
            NWOProvider instance if found, None otherwise
        """
        # First check if it's a configured provider name
        if name in self.providers:
            return self.providers[name]
            
        # Try to parse as NWO format
        try:
            return NWOProvider.parse(name)
        except ValueError:
            return None
    
    def get_dspy_config(self) -> Dict[str, Any]:
        """Get DSPy-specific configuration."""
        return self.data.get('dspy', {})
    
    def get_princeton_config(self) -> Dict[str, Any]:
        """Get Princeton WordNet-specific configuration."""
        return self.data.get('princeton', {})
    
    def get_wordnet_config(self) -> Dict[str, Any]:
        """Get general WordNet configuration."""
        return self.data.get('wordnet', {})
    
    def supports_nwo_format(self) -> bool:
        """Check if configuration supports NWO format."""
        return any(
            not provider.is_legacy_format() 
            for provider in self.providers.values()
        )
    
    def get_legacy_providers(self) -> Dict[str, NWOProvider]:
        """Get providers using legacy format."""
        return {
            name: provider 
            for name, provider in self.providers.items()
            if provider.is_legacy_format()
        }
    
    def get_nwo_providers(self) -> Dict[str, NWOProvider]:
        """Get providers using NWO format."""
        return {
            name: provider 
            for name, provider in self.providers.items()
            if not provider.is_legacy_format()
        }