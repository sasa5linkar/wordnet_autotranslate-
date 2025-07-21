"""
Setup configuration for WordNet Auto-Translation package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() for line in f 
            if line.strip() and not line.startswith('#')
        ]
else:
    requirements = []

setup(
    name="wordnet-autotranslate",
    version="0.1.0",
    author="WordNet Auto-Translation Contributors",
    description="Automatic expansion of WordNet in less-resourced languages using DSPy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sasa5linkar/wordnet_autotranslate-",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "notebooks": [
            "jupyter>=1.0.0",
            "jupyterlab>=4.0.0",
            "ipywidgets>=8.0.0",
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
        ],
        "gui": [
            "streamlit>=1.25.0",
            "gradio>=3.35.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "wordnet-autotranslate=wordnet_autotranslate.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)