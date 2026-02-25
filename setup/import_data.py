#!/usr/bin/env python3
import os
import sys
import time
import requests
import tempfile
import shutil
from pathlib import Path

# Add config to path (parent directory)
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import HAPI_URL, NDJSON_BASE, DATA_DIR
except ImportError:
    print("Error: config.py not found. Please ensure config.py exists.")
    sys.exit(1)

POLL_HEADERS = {"Accept": "application/json"}

# Define each import "part" as a list of (resourceType, filename)
# Note: ObservationChartevents will be split dynamically
import_sequence = [
    # part 1
    [
        ("Patient", "Patient.ndjson"),
        ("Encounter", "EncounterICU.ndjson"),
        ("Location", "Location.ndjson"),
        ("Encounter", "Encounter.ndjson"),
        ("Organization", "Organization.ndjson"),
        ("Condition", "Condition.ndjson"),
        ("Procedure", "Procedure.ndjson"),
        ("Procedure", "ProcedureICU.ndjson"),
        ("Medication", "Medication.ndjson"),
        ("MedicationRequest", "MedicationRequest.ndjson"),
        ("MedicationDispense", "MedicationDispense.ndjson"),
        ("MedicationAdministration", "MedicationAdministration.ndjson"),
        ("MedicationAdministration", "MedicationAdministrationICU.ndjson"),
        ("Specimen", "Specimen.ndjson"),
        ("Specimen", "SpecimenLab.ndjson"),
    ],
    # part 2
    [
        ("Observation", "ObservationLabevents.ndjson"),
        ("Observation", "ObservationDatetimeevents.ndjson"),
        ("Observation", "ObservationOutputevents.ndjson"),
        ("Observation", "ObservationMicroTest.ndjson"),
        ("Observation", "ObservationMicroOrg.ndjson"),
        ("Observation", "ObservationMicroSusc.ndjson"),
    ],
]


def split_ndjson(input_path, output_prefix, num_splits=4):
    """Split a large NDJSON file into smaller files."""
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    split_size = total_lines // num_splits
    remainder = total_lines % num_splits

    split_files = []
    start = 0
    for i in range(num_splits):
        end = start + split_size + (1 if i < remainder else 0)
        output_path = f"{output_prefix}_part{i+1}.ndjson"
        with open(output_path, "w", encoding="utf-8") as out_f:
            out_f.writelines(lines[start:end])
        print(f"Wrote {end - start} lines to {output_path}")
        split_files.append(output_path)
        start = end

    return split_files


def build_payload(files):
    params = [
        {"name": "inputFormat", "valueCode": "application/fhir+ndjson"},
        {
            "name": "storageDetail",
            "part": [
                {"name": "type", "valueCode": "https"},
                {"name": "maxBatchResourceCount", "valueString": "200"},
            ],
        },
    ]
    for rtype, fname in files:
        params.append(
            {
                "name": "input",
                "part": [
                    {"name": "type", "valueCode": rtype},
                    {"name": "url", "valueUri": f"{NDJSON_BASE}/{fname}"},
                ],
            }
        )
    return {"resourceType": "Parameters", "parameter": params}


def submit_import(payload):
    url = f"{HAPI_URL}/$import"
    headers = {"Prefer": "respond-async", "Content-Type": "application/fhir+json"}
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 202:
        print(
            f"[ERROR] Failed to start import: {resp.status_code}\n{resp.text}",
            file=sys.stderr,
        )
        sys.exit(1)
    # Get polling URL
    poll_url = resp.headers.get("Content-Location")
    if not poll_url:
        print(
            "[ERROR] No Content-Location header; cannot poll status.", file=sys.stderr
        )
        sys.exit(1)
    print(f"[INFO] Job submitted; polling status at {poll_url}")
    return poll_url


def poll_until_complete(poll_url):
    while True:
        resp = requests.get(poll_url, headers=POLL_HEADERS)
        if resp.status_code == 202:
            progress = resp.headers.get("X-Progress", "").strip()
            retry_after = resp.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else 5
            print(f"[POLL] In progress... {progress or ''}(waiting {wait}s)")
            time.sleep(wait)
        elif resp.status_code == 200:
            print("[POLL] ✔ Import complete.")
            return resp.json()  # you can inspect the final outcome if you like
        else:
            print(
                f"[ERROR] Polling failed ({resp.status_code}): {resp.text}",
                file=sys.stderr,
            )
            resp.raise_for_status()


def main():
    """Run all import jobs with automatic file splitting and cleanup."""
    temp_files = []  # Track temporary files for cleanup

    try:
        # First, handle the smaller files import sequence (parts 1-2)
        for idx, files in enumerate(import_sequence, start=1):
            print(f"\n=== Starting import part {idx} ===")
            payload = build_payload(files)
            poll_url = submit_import(payload)
            poll_until_complete(poll_url)

        # import large ObservationChartevents.ndjson file by splitting it
        chartevents_file = DATA_DIR / "ObservationChartevents.ndjson"
        if chartevents_file.exists():
            print(f"\n=== Splitting large file: {chartevents_file.name} ===")

            # Create split files in the DATA_DIR so the HTTP server can access them
            temp_prefix = str(DATA_DIR / "ObservationChartevents")

            # Split the file into 4 parts
            split_files = split_ndjson(str(chartevents_file), temp_prefix, num_splits=4)
            temp_files.extend(split_files)

            # Import each split file as a separate part
            for i, split_file in enumerate(split_files, start=3):
                print(f"\n=== Starting import part {i} (split file) ===")
                files = [("Observation", os.path.basename(split_file))]

                payload = build_payload(files)
                poll_url = submit_import(payload)
                poll_until_complete(poll_url)
        else:
            print(
                f"Warning: {chartevents_file} not found, skipping chart events import"
            )

        print("\n✅ All import jobs finished successfully.")

    finally:
        # Clean up temporary files
        if temp_files:
            print("\n=== Cleaning up temporary files ===")
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    print(f"Removed: {temp_file}")
                except OSError as e:
                    print(f"Warning: Could not remove {temp_file}: {e}")


if __name__ == "__main__":
    main()
