#!/usr/bin/env python3
"""
Setup script for FHIRPath-QA project.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="fhirpath-qa",
    version="0.1.0",
    author="Michael Frew",
    author_email="michael.frew@uwaterloo.ca",
    description="Question-FHIRPath Query generation system for MIMIC-IV on FHIR data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mooshifrew/fhirpath-qa",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
            "mypy>=0.800",
        ],
    },
    entry_points={
        "console_scripts": [
            "fhirpath-qa-generate=generate_questions:main",
        ],
    },
    include_package_data=True,
    package_data={
        "fhirpath_gen": [
            "valuesets/*.json",
        ],
    },
)
