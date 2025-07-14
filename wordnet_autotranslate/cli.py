#!/usr/bin/env python3
"""Command-line interface for WordNet AutoTranslate."""

import argparse
import sys
import yaml
from pathlib import Path

from wordnet_autotranslate import WordNetAutoTranslator, Config


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="WordNet AutoTranslate CLI with NWO format support"
    )
    parser.add_argument(
        "text",
        nargs='?',  # Make text optional
        help="Text to translate"
    )
    parser.add_argument(
        "--source-lang", "-s",
        default="en",
        help="Source language code (default: en)"
    )
    parser.add_argument(
        "--target-lang", "-t", 
        default="es",
        help="Target language code (default: es)"
    )
    parser.add_argument(
        "--provider", "-p",
        help="Provider to use (supports NWO format, e.g., @dspy/wordnet)"
    )
    parser.add_argument(
        "--config", "-c",
        help="Configuration file path"
    )
    parser.add_argument(
        "--list-providers", 
        action="store_true",
        help="List available providers"
    )
    parser.add_argument(
        "--list-languages",
        action="store_true", 
        help="List supported languages"
    )
    parser.add_argument(
        "--synsets",
        action="store_true",
        help="Show WordNet synsets for the input text"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = None
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            config = Config.from_file(config_path)
        else:
            print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
            return 1
    
    # Initialize translator
    translator = WordNetAutoTranslator(config)
    
    # Handle list commands
    if args.list_providers:
        providers = translator.get_available_providers()
        print("Available providers:")
        for name, provider in providers.items():
            nwo_str = provider.to_string()
            legacy_str = " (legacy)" if provider.is_legacy_format() else " (NWO)"
            print(f"  {name}: {nwo_str}{legacy_str}")
        return 0
    
    if args.list_languages:
        languages = translator.get_supported_languages(args.provider)
        print(f"Supported languages{' for ' + args.provider if args.provider else ''}:")
        for lang in languages:
            print(f"  {lang}")
        return 0
    
    # Handle synsets command
    if args.synsets:
        if not args.text:
            print("Error: text is required for synsets command", file=sys.stderr)
            return 1
            
        words = args.text.split()
        synsets = translator.get_wordnet_synsets(args.text, args.source_lang, args.provider)
        
        print(f"WordNet synsets for '{args.text}':")
        if args.provider:
            print(f"Provider: {args.provider}")
        
        for synset_data in synsets:
            word = synset_data['word']
            provider = synset_data['provider']
            print(f"\nWord: {word} (via {provider})")
            
            for synset in synset_data['synsets']:
                print(f"  {synset['name']}: {synset['definition']}")
                if synset.get('examples'):
                    for example in synset['examples'][:2]:  # Show first 2 examples
                        print(f"    Example: {example}")
        
        return 0
    
    # Perform translation
    if not args.text:
        print("Error: text is required for translation", file=sys.stderr)
        return 1
        
    try:
        result = translator.translate(
            args.text,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            provider=args.provider
        )
        
        if args.verbose:
            print(f"Source ({args.source_lang}): {args.text}")
            if args.provider:
                print(f"Provider: {args.provider}")
            print(f"Target ({args.target_lang}): {result}")
        else:
            print(result)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())