# Translation Graph Visualization

This directory contains auto-generated visualizations of the LangGraph Translation Pipeline.

## Generated Files

### 📊 `translation_graph.mmd`
Mermaid diagram source code. You can:
- Copy to [mermaid.live](https://mermaid.live) for interactive viewing
- Use directly in GitHub markdown (renders automatically)
- Include in documentation

### 🖼️ `translation_graph.png`
PNG image of the graph structure. Useful for:
- Presentations
- Documentation
- Quick reference

### 📝 `translation_graph.txt`
ASCII art representation. Great for:
- Terminal viewing
- Text-only documentation
- Quick overview without graphics

### 📚 `translation_graph_doc.md`
Comprehensive documentation including:
- Graph structure with embedded Mermaid diagram
- Detailed explanation of each stage
- State flow description
- Design rationale
- Extensibility guide

## How to Regenerate

Run the visualization script whenever you modify the graph structure:

```bash
python visualize_translation_graph.py
```

This ensures all visualizations stay in sync with the code.

### Custom Output Directory

```bash
python visualize_translation_graph.py --output-dir ./docs/images
```

## Graph Structure Overview

```
START → analyse_sense → translate_definition → translate_synonyms → assemble_result → END
```

Each stage:
1. **analyse_sense**: Understand semantic nuances before translation
2. **translate_definition**: Translate definition using sense context
3. **translate_synonyms**: Generate synonym candidates with confidence
4. **assemble_result**: Combine all outputs into final result

## Viewing Options

### Option 1: View PNG Image
Open `translation_graph.png` in any image viewer.

### Option 2: View in Browser
Copy `translation_graph.mmd` content to [mermaid.live](https://mermaid.live)

### Option 3: View in VS Code
Install the "Markdown Preview Mermaid Support" extension and view `translation_graph_doc.md`

### Option 4: Terminal View
```bash
cat translation_graph.txt
```

## Automatic Updates

The visualization script:
- ✅ Detects graph structure from code
- ✅ Generates multiple formats automatically
- ✅ Creates comprehensive documentation
- ✅ Keeps everything in sync

**Best Practice:** Add `visualize_translation_graph.py` to your development workflow.
Run it after any graph structure changes to ensure documentation stays current.

## Integration with CI/CD

You can add this to your CI pipeline to ensure diagrams are always up-to-date:

```yaml
- name: Generate graph visualizations
  run: python visualize_translation_graph.py --output-dir ./docs
```

---

**Auto-generated visualizations:** These files are created by `visualize_translation_graph.py`
and should be regenerated rather than manually edited.
