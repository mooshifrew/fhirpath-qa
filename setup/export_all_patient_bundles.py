import requests
import json
import os
import sys
from time import sleep
from pathlib import Path

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import HAPI_URL, PATIENT_BUNDLES_DIR
except ImportError:
    print("Error: config.py not found. Please ensure config.py exists.")
    sys.exit(1)

FHIR_BASE = HAPI_URL
PATIENTS_PER_PAGE = 20
OUT_DIR = str(PATIENT_BUNDLES_DIR)

# You can add/remove includes here as needed.
INCLUDE_PARAMS = [
    ("_include", "Encounter:location"),
    ("_include", "Encounter:service-provider"),
    ("_include", "Encounter:participant-individual"),
    ("_revinclude", "Provenance:target"),
    ("_count", "200"),
    ("_include:iterate", "Encounter:location"),
    ("_include", "Observation:specimen"),
    ("_include", "MedicationAdministration:request"),
    ("_include:iterate", "Encounter:location"),
    ("_include:iterate", "Observation:specimen"),
]

os.makedirs(OUT_DIR, exist_ok=True)


def get_all_patient_ids(fhir_base):
    patient_ids = []
    url = f"{fhir_base}/Patient?_elements=id&_count={PATIENTS_PER_PAGE}"
    while url:
        print(f"Fetching: {url}")
        resp = requests.get(url, headers={"Accept": "application/fhir+json"})
        resp.raise_for_status()
        bundle = resp.json()
        for entry in bundle.get("entry", []):
            patient_ids.append(entry["resource"]["id"])
        url = next(
            (l["url"] for l in bundle.get("link", []) if l.get("relation") == "next"),
            None,
        )
    print(f"Total patients found: {len(patient_ids)}")
    return patient_ids


def get_full_bundle(url, extra_params=None):
    """Fetches all pages of a $everything bundle (with optional _include/_type)
    and merges entries, de-duped by resourceType/id."""
    params = list(extra_params or [])
    headers = {"Accept": "application/fhir+json"}

    all_by_key = {}
    first_bundle = None

    # First request can include extra params; subsequent pages follow their 'next' links
    resp = requests.get(url, headers=headers, params=params if params else None)
    resp.raise_for_status()
    bundle = resp.json()
    first_bundle = bundle

    def add_entries(b):
        for e in b.get("entry", []):
            r = e.get("resource")
            if not r:
                continue
            key = f"{r['resourceType']}/{r['id']}"
            all_by_key[key] = r

    add_entries(bundle)

    while True:
        nxt = next(
            (l["url"] for l in bundle.get("link", []) if l.get("relation") == "next"),
            None,
        )
        if not nxt:
            break
        bundle = requests.get(nxt, headers=headers).json()
        add_entries(bundle)

    if first_bundle is None:
        return None

    first_bundle["entry"] = [{"resource": r} for r in all_by_key.values()]
    # Optional: make it an explicit 'collection' so downstream tools don't assume it's a searchset
    first_bundle["type"] = "collection"
    return first_bundle


def main():
    patient_ids = get_all_patient_ids(FHIR_BASE)
    for idx, patient_id in enumerate(patient_ids):
        out_file = os.path.join(OUT_DIR, f"{patient_id}.json")
        if os.path.exists(out_file):
            print(f"File for {patient_id} already exists. Skipping.")
            continue

        print(
            f"({idx+1}/{len(patient_ids)}) Downloading bundle for patient {patient_id} ..."
        )
        everything_url = f"{FHIR_BASE}/Patient/{patient_id}/$everything"
        try:
            bundle = get_full_bundle(
                everything_url, extra_params=INCLUDE_PARAMS
            )  # <- NEW
            if bundle and bundle.get("entry"):
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(bundle, f, indent=2)
                print(f"  ✔ Saved to {out_file} ({len(bundle['entry'])} entries)")
            else:
                print(f"  ⚠ No bundle/entries for patient {patient_id}")
        except Exception as e:
            print(f"  ✗ Failed to fetch for {patient_id}: {e}")
        sleep(0.2)


if __name__ == "__main__":
    main()
