#!/usr/bin/env python3
"""
Launcher script for the Serbian WordNet Synset Browser GUI.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Launch the Streamlit GUI application."""
    # Get the path to the synset browser script
    script_path = Path(__file__).parent / "src" / "wordnet_autotranslate" / "gui" / "synset_browser.py"
    
    if not script_path.exists():
        print(f"Error: Could not find synset browser script at {script_path}")
        sys.exit(1)
    
    # Launch Streamlit with the synset browser
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(script_path),
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--server.headless=true"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()