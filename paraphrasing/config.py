"""Configuration constants for the paraphrasing pipeline."""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# LLM Configuration
MODEL = os.getenv("PARAPHRASE_MODEL", "gpt-4o")  # must support structured outputs
TEMPERATURE = 0.7
BATCH_SIZE = 8  # Paraphrases per API call
MAX_PARAPHRASES_PER_TEMPLATE = 15  # Target number of unique paraphrases
MAX_RETRIES = 3  # Maximum API retry attempts

# Quality Control Thresholds
SIMILARITY_THRESHOLD = 0.7  # Minimum semantic similarity (0.0-1.0)
MIN_EDIT_DISTANCE = 10  # Minimum character difference for deduplication
MIN_NORMALIZED_DISTANCE = 0.15  # Minimum normalized edit distance (0.0-1.0)

# File Paths
TEMPLATES_FILE = PROJECT_ROOT / "id2question_templates.json"
OUTPUT_FILE = PROJECT_ROOT / "fhirpath_gen" / "template_paraphrases_patient.json"

# Sentence Transformer Model
SEMANTIC_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
