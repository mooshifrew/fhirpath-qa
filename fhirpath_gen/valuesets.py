from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

# TODO: import valuesets directly from a terminology system

VALUES_DIR = Path(__file__).parent / "valuesets"


def _load_one_json(path: Path) -> list[str]:
    """
    Load a single valueset JSON.
    Supports either:
      - simple list: ["Aspirin", "Ibuprofen", ...]
      - object with 'values': {"values": ["Aspirin", ...], ...metadata}
    Always returns a list of strings.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if "values" in data and isinstance(data["values"], list):
            return data["values"]

    raise ValueError(
        f"Unsupported format in {path}. "
        "Use a list of strings or an object with a 'values' list."
    )


@lru_cache(maxsize=1)
def load_all_valuesets() -> dict[str, tuple[str, ...]]:
    """
    Read all *.json under VALUES_DIR and return a mapping:
      key == file stem (e.g., 'drug_name')
      value == tuple of strings (immutable + indexable).
    """
    if not VALUES_DIR.exists():
        raise FileNotFoundError(f"Valueset directory not found: {VALUES_DIR}")

    result: dict[str, tuple[str, ...]] = {}
    for fp in sorted(VALUES_DIR.glob("*.json")):
        key = fp.stem  # e.g., "drug_name"
        values = _load_one_json(fp)
        result[key] = tuple(values)  # force immutable tuple
    return result


# Materialize and export globals: DRUG_NAME_VALUESET, PROCEDURE_NAME_VALUESET, ...
VALUESETS = load_all_valuesets()
for _k, _vals in VALUESETS.items():
    globals()[f"{_k.upper()}_VALUESET"] = _vals

# Load lab test and vital values
path = VALUES_DIR / "value_mapping" / "placeholder_values.json"
with path.open(mode="r", encoding="utf-8") as f:
    ehr_sql_values = json.load(f)


def get_valueset(name: str) -> tuple[str, ...]:
    """Fetch a valueset by its key (e.g., 'drug_name')."""
    try:
        return VALUESETS[name]
    except KeyError:
        raise KeyError(
            f"Unknown valueset {name!r}. " f"Known: {', '.join(sorted(VALUESETS))}"
        )
