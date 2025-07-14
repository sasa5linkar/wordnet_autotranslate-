# Integration Guide

This guide explains how to integrate WordNet AutoTranslate with NWO format support into your projects.

## Installation

### Basic Installation

```bash
pip install wordnet_autotranslate
```

### Development Installation

```bash
git clone https://github.com/sasa5linkar/wordnet_autotranslate-.git
cd wordnet_autotranslate-
pip install -e .
```

### With Optional Dependencies

```bash
# For testing
pip install wordnet_autotranslate[test]

# For development
pip install wordnet_autotranslate[dev]

# All dependencies
pip install wordnet_autotranslate[test,dev]
```

## Quick Start

### Basic Usage

```python
from wordnet_autotranslate import WordNetAutoTranslator

# Initialize with default configuration
translator = WordNetAutoTranslator()

# Simple translation
result = translator.translate("Hello world", target_lang="es")
print(result)  # "hola mundo"
```

### NWO Format Usage

```python
from wordnet_autotranslate import WordNetAutoTranslator

# Configure with NWO providers
config = {
    'providers': {
        'dspy_wordnet': '@dspy/wordnet@2.0.0',
        'princeton_wordnet': '@princeton/wordnet@3.0'
    }
}

translator = WordNetAutoTranslator(config)

# Use specific provider
result = translator.translate(
    "The cat is sleeping",
    provider="@dspy/wordnet"
)
```

## Configuration

### Configuration File

Create `config.yaml`:

```yaml
providers:
  # NWO format providers
  dspy_main:
    nwo: "@dspy/wordnet@2.0.0"
    model: "gpt-3.5-turbo"
    temperature: 0.3
    
  princeton_backup:
    nwo: "@princeton/wordnet@3.0"
    data_path: "~/nltk_data"
    
  # Legacy format
  legacy_wordnet: "wordnet"

# Provider-specific settings
dspy:
  default_model: "gpt-3.5-turbo"
  temperature: 0.3
  wordnet_enhancement: true
  
princeton:
  enable_multilingual: true
  download_missing: true

# General settings
wordnet:
  default_language: "en"
  cache_synsets: true
```

Load configuration:

```python
from wordnet_autotranslate import Config, WordNetAutoTranslator

config = Config.from_file("config.yaml")
translator = WordNetAutoTranslator(config)
```

### Environment Variables

```bash
export WORDNET_CONFIG_PATH="./config.yaml"
export DSPY_MODEL="gpt-4"
export PRINCETON_DATA_PATH="~/custom_nltk_data"
```

```python
import os
from wordnet_autotranslate import Config, WordNetAutoTranslator

# Load from environment
config_path = os.getenv('WORDNET_CONFIG_PATH', 'config.yaml')
config = Config.from_file(config_path)

# Override with environment variables
dspy_config = config.get_dspy_config()
dspy_config['model'] = os.getenv('DSPY_MODEL', dspy_config.get('model'))

translator = WordNetAutoTranslator(config)
```

## Integration Examples

### Web Application (Flask)

```python
from flask import Flask, request, jsonify
from wordnet_autotranslate import WordNetAutoTranslator, Config

app = Flask(__name__)

# Initialize translator
config = Config.from_file("config.yaml")
translator = WordNetAutoTranslator(config)

@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    
    result = translator.translate(
        text=data['text'],
        source_lang=data.get('source_lang', 'en'),
        target_lang=data.get('target_lang', 'es'),
        provider=data.get('provider')  # Supports NWO format
    )
    
    return jsonify({
        'translation': result,
        'provider': data.get('provider', 'default')
    })

@app.route('/providers', methods=['GET'])
def list_providers():
    providers = translator.get_available_providers()
    
    return jsonify({
        'providers': {
            name: {
                'nwo': provider.to_string(),
                'legacy': provider.is_legacy_format()
            }
            for name, provider in providers.items()
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
```

### Async Application (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from wordnet_autotranslate import WordNetAutoTranslator, Config
from typing import Optional, Dict, Any

app = FastAPI(title="WordNet AutoTranslate API")

# Initialize translator
config = Config.from_file("config.yaml")
translator = WordNetAutoTranslator(config)

class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "es"
    provider: Optional[str] = None  # Supports NWO format

class TranslationResponse(BaseModel):
    translation: str
    provider: Optional[str]
    synsets: Optional[list] = None

@app.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    try:
        result = translator.translate(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            provider=request.provider
        )
        
        # Optionally get synsets for enhanced translation
        synsets = None
        if request.provider:
            synsets = translator.get_wordnet_synsets(
                request.text, 
                lang=request.source_lang,
                provider=request.provider
            )
        
        return TranslationResponse(
            translation=result,
            provider=request.provider,
            synsets=synsets
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/providers")
async def list_providers():
    providers = translator.get_available_providers()
    
    return {
        "providers": {
            name: {
                "nwo": provider.to_string(),
                "namespace": provider.namespace,
                "name": provider.name,
                "version": provider.version,
                "legacy": provider.is_legacy_format()
            }
            for name, provider in providers.items()
        }
    }
```

### Command Line Tool

```python
#!/usr/bin/env python3
"""Custom CLI tool using WordNet AutoTranslate."""

import argparse
import sys
from pathlib import Path
from wordnet_autotranslate import WordNetAutoTranslator, Config

def main():
    parser = argparse.ArgumentParser(description="Custom WordNet Translation Tool")
    parser.add_argument("input_file", help="Input text file")
    parser.add_argument("output_file", help="Output translation file")
    parser.add_argument("--provider", help="Provider (supports NWO format)")
    parser.add_argument("--config", help="Configuration file")
    parser.add_argument("--source-lang", default="en", help="Source language")
    parser.add_argument("--target-lang", default="es", help="Target language")
    
    args = parser.parse_args()
    
    # Load configuration
    config = None
    if args.config:
        config = Config.from_file(args.config)
    
    translator = WordNetAutoTranslator(config)
    
    # Read input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1
    
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Translate
    try:
        result = translator.translate(
            text=text,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            provider=args.provider
        )
        
        # Write output
        output_path = Path(args.output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print(f"Translation completed: {input_path} -> {output_path}")
        if args.provider:
            print(f"Provider used: {args.provider}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Batch Processing

```python
"""Batch translation with multiple providers."""

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from wordnet_autotranslate import WordNetAutoTranslator, Config

class BatchTranslator:
    def __init__(self, config_path: str = None):
        config = Config.from_file(config_path) if config_path else None
        self.translator = WordNetAutoTranslator(config)
    
    def translate_batch(self, texts: list, provider: str = None, 
                       source_lang: str = "en", target_lang: str = "es",
                       max_workers: int = 4):
        """Translate multiple texts using threading."""
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all translation tasks
            future_to_text = {
                executor.submit(
                    self.translator.translate,
                    text, source_lang, target_lang, provider
                ): text for text in texts
            }
            
            # Collect results
            for future in as_completed(future_to_text):
                text = future_to_text[future]
                try:
                    result = future.result()
                    results.append({
                        'original': text,
                        'translation': result,
                        'provider': provider,
                        'success': True
                    })
                except Exception as e:
                    results.append({
                        'original': text,
                        'translation': None,
                        'error': str(e),
                        'success': False
                    })
        
        return results
    
    def process_csv(self, input_csv: str, output_csv: str, 
                   text_column: str = 'text', provider: str = None):
        """Process CSV file with translations."""
        
        # Read input CSV
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Extract texts
        texts = [row[text_column] for row in rows]
        
        # Translate batch
        results = self.translate_batch(texts, provider=provider)
        
        # Add translations to rows
        for row, result in zip(rows, results):
            row['translation'] = result['translation']
            row['provider'] = result.get('provider', 'default')
            row['success'] = result['success']
            if not result['success']:
                row['error'] = result.get('error')
        
        # Write output CSV
        fieldnames = list(rows[0].keys())
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

# Usage
if __name__ == "__main__":
    batch_translator = BatchTranslator("config.yaml")
    
    # Example: Process CSV with different providers
    providers = ["@dspy/wordnet", "@princeton/wordnet", "wordnet"]
    
    for provider in providers:
        output_file = f"translations_{provider.replace('/', '_').replace('@', '')}.csv"
        batch_translator.process_csv(
            "input.csv", 
            output_file,
            provider=provider
        )
        print(f"Processed with {provider} -> {output_file}")
```

### Testing Integration

```python
"""Testing your integration with WordNet AutoTranslate."""

import unittest
from wordnet_autotranslate import WordNetAutoTranslator, Config, NWOProvider

class TestWordNetIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test configuration."""
        self.config_data = {
            'providers': {
                'test_dspy': '@dspy/wordnet',
                'test_princeton': '@princeton/wordnet',
                'test_legacy': 'wordnet'
            }
        }
        self.translator = WordNetAutoTranslator(self.config_data)
    
    def test_nwo_provider_parsing(self):
        """Test NWO format parsing."""
        provider = NWOProvider.parse("@dspy/wordnet@2.0.0")
        
        self.assertEqual(provider.namespace, "dspy")
        self.assertEqual(provider.name, "wordnet")
        self.assertEqual(provider.version, "2.0.0")
        self.assertFalse(provider.is_legacy_format())
    
    def test_legacy_provider_parsing(self):
        """Test legacy format parsing."""
        provider = NWOProvider.parse("wordnet")
        
        self.assertIsNone(provider.namespace)
        self.assertEqual(provider.name, "wordnet")
        self.assertIsNone(provider.version)
        self.assertTrue(provider.is_legacy_format())
    
    def test_translation_with_providers(self):
        """Test translation with different providers."""
        test_text = "hello world"
        providers = ["@dspy/wordnet", "@princeton/wordnet", "wordnet"]
        
        for provider in providers:
            with self.subTest(provider=provider):
                result = self.translator.translate(test_text, provider=provider)
                self.assertIsInstance(result, str)
                self.assertGreater(len(result), 0)
    
    def test_language_support(self):
        """Test language support querying."""
        languages = self.translator.get_supported_languages()
        
        self.assertIsInstance(languages, list)
        self.assertIn('en', languages)
        self.assertIn('es', languages)
    
    def test_synset_retrieval(self):
        """Test WordNet synset retrieval."""
        synsets = self.translator.get_wordnet_synsets("cat")
        
        self.assertIsInstance(synsets, list)
        self.assertGreater(len(synsets), 0)
    
    def test_error_handling(self):
        """Test error handling."""
        with self.assertRaises(ValueError):
            NWOProvider.parse("@invalid/format/with/too/many/slashes")

if __name__ == '__main__':
    unittest.main()
```

## Production Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package
RUN pip install -e .

# Download NLTK data
RUN python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "wordnet_autotranslate.cli", "--help"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  wordnet-autotranslate:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./data:/app/data
    environment:
      - WORDNET_CONFIG_PATH=/app/config.yaml
      - PYTHONPATH=/app
    command: python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wordnet-autotranslate
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wordnet-autotranslate
  template:
    metadata:
      labels:
        app: wordnet-autotranslate
    spec:
      containers:
      - name: wordnet-autotranslate
        image: wordnet-autotranslate:latest
        ports:
        - containerPort: 8000
        env:
        - name: WORDNET_CONFIG_PATH
          value: "/app/config.yaml"
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
      volumes:
      - name: config
        configMap:
          name: wordnet-config

---
apiVersion: v1
kind: Service
metadata:
  name: wordnet-autotranslate-service
spec:
  selector:
    app: wordnet-autotranslate
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Performance Optimization

### Caching

```python
from functools import lru_cache
from wordnet_autotranslate import WordNetAutoTranslator, Config

class CachedTranslator:
    def __init__(self, config_path: str = None):
        config = Config.from_file(config_path) if config_path else None
        self.translator = WordNetAutoTranslator(config)
    
    @lru_cache(maxsize=1000)
    def translate_cached(self, text: str, source_lang: str = "en", 
                        target_lang: str = "es", provider: str = None):
        """Cached translation for repeated requests."""
        return self.translator.translate(text, source_lang, target_lang, provider)
    
    @lru_cache(maxsize=500)
    def get_synsets_cached(self, word: str, lang: str = "en", provider: str = None):
        """Cached synset retrieval."""
        return self.translator.get_wordnet_synsets(word, lang, provider)
```

### Connection Pooling

```python
import threading
from wordnet_autotranslate import WordNetAutoTranslator, Config

class TranslatorPool:
    def __init__(self, config_path: str = None, pool_size: int = 5):
        self.config_path = config_path
        self.pool_size = pool_size
        self.translators = []
        self.lock = threading.Lock()
        
        # Initialize pool
        for _ in range(pool_size):
            config = Config.from_file(config_path) if config_path else None
            translator = WordNetAutoTranslator(config)
            self.translators.append(translator)
    
    def get_translator(self):
        """Get a translator from the pool."""
        with self.lock:
            if self.translators:
                return self.translators.pop()
            else:
                # Create new translator if pool is empty
                config = Config.from_file(self.config_path) if self.config_path else None
                return WordNetAutoTranslator(config)
    
    def return_translator(self, translator):
        """Return a translator to the pool."""
        with self.lock:
            if len(self.translators) < self.pool_size:
                self.translators.append(translator)
```

## Troubleshooting

### Common Issues

1. **NLTK Data Missing**: Run `python -c "import nltk; nltk.download('wordnet')"`
2. **DSPy Not Available**: Install with `pip install dspy-ai`
3. **Permission Errors**: Check file permissions for config files
4. **Memory Issues**: Reduce batch sizes or implement streaming

### Debugging

```python
import logging
from wordnet_autotranslate import WordNetAutoTranslator

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

translator = WordNetAutoTranslator()

# Debug provider information
providers = translator.get_available_providers()
for name, provider in providers.items():
    print(f"Provider {name}: {provider.to_string()} (legacy: {provider.is_legacy_format()})")
```

This integration guide covers the most common use cases for WordNet AutoTranslate with NWO format support. For more specific requirements, refer to the API documentation and examples in the repository.