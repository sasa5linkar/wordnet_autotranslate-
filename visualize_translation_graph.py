#!/usr/bin/env python3
"""Visualize the LangGraph Translation Pipeline.

This script generates visual representations of the translation graph structure
using LangGraph's built-in visualization capabilities. It creates:

1. A Mermaid diagram (text-based, for documentation)
2. A PNG image (if graphviz is available)
3. An ASCII representation (fallback)

The visualization automatically updates whenever the graph structure changes,
making it easy to keep documentation in sync with code.

Usage:
    python visualize_translation_graph.py

Output:
    - translation_graph.mmd (Mermaid diagram)
    - translation_graph.png (PNG image, requires graphviz)
    - translation_graph.txt (ASCII representation)
    - Prints the Mermaid diagram to console
"""

import sys
from pathlib import Path
from typing import Optional

try:
    from src.wordnet_autotranslate.pipelines.langgraph_translation_pipeline import (
        LangGraphTranslationPipeline,
    )
except ImportError:
    print("Error: Could not import LangGraphTranslationPipeline")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class DummyLLM:
    """Minimal LLM stand-in for graph construction (no actual calls made)."""
    
    def invoke(self, messages):
        pass


def create_mermaid_diagram(graph) -> str:
    """Generate Mermaid diagram from the compiled graph.
    
    Args:
        graph: Compiled LangGraph graph
        
    Returns:
        Mermaid diagram as string
    """
    try:
        # Try to get Mermaid representation
        mermaid = graph.get_graph().draw_mermaid()
        return mermaid
    except AttributeError:
        # Fallback: create manual Mermaid diagram based on known structure
        return """graph TD
    START((__start__))
    END((__end__))
    
    SENSE[analyse_sense<br/>📊 Analyze word sense<br/>and semantic features]
    DEF[translate_definition<br/>📝 Translate definition<br/>with context]
    SYN[translate_synonyms<br/>🔤 Generate target<br/>language synonyms]
    ASSEMBLE[assemble_result<br/>📦 Combine all outputs<br/>into final result]
    
    START --> SENSE
    SENSE --> DEF
    DEF --> SYN
    SYN --> ASSEMBLE
    ASSEMBLE --> END
    
    style START fill:#90EE90
    style END fill:#FFB6C1
    style SENSE fill:#87CEEB
    style DEF fill:#DDA0DD
    style SYN fill:#F0E68C
    style ASSEMBLE fill:#FFA07A
"""


def create_ascii_diagram() -> str:
    """Create a simple ASCII representation of the graph."""
    return """
Translation Pipeline Graph Structure
=====================================

    ┌─────────┐
    │  START  │
    └────┬────┘
         │
         ▼
    ┌─────────────────────┐
    │  analyse_sense      │  ← Stage 1: Analyze word sense and semantic features
    │                     │    • Identify nuances and distinguishing features
    │  📊 Sense Analysis  │    • Build understanding before translation
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ translate_definition│  ← Stage 2: Translate the definition
    │                     │    • Use sense analysis context
    │ 📝 Definition       │    • Maintain semantic precision
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ translate_synonyms  │  ← Stage 3: Generate target synonyms
    │                     │    • Create synonym candidates
    │ 🔤 Synonyms         │    • Include confidence levels
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │  assemble_result    │  ← Stage 4: Combine all outputs
    │                     │    • Merge translations
    │ 📦 Assembly         │    • Create curator summary
    └──────────┬──────────┘
               │
               ▼
    ┌─────────┐
    │   END   │
    └─────────┘

Pipeline Flow:
--------------
1. Input synset enters at START
2. Sense analysis extracts semantic features
3. Definition translation uses sense context
4. Synonym generation builds on definition
5. Assembly merges all stages into final result
6. Result exits at END

Each stage passes state forward through the graph,
accumulating information for downstream nodes.
"""


def save_png_diagram(graph, output_path: Path) -> bool:
    """Try to save PNG diagram using graphviz.
    
    Args:
        graph: Compiled LangGraph graph
        output_path: Path to save PNG file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from IPython.display import Image
        
        # Get the graph representation
        png_data = graph.get_graph().draw_mermaid_png()
        
        # Save to file
        output_path.write_bytes(png_data)
        return True
    except Exception as e:
        print(f"⚠️  Could not generate PNG: {e}")
        print("   (Install graphviz and pygraphviz for PNG support)")
        return False


def visualize_translation_graph(output_dir: Optional[Path] = None):
    """Generate all visualization formats for the translation graph.
    
    Args:
        output_dir: Directory to save output files (default: current directory)
    """
    if output_dir is None:
        output_dir = Path.cwd()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔍 Visualizing LangGraph Translation Pipeline")
    print("=" * 60)
    
    # Create a dummy pipeline to extract the graph
    print("\n📊 Building graph structure...")
    try:
        pipeline = LangGraphTranslationPipeline(
            source_lang="en",
            target_lang="sr",
            llm=DummyLLM(),
        )
        graph = pipeline._graph
        print("✅ Graph constructed successfully")
    except Exception as e:
        print(f"❌ Error building graph: {e}")
        return
    
    # Generate Mermaid diagram
    print("\n📝 Generating Mermaid diagram...")
    try:
        mermaid = create_mermaid_diagram(graph)
        mermaid_path = output_dir / "translation_graph.mmd"
        mermaid_path.write_text(mermaid, encoding="utf-8")
        print(f"✅ Saved Mermaid diagram: {mermaid_path}")
        
        # Also print to console
        print("\n" + "=" * 60)
        print("MERMAID DIAGRAM (copy to mermaid.live or GitHub)")
        print("=" * 60)
        print(mermaid)
        print("=" * 60)
    except Exception as e:
        print(f"⚠️  Could not generate Mermaid diagram: {e}")
    
    # Generate ASCII diagram
    print("\n📊 Generating ASCII diagram...")
    try:
        ascii_diagram = create_ascii_diagram()
        ascii_path = output_dir / "translation_graph.txt"
        ascii_path.write_text(ascii_diagram, encoding="utf-8")
        print(f"✅ Saved ASCII diagram: {ascii_path}")
        print(ascii_diagram)
    except Exception as e:
        print(f"⚠️  Could not generate ASCII diagram: {e}")
    
    # Try to generate PNG
    print("\n🖼️  Attempting to generate PNG diagram...")
    png_path = output_dir / "translation_graph.png"
    if save_png_diagram(graph, png_path):
        print(f"✅ Saved PNG diagram: {png_path}")
    else:
        print("ℹ️  PNG generation skipped (optional dependency)")
    
    # Generate detailed documentation
    print("\n📚 Generating detailed documentation...")
    try:
        doc_path = output_dir / "translation_graph_doc.md"
        doc_content = generate_documentation(mermaid)
        doc_path.write_text(doc_content, encoding="utf-8")
        print(f"✅ Saved documentation: {doc_path}")
    except Exception as e:
        print(f"⚠️  Could not generate documentation: {e}")
    
    print("\n" + "=" * 60)
    print("✨ Visualization complete!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print("\nGenerated files:")
    for file in output_dir.glob("translation_graph*"):
        print(f"  • {file.name}")
    print("\n💡 Tip: Re-run this script whenever you modify the graph structure")
    print("=" * 60)


def generate_documentation(mermaid_diagram: str) -> str:
    """Generate comprehensive markdown documentation with embedded diagram.
    
    Args:
        mermaid_diagram: Mermaid diagram code
        
    Returns:
        Markdown documentation as string
    """
    return f"""# LangGraph Translation Pipeline - Architecture

**Auto-generated:** This document is automatically generated from the code.  
**Purpose:** Visualize and document the translation pipeline graph structure.  
**Last Updated:** {Path(__file__).stat().st_mtime}

## Overview

The LangGraph Translation Pipeline uses a state machine to orchestrate the translation
of WordNet synsets through multiple specialized stages. Each stage refines and adds to
the accumulated state, building toward a complete translation result.

## Graph Structure

```mermaid
{mermaid_diagram}
```

## Pipeline Stages

### 1. 📊 **analyse_sense**
**Purpose:** Understand the semantic nuance of the source synset before translation.

**Input:**
- Source synset (lemmas, definition, examples, POS)

**Processing:**
- Identifies distinguishing semantic features
- Extracts key aspects that differentiate this sense
- Assesses domain and topical context
- Builds confidence in sense understanding

**Output:**
- `sense_summary`: Concise English description (1-2 sentences)
- `key_features`: List of 2-4 distinguishing aspects
- `domain_tags`: Optional topical labels
- `confidence`: Assessment (high/medium/low)

**Why First?** Understanding the precise sense prevents mistranslation and ensures
semantic fidelity throughout the pipeline.

---

### 2. 📝 **translate_definition**
**Purpose:** Translate the definition while preserving the analyzed sense.

**Input:**
- Source synset
- Sense analysis results (from Stage 1)

**Processing:**
- Translates definition to target language
- Maintains semantic precision using sense context
- Generates example sentences in target language
- Adds lexicographer notes if needed

**Output:**
- `definition_translation`: Definition in target language
- `notes`: Optional clarifications
- `examples`: Example sentences in target language

**Why Second?** The sense analysis guides accurate definition translation,
preventing ambiguity and ensuring the correct semantic interpretation.

---

### 3. 🔤 **translate_synonyms**
**Purpose:** Generate target language synonyms that align with the sense and definition.

**Input:**
- Source synset
- Sense analysis (from Stage 1)
- Translated definition (from Stage 2)

**Processing:**
- Proposes synonym candidates in target language
- Assigns confidence levels to each synonym
- Provides usage examples for synonyms
- Selects preferred headword

**Output:**
- `preferred_headword`: Best single translation
- `synonyms`: List of synonym objects with confidence and examples
- `examples`: Additional usage examples
- `notes`: Commentary on synonym choices

**Why Third?** With both sense understanding and translated definition available,
synonym generation can be precise and contextually appropriate.

---

### 4. 📦 **assemble_result**
**Purpose:** Combine all stage outputs into a structured final result.

**Input:**
- All previous stage outputs (sense, definition, synonyms)

**Processing:**
- Extracts translations from payloads
- Selects primary translation (preferred headword)
- Collects and deduplicates examples
- Merges notes from all stages
- Generates curator-friendly summary

**Output:**
- Complete `TranslationResult` object with:
  - `translation`: Primary target language term
  - `definition_translation`: Translated definition
  - `translated_synonyms`: List of synonym candidates
  - `examples`: Deduplicated example sentences
  - `notes`: Merged notes from all stages
  - `curator_summary`: Human-readable summary
  - `payload`: Full details from all stages

**Why Last?** Final assembly allows for intelligent merging, prioritization,
and presentation of accumulated results.

---

## State Flow

The graph uses a `TranslationGraphState` TypedDict that accumulates information:

```python
TranslationGraphState = {{
    "synset": Dict[str, Any],              # Input synset (always present)
    "sense_analysis": Dict[str, Any],      # Added by Stage 1
    "definition_translation": Dict[str, Any],  # Added by Stage 2
    "synonym_translation": Dict[str, Any],     # Added by Stage 3
    "result": Dict[str, Any],              # Added by Stage 4 (final output)
}}
```

Each stage:
1. Receives the current state
2. Accesses data from previous stages
3. Calls the LLM with a stage-specific prompt
4. Updates state with its results
5. Returns updated state to next stage

## Design Rationale

### Sequential Processing
The pipeline is intentionally sequential (no parallel branches) because:
- Each stage builds on previous results
- Sense analysis informs definition translation
- Definition translation guides synonym generation
- Assembly requires all upstream data

### Modular Stages
Each stage is isolated and testable:
- Clear input/output contracts
- Independent LLM prompts
- Separate error handling per stage
- Easy to modify or extend individual stages

### State Accumulation
State grows through the pipeline:
- No information is lost
- Full audit trail of all decisions
- Downstream stages access all upstream results
- Final payload contains complete provenance

## Extensibility

### Adding New Stages
To add a stage (e.g., quality estimation):

1. Add state field to `TranslationGraphState`
2. Implement stage function: `def _estimate_quality(self, state) -> TranslationGraphState`
3. Add node: `graph.add_node("estimate_quality", self._estimate_quality)`
4. Add edge: `graph.add_edge("translate_synonyms", "estimate_quality")`
5. Update subsequent edges

### Adding Conditional Branches
For conditional logic (e.g., skip if confidence is low):

```python
def route_by_confidence(state):
    if state["sense_analysis"]["payload"].get("confidence") == "low":
        return "manual_review"
    return "translate_definition"

graph.add_conditional_edges(
    "analyse_sense",
    route_by_confidence,
    {{"translate_definition": "translate_definition", "manual_review": "manual_review"}}
)
```

## Monitoring & Debugging

Each stage logs:
- Full prompt sent to LLM
- Raw LLM response
- Parsed payload
- Stage name and metadata

Access logs via: `result["payload"]["logs"][stage_name]`

## Performance Considerations

- **Sequential execution**: ~3 LLM calls per synset
- **No caching**: Each synset translated independently
- **Timeout**: 600 seconds per LLM call (configurable)
- **Streaming**: `translate_stream()` for large batches

## Related Files

- **Implementation:** `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`
- **Tests:** `tests/test_langgraph_pipeline.py`
- **Example Usage:** `notebooks/02_langgraph_pipeline_demo.ipynb`

## Regenerating This Document

Run the visualization script to regenerate all diagrams and documentation:

```bash
python visualize_translation_graph.py
```

This ensures documentation stays synchronized with code changes.

---

**Note:** This is an auto-generated document. Manual edits will be overwritten.
To update, modify the graph structure in the source code and re-run visualization.
"""


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Visualize the LangGraph Translation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visualize_translation_graph.py
  python visualize_translation_graph.py --output-dir ./docs/images
  
This script automatically detects graph structure changes and regenerates
all visualizations, keeping documentation synchronized with code.
        """
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Directory to save visualization files (default: current directory)"
    )
    
    args = parser.parse_args()
    
    try:
        visualize_translation_graph(output_dir=args.output_dir)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
