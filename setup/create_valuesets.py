import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple


def collect_placeholder_values(
    base_dir: Path, folders: Iterable[str], filename: str = "annotated.json"
) -> Tuple[Dict[str, Dict[str, Set[str]]], Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Collect unique values for each placeholder across multiple JSON files.
    Also build aggregated sets for drug/procedure/diagnosis placeholders and
    mappings of lab names -> lab values and vital names -> vital values.

    Returns
    -------
    (placeholder_values, lab_value_mapping, vital_value_mapping)
    """
    placeholder_values: Dict[str, Dict[str, Set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    # Aggregators for combining numbered placeholders (drug_name#, procedure_name#, diagnosis_name#)
    aggregator_base_sets: Dict[str, Set[str]] = defaultdict(set)
    # Map each lab name to the set of its observed lab values
    lab_value_mapping: Dict[str, Set[str]] = defaultdict(set)
    # Map each vital name to the set of its observed vital values
    vital_value_mapping: Dict[str, Set[str]] = defaultdict(set)

    import re

    agg_pattern = re.compile(r"^(drug_name|procedure_name|diagnosis_name)(\d*)$")

    def _normalize_to_str_list(v: Any) -> list[str]:
        """Convert a value that may be scalar/list/dict into a list[str] (skip empties)."""
        if v in (None, "", "null", "-"):
            return []
        items = v if isinstance(v, list) else [v]
        out: list[str] = []
        for it in items:
            if it in (None, "", "null", "-"):
                continue
            if isinstance(it, dict):
                out.append(json.dumps(it, sort_keys=True))
            else:
                out.append(str(it))
        return out

    for folder in folders:
        json_path = base_dir / folder / filename
        if not json_path.exists():
            print(f"Warning: {json_path} does not exist, skipping.")
            continue
        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {json_path}: {e}")
            continue

        for entry in data:
            val_dict = entry.get("val_dict")
            if not isinstance(val_dict, dict):
                continue

            # Extract the val_placeholder dictionary to facilitate lab_name/lab_value and vital_name/vital_value mapping
            val_placeholders: Dict[str, Any] = val_dict.get("val_placeholder", {})

            # -------- lab_name -> lab_value mapping (handles suffixes and lists/dicts) --------
            for pname, pvalue in list(val_placeholders.items()):
                if not pname.startswith("lab_name"):
                    continue
                suffix = pname[len("lab_name") :]
                lab_value_key = f"lab_value{suffix}"
                if lab_value_key not in val_placeholders:
                    continue

                lab_names = _normalize_to_str_list(val_placeholders[pname])
                lab_vals = _normalize_to_str_list(val_placeholders[lab_value_key])

                if not lab_names or not lab_vals:
                    continue

                for ln in lab_names:
                    lab_value_mapping[ln].update(lab_vals)

            # -------- vital_name -> vital_value mapping (mirrors lab logic) --------
            for pname, pvalue in list(val_placeholders.items()):
                if not pname.startswith("vital_name"):
                    continue
                suffix = pname[len("vital_name") :]
                vital_value_key = f"vital_value{suffix}"
                if vital_value_key not in val_placeholders:
                    continue

                vital_names = _normalize_to_str_list(val_placeholders[pname])
                vital_vals = _normalize_to_str_list(val_placeholders[vital_value_key])

                if not vital_names or not vital_vals:
                    continue

                for vn in vital_names:
                    vital_value_mapping[vn].update(vital_vals)

            # -------- generic placeholder collection + aggregation --------
            for category, placeholders in val_dict.items():
                if not isinstance(placeholders, dict):
                    continue
                for placeholder_name, value in placeholders.items():
                    values_to_add = _normalize_to_str_list(value)
                    if not values_to_add:
                        continue

                    # Add values to placeholder-specific set
                    placeholder_values[category][placeholder_name].update(values_to_add)

                    # If this is a val_placeholder matching our aggregation pattern, update aggregator set
                    if category == "val_placeholder":
                        m = agg_pattern.match(placeholder_name)
                        if m:
                            base_name = m.group(1)
                            aggregator_base_sets[base_name].update(values_to_add)

    # After processing all files, merge aggregated sets into placeholder_values
    if aggregator_base_sets:
        for base_name, merged_values in aggregator_base_sets.items():
            if merged_values:
                placeholder_values["val_placeholder"][base_name] = merged_values

    return placeholder_values, lab_value_mapping, vital_value_mapping


def create_individual_valuesets(data: Dict[str, Any]) -> None:
    """
    Create individual valueset JSON files from the collected data.
    """
    valuesets_dir = Path("fhirpath_gen/valuesets")
    valuesets_dir.mkdir(parents=True, exist_ok=True)

    # Mapping of placeholder names to valueset filenames
    placeholder_to_valueset = {
        "drug_name": "drug_name.json",
        "procedure_name": "procedure_name.json",
        "diagnosis_name": "diagnosis_name.json",
        "lab_name": "lab_name.json",
        "vital_name": "vital_name.json",
        "input_name": "input_name.json",
        "output_name": "output_name.json",
        "spec_name": "spec_name.json",
        "abbreviation": "abbreviation.json",
        "admission_route": "admission_route.json",
        "careunit": "careunit.json",
        "drug_route": "drug_route.json",
        "gender": "gender.json",
        "patient_id": "patient_id.json",
    }

    # Extract val_placeholder data
    val_placeholder = data.get("val_placeholder", {})

    # Create individual valueset files
    for placeholder_name, filename in placeholder_to_valueset.items():
        if placeholder_name in val_placeholder:
            values = val_placeholder[placeholder_name]
            if isinstance(values, list):
                # Sort the values to ensure consistent output
                sorted_values = sorted(values)
            else:
                sorted_values = (
                    sorted(list(values)) if hasattr(values, "__iter__") else [values]
                )

            output_path = valuesets_dir / filename
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(sorted_values, f, indent=2, ensure_ascii=False)
            print(f"Created {output_path} with {len(sorted_values)} values")

    # Create the value_mapping directory and placeholder_values.json
    value_mapping_dir = valuesets_dir / "value_mapping"
    value_mapping_dir.mkdir(exist_ok=True)

    mapping_path = value_mapping_dir / "placeholder_values.json"
    with mapping_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Created {mapping_path}")


def main(args: Iterable[str]) -> None:
    # Check if we should use existing placeholder_values_simple.json or collect from annotated files
    use_existing = len(args) > 0 and args[0] == "--use-existing"

    if use_existing:
        # Use existing placeholder_values_simple.json file
        existing_file = Path("placeholder_values_simple.json")
        if not existing_file.exists():
            print(
                f"Error: {existing_file} does not exist. Please run without --use-existing to collect from annotated files."
            )
            return

        print(f"Loading existing data from {existing_file}...")
        with existing_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract placeholder values from the existing data structure
        placeholder_values = data.get("val_placeholder", {})
        lab_value_mapping = data.get("lab_value_mapping", {})
        vital_value_mapping = data.get("vital_value_mapping", {})

        # Convert to the expected format
        output = {
            "val_placeholder": placeholder_values,
            "lab_value_mapping": lab_value_mapping,
            "vital_value_mapping": vital_value_mapping,
        }
    else:
        # Determine the base directory: either passed on CLI or default to script location
        if args:
            base_dir = Path(args[0]).expanduser().resolve()
        else:
            base_dir = Path(__file__).parent
        folders = ["test", "train", "valid"]
        filename = "annotated.json"
        print(f"Collecting placeholder values from {base_dir}...")
        placeholder_values, lab_value_mapping, vital_value_mapping = (
            collect_placeholder_values(base_dir, folders, filename)
        )

        # Convert sets to sorted lists for JSON serialisation
        output: Dict[str, Any] = {}
        for category, placeholders in placeholder_values.items():
            output[category] = {
                placeholder: sorted(values)
                for placeholder, values in placeholders.items()
            }

        # Add lab and vital value mappings as separate top-level keys
        output["lab_value_mapping"] = {
            lab_name: sorted(values) for lab_name, values in lab_value_mapping.items()
        }
        output["vital_value_mapping"] = {
            vital_name: sorted(values)
            for vital_name, values in vital_value_mapping.items()
        }

    # Write the main placeholder_values.json file
    output_path = Path.cwd() / "placeholder_values.json"
    with output_path.open("w", encoding="utf-8") as out_f:
        json.dump(output, out_f, indent=2, ensure_ascii=False)
    print(f"Finished. Results written to {output_path}")

    # Create individual valueset files
    create_individual_valuesets(output)


if __name__ == "__main__":
    main(sys.argv[1:])
