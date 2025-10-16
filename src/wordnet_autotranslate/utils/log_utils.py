"""Utility functions for saving and analyzing full LLM logs from translation pipeline."""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def save_full_logs(
    result: Dict[str, Any], 
    output_path: str | Path = None,
    include_prompts: bool = True,
    include_messages: bool = True
) -> Path:
    """Save complete untruncated LLM logs to a JSON file.
    
    Args:
        result: Translation result dict from pipeline.translate_synset()
        output_path: Where to save the logs. If None, auto-generates filename.
        include_prompts: Whether to include full prompt text (default: True)
        include_messages: Whether to include message history (default: True)
        
    Returns:
        Path to saved log file.
        
    Example:
        >>> result = pipeline.translate_synset(synset)
        >>> log_path = save_full_logs(result)
        >>> print(f"Logs saved to: {log_path}")
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        synset_id = result.get("source", {}).get("id", "unknown").replace(":", "_")
        output_path = Path(f"logs/full_log_{synset_id}_{timestamp}.json")
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract all full calls
    full_logs = {
        "metadata": {
            "synset_id": result["source"]["id"],
            "translation": result["translation"],
            "target_lang": result["target_lang"],
            "source_lang": result["source_lang"],
            "timestamp": datetime.now().isoformat(),
            "translated_synonyms": result["translated_synonyms"],
        },
        "stages": {}
    }
    
    # Add each stage's complete data
    for stage, call in result["payload"]["calls"].items():
        stage_data = {
            "stage": call.get("stage", ""),
            "raw_response": call.get("raw_response", ""),
            "raw_response_length": len(call.get("raw_response", "")),
            "parsed_payload": call.get("payload", {}),
        }
        
        if include_prompts:
            stage_data["prompt"] = call.get("prompt", "")
            stage_data["system_prompt"] = call.get("system_prompt", "")
        
        if include_messages:
            stage_data["messages"] = call.get("messages", [])
        
        full_logs["stages"][stage] = stage_data
    
    # Save with pretty formatting
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_logs, f, indent=2, ensure_ascii=False)
    
    return output_path


def save_batch_logs(
    results: List[Dict[str, Any]], 
    output_dir: str | Path = "logs/batch"
) -> Path:
    """Save full logs for multiple synsets to a directory.
    
    Args:
        results: List of translation results from pipeline.translate()
        output_dir: Directory to save individual log files
        
    Returns:
        Path to output directory.
        
    Example:
        >>> results = pipeline.translate(synsets[:10])
        >>> log_dir = save_batch_logs(results)
        >>> print(f"Saved {len(results)} log files to: {log_dir}")
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i, result in enumerate(results):
        synset_id = result.get("source", {}).get("id", f"synset_{i}").replace(":", "_")
        output_path = output_dir / f"{synset_id}.json"
        save_full_logs(result, output_path)
    
    # Create index file
    index_path = output_dir / "_index.json"
    index_data = {
        "total_synsets": len(results),
        "timestamp": datetime.now().isoformat(),
        "synsets": [
            {
                "id": r["source"]["id"],
                "translation": r["translation"],
                "filename": f"{r['source']['id'].replace(':', '_')}.json"
            }
            for r in results
        ]
    }
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    return output_dir


def analyze_stage_lengths(result: Dict[str, Any]) -> Dict[str, int]:
    """Analyze the length of raw responses for each stage.
    
    Args:
        result: Translation result from pipeline
        
    Returns:
        Dict mapping stage names to response lengths in characters.
        
    Example:
        >>> lengths = analyze_stage_lengths(result)
        >>> for stage, length in lengths.items():
        >>>     print(f"{stage}: {length:,} chars")
    """
    return {
        stage: len(call.get("raw_response", ""))
        for stage, call in result["payload"]["calls"].items()
    }


def extract_validation_errors(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract any validation errors or warnings from pipeline stages.
    
    Args:
        result: Translation result from pipeline
        
    Returns:
        List of validation issues found during processing.
    """
    errors = []
    
    for stage, payload in result["payload"].items():
        if stage in ["calls", "logs"]:
            continue
        
        if isinstance(payload, dict) and "error" in payload:
            errors.append({
                "stage": stage,
                "error": payload["error"]
            })
    
    return errors


if __name__ == "__main__":
    print("LLM Log Utilities")
    print("=" * 50)
    print("\nAvailable functions:")
    print("  - save_full_logs(result) - Save complete logs for one synset")
    print("  - save_batch_logs(results) - Save logs for multiple synsets")
    print("  - analyze_stage_lengths(result) - Check response sizes")
    print("  - extract_validation_errors(result) - Find any errors")
