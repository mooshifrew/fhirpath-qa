import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# FHIR Server Configuration
HAPI_URL = os.getenv("HAPI_URL", "http://localhost:8080/fhir")
NDJSON_BASE = os.getenv("NDJSON_BASE", "http://host.docker.internal:8000")

# Data Directory Configuration
DATA_DIR = PROJECT_ROOT / "compose" / "data"
PATIENT_BUNDLES_DIR = PROJECT_ROOT / "patient_bundles"
OUTPUT_DIR = PROJECT_ROOT / "output"

# HTTP Server Configuration (for serving files to Docker)
HTTP_SERVER_HOST = "0.0.0.0"  # Listen on all interfaces
HTTP_SERVER_PORT = 8000
HTTP_SERVER_DIR = DATA_DIR


# Valueset Configuration
VALUESETS_DIR = PROJECT_ROOT / "fhirpath_gen" / "valuesets"

# Patient Data Configuration
PATIENT_IDS_FILE = PROJECT_ROOT / "patient_ids.txt"

# FHIRPath Evaluation Configuration
# Path to the octofhir-fhirpath executable for query evaluation
# Download from: https://github.com/octofhir/octofhir-fhirpath/releases
# or install with cargo (and add to PATH)
FHIRPATH_EXE = os.getenv("FHIRPATH_EXE", r"path_to_octofhir-fhirpath.exe")

# Ensure directories exist
for directory in [PATIENT_BUNDLES_DIR, OUTPUT_DIR]:
    directory.mkdir(exist_ok=True)
