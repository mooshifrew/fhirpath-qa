import requests
from pprint import pprint
import json
import sys
from pathlib import Path

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import HAPI_URL

    FHIR_BASE = HAPI_URL
except ImportError:
    FHIR_BASE = "http://localhost:8080/fhir"  # fallback


def get_patient_identifier(patient_id):
    url = f"{FHIR_BASE}/Patient/{patient_id}"
    resp = requests.get(url, headers={"Accept": "application/fhir+json"})
    resp.raise_for_status()
    patient = resp.json()
    # There may be multiple identifiers, pick the first, or add logic for specific system
    identifier_value = None
    identifiers = patient.get("identifier", [])
    if identifiers:
        # Use the first identifier value
        identifier_value = identifiers[0].get("value")
    return identifier_value


def get_all_patient_ids(fhir_base):
    """Fetches all Patient IDs, handling pagination."""
    patient_ids = []
    url = f"{fhir_base}/Patient?_elements=id&_count=20"
    while url:
        print(f"Fetching: {url}")
        resp = requests.get(url, headers={"Accept": "application/fhir+json"})
        resp.raise_for_status()
        bundle = resp.json()
        # Add Patient IDs from this page
        for entry in bundle.get("entry", []):
            patient_id = entry["resource"]["id"]
            patient_ids.append(patient_id)
        # Next link
        url = next(
            (l["url"] for l in bundle.get("link", []) if l.get("relation") == "next"),
            None,
        )
    print(f"Total patients found: {len(patient_ids)}")
    return patient_ids


def main():
    patient_ids = get_all_patient_ids(FHIR_BASE)
    id2num = {}
    num2id = {}

    for id in patient_ids:
        try:
            num = get_patient_identifier(id)
            id2num[id] = num
            num2id[num] = id
        except Exception as e:
            print(f"Failed for {id}: {e}")

    pprint(id2num)
    pprint(num2id)


if __name__ == "__main__":
    main()
