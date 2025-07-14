"""Setup configuration for wordnet_autotranslate package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="wordnet_autotranslate",
    version="0.1.0",
    author="WordNet AutoTranslate Team",
    description="Automatic translation system with WordNet integration supporting NWO format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "nltk>=3.8",
        "dspy-ai>=2.0.0",
        "numpy>=1.21.0",
        "PyYAML>=6.0",
        "requests>=2.25.0",
    ],
    extras_require={
        "test": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
            "mock>=4.0.0",
        ],
        "dev": [
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.900",
        ],
    },
)