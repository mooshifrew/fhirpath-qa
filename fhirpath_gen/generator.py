from datetime import datetime
from typing import Optional, Tuple, List, Dict
import random as _random
import json
import re
import os
from pydantic.dataclasses import dataclass
from dataclasses import field
from pydantic import ConfigDict
from .valuesets import (
    ABBREVIATION_VALUESET,
    ADMISSION_ROUTE_VALUESET,
    CAREUNIT_VALUESET,
    DIAGNOSIS_NAME_VALUESET,
    DRUG_NAME_VALUESET,
    DRUG_ROUTE_VALUESET,
    GENDER_VALUESET,
    INPUT_NAME_VALUESET,
    LAB_NAME_VALUESET,
    OUTPUT_NAME_VALUESET,
    PATIENT_ID_VALUESET,
    PROCEDURE_NAME_VALUESET,
    SPEC_NAME_VALUESET,
    VITAL_NAME_VALUESET,
)
from .utils import rust_evaluate_query, date_range_from_bundle
from .simple_placeholders.value_extraction import get_value_extraction_query

# Module-level cache for paraphrases (shared across all GenerationContext instances)
# Keyed by file path to support different paraphrase files
_paraphrases_cache: Dict[str, Optional[Dict[str, List[str]]]] = {}


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class GenerationContext:
    """
    Shared context for random data generation across placeholders and expressions within a template.

    - seed: Optional[int]      -> If provided, seeds the RNG for deterministic runs
    - rng: random.Random       -> RNG instance (seeded when seed is set)
    - now: datetime            -> "current" reference time
    - patient_id: Optional[str]
    - date_range: Optional[(date, date)]
    - use_paraphrases: bool    -> Whether to use paraphrased templates
    """

    patient_id: Optional[str] = None

    seed: Optional[int] = 42
    rng: _random.Random = field(default_factory=_random.Random, repr=False)
    now: datetime = datetime(2100, 6, 6)
    date_range: Tuple[datetime, datetime] = (datetime(2050, 1, 1), datetime(2150, 1, 1))
    use_paraphrases: bool = False

    filled: Dict[str, str] = field(
        default_factory=dict
    )  # so that vital/lab values are realistic

    paraphrase_file: Optional[str] = (
        None  # Path to paraphrase file, if using paraphrases
    )

    def __post_init__(self):
        """
        Called after Pydantic validation. Ensures the RNG is properly seeded.
        Loads paraphrases if use_paraphrases is enabled.
        """
        if self.seed is not None:
            self.rng.seed(self.seed)
        if self.use_paraphrases:
            paraphrase_file = (
                self.paraphrase_file or self._get_default_paraphrase_file()
            )
            GenerationContext.load_paraphrases(paraphrase_file)

    @staticmethod
    def _get_default_paraphrase_file() -> str:
        """Get the default paraphrase file path."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "paraphrases_clinical_validated.json")

    @classmethod
    def load_paraphrases(
        cls, paraphrase_file: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Load paraphrases from JSON file with caching.

        Args:
            paraphrase_file: Path to the paraphrase file. If None, uses default location.

        Returns:
            Dictionary mapping template IDs to lists of paraphrased template strings.
            Returns empty dict if file doesn't exist or is malformed.
        """
        global _paraphrases_cache

        # Use default file if not provided
        if paraphrase_file is None:
            paraphrase_file = cls._get_default_paraphrase_file()

        # Normalize path for caching
        paraphrase_file = os.path.abspath(paraphrase_file)

        # Check cache
        if (
            paraphrase_file not in _paraphrases_cache
            or _paraphrases_cache[paraphrase_file] is None
        ):
            try:
                if os.path.exists(paraphrase_file):
                    with open(paraphrase_file, "r", encoding="utf-8") as f:
                        paraphrases_dict = json.load(f)
                        # Validate structure - ensure all values are lists
                        if not isinstance(paraphrases_dict, dict):
                            print(
                                f"Warning: {paraphrase_file} is not a valid JSON object, using empty dict"
                            )
                            _paraphrases_cache[paraphrase_file] = {}
                        else:
                            # Validate that all values are lists
                            for template_id, paraphrases in paraphrases_dict.items():
                                if not isinstance(paraphrases, list):
                                    print(
                                        f"Warning: Template {template_id} in paraphrases file is not a list, skipping"
                                    )
                                    paraphrases_dict[template_id] = []
                            _paraphrases_cache[paraphrase_file] = paraphrases_dict
                else:
                    print(
                        f"Warning: Paraphrase file not found at {paraphrase_file}, paraphrasing disabled"
                    )
                    _paraphrases_cache[paraphrase_file] = {}
            except json.JSONDecodeError as e:
                print(
                    f"Warning: Failed to parse {paraphrase_file}: {e}, using empty dict"
                )
                _paraphrases_cache[paraphrase_file] = {}
            except Exception as e:
                print(
                    f"Warning: Error loading {paraphrase_file}: {e}, using empty dict"
                )
                _paraphrases_cache[paraphrase_file] = {}

        return _paraphrases_cache[paraphrase_file]

    def to_dict(self):
        """Convert to dictionary, excluding the rng field for JSON serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if key != "rng":  # Exclude the random.Random object
                result[key] = value
        return result

    # valueset subsetting, default to the full valuesets
    drug_names: List[str] = DRUG_NAME_VALUESET
    procedure_names: List[str] = PROCEDURE_NAME_VALUESET
    admission_routes: List[str] = ADMISSION_ROUTE_VALUESET
    care_units: List[str] = CAREUNIT_VALUESET
    diagnosis_names: List[str] = DIAGNOSIS_NAME_VALUESET
    drug_routes: List[str] = DRUG_ROUTE_VALUESET
    genders: List[str] = GENDER_VALUESET
    input_names: List[str] = INPUT_NAME_VALUESET
    lab_names: List[str] = LAB_NAME_VALUESET
    output_names: List[str] = OUTPUT_NAME_VALUESET
    spec_names: List[str] = SPEC_NAME_VALUESET
    vital_names: List[str] = VITAL_NAME_VALUESET


def parse_datetime(date_str):
    """Parse various datetime formats from FHIR resources"""
    if not date_str:
        return None

    # Remove timezone info for parsing
    date_str = re.sub(r"[+-]\d{2}:\d{2}$", "", date_str)

    # Try different datetime formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def filter_numeric_codes(values):
    """
    Filter out purely numeric codes from a list of values.

    A value is considered a code if it contains only digits and possibly
    some common separators like hyphens, underscores, or dots.

    Args:
        values: List of string values to filter

    Returns:
        List of values with numeric codes removed
    """
    if not values:
        return values

    filtered_values = []
    for value in values:
        if not value:
            continue

        # Convert to string and strip whitespace
        value_str = str(value).strip()

        # Skip empty values
        if not value_str:
            continue

        # Check if the value is purely numeric (with optional separators)
        # This regex matches strings that contain only:
        # - digits (0-9)
        # - hyphens (-)
        # - underscores (_)
        # - dots (.)
        # - forward slashes (/)
        # - spaces (for codes like "70017" or "70053")
        if re.match(r"^[\d\s\-_\.\/]+$", value_str):
            # This is likely a code, skip it
            continue
        else:
            # This contains non-numeric characters, keep it
            filtered_values.append(value_str)

    return filtered_values


def filter_against_ehrsql_valuesets(patient_values, ehrsql_valueset):
    """
    Filter patient values to only include those that are also in the EHR-SQL valueset.
    Uses case-insensitive comparison but preserves original strings.

    Args:
        patient_values: List of patient-specific values
        ehrsql_valueset: Set or list of EHR-SQL values to match against

    Returns:
        List of patient values that are also in the EHR-SQL valueset
    """
    if not patient_values or not ehrsql_valueset:
        return patient_values

    # Create a lowercase lookup set from EHR-SQL valueset
    ehrsql_lowercase = {str(val).lower().strip() for val in ehrsql_valueset}

    filtered_values = []
    for value in patient_values:
        if not value:
            continue

        value_str = str(value).strip()
        if not value_str:
            continue

        # Check if the lowercase version exists in EHR-SQL valueset
        if value_str.lower() in ehrsql_lowercase:
            filtered_values.append(value_str)

    return filtered_values


def extract_datetime_from_resource(resource):
    """Extract all datetime values from a FHIR resource"""
    datetimes = []

    def extract_from_value(value):
        if isinstance(value, dict):
            for k, v in value.items():
                extract_from_value(v)
        elif isinstance(value, list):
            for item in value:
                extract_from_value(item)
        elif isinstance(value, str):
            dt = parse_datetime(value)
            if dt:
                datetimes.append(dt)

    # Common FHIR datetime fields
    datetime_fields = [
        "effectiveDateTime",
        "effectivePeriod",
        "period",
        "authoredOn",
        "performedDateTime",
        "performedPeriod",
        "onsetDateTime",
        "onsetPeriod",
        "abatementDateTime",
        "abatementPeriod",
        "issued",
        "lastUpdated",
        "created",
        "start",
        "end",
        "date",
        "recordedDate",
    ]

    for field in datetime_fields:
        if field in resource:
            extract_from_value(resource[field])

    return datetimes


def find_latest_datetime_in_bundle(bundle_path):
    """Find the latest datetime in a single patient bundle"""
    try:
        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle = json.load(f)

        latest_dt = None

        if "entry" in bundle:
            for entry in bundle["entry"]:
                if "resource" in entry:
                    resource = entry["resource"]
                    datetimes = extract_datetime_from_resource(resource)

                    for dt in datetimes:
                        if latest_dt is None or dt > latest_dt:
                            latest_dt = dt

        return latest_dt

    except Exception as e:
        print(f"Error processing {bundle_path}: {e}")
        return None


def find_datetime_range_in_bundle(bundle_path):
    """Find the earliest and latest datetimes in a single patient bundle.

    Returns:
        tuple: (earliest_dt, latest_dt) or (None, None) if no datetimes found
    """
    try:
        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle = json.load(f)

        earliest_dt = None
        latest_dt = None

        if "entry" in bundle:
            for entry in bundle["entry"]:
                if "resource" in entry:
                    resource = entry["resource"]
                    datetimes = extract_datetime_from_resource(resource)

                    for dt in datetimes:
                        if earliest_dt is None or dt < earliest_dt:
                            earliest_dt = dt
                        if latest_dt is None or dt > latest_dt:
                            latest_dt = dt

        return earliest_dt, latest_dt

    except Exception as e:
        print(f"Error processing {bundle_path}: {e}")
        return None, None


def create_patient_specific_context(
    patient_id: str,
    bundle_dir: str = "patient_bundles",
    seed: Optional[int] = 42,
    filter_against_ehrsql: bool = False,
    use_paraphrases: bool = False,
    paraphrase_file: Optional[str] = None,
) -> GenerationContext:
    """
    Create a GenerationContext specific to a patient by querying their bundle for all placeholder values.

    Args:
        patient_id: The patient ID to create context for (can be numeric or hash)
        bundle_dir: Directory containing patient bundle files
        seed: Optional seed for the random number generator
        filter_against_ehrsql: If True, filter patient values to only include those
                              that are also in the original EHR-SQL valuesets
        use_paraphrases: If True, enable paraphrasing for template selection
        paraphrase_file: Path to the paraphrase file to use (if None, uses default)

    Returns:
        GenerationContext with patient-specific valuesets and current datetime
    """

    # Import here to avoid circular imports
    from .utils import ID2NUM, NUM2ID

    # Convert to hash ID if needed
    if patient_id in NUM2ID:
        patient_id_hash = NUM2ID[patient_id]
    elif patient_id in ID2NUM:
        patient_id_hash = patient_id
    else:
        # If neither, assume it's already a hash and use as-is
        patient_id_hash = patient_id

    # Check if the patient bundle file exists
    # Convert bundle_dir to string if it's a Path object
    bundle_dir_str = str(bundle_dir)
    bundle_path = os.path.join(bundle_dir_str, f"{patient_id_hash}.json")

    if not os.path.exists(bundle_path):
        raise FileNotFoundError(
            f"Patient bundle file not found: {bundle_path}\n"
            f"Patient ID: {patient_id}\n"
            f"Hash ID: {patient_id_hash}\n"
            f"Please ensure the patient bundle exists in the {bundle_dir} directory."
        )

    # Find the datetime range in the patient bundle (earliest to latest)
    earliest_datetime, latest_datetime = find_datetime_range_in_bundle(bundle_path)

    if latest_datetime is None:
        # Fallback to default datetime if none found
        current_datetime = datetime(2100, 6, 6)
        date_range = (datetime(2050, 1, 1), datetime(2150, 1, 1))
        print(
            f"Warning: No datetime found in bundle for patient {patient_id}, using default"
        )
    else:
        current_datetime = latest_datetime
        # Use earliest datetime as start, latest as end
        # If no earliest found (shouldn't happen if latest exists), use latest as both
        if earliest_datetime is None:
            earliest_datetime = latest_datetime
        date_range = (earliest_datetime, latest_datetime)

    # Define placeholder names to query (excluding *_value types as requested)
    placeholder_names = [
        "drug_name",
        "procedure_name",
        "admission_route",
        "careunit",
        "diagnosis_name",
        "drug_route",
        "gender",
        "input_name",
        "lab_name",
        "output_name",
        "spec_name",
        "vital_name",
    ]

    # Initialize valuesets with empty lists
    patient_valuesets = {
        "drug_names": [],
        "procedure_names": [],
        "admission_routes": [],
        "care_units": [],
        "diagnosis_names": [],
        "drug_routes": [],
        "genders": [],
        "input_names": [],
        "lab_names": [],
        "output_names": [],
        "spec_names": [],
        "vital_names": [],
    }

    # Map placeholder names to valueset keys
    placeholder_to_valueset = {
        "drug_name": "drug_names",
        "procedure_name": "procedure_names",
        "admission_route": "admission_routes",
        "careunit": "care_units",
        "diagnosis_name": "diagnosis_names",
        "drug_route": "drug_routes",
        "gender": "genders",
        "input_name": "input_names",
        "lab_name": "lab_names",
        "output_name": "output_names",
        "spec_name": "spec_names",
        "vital_name": "vital_names",
    }

    # Query each placeholder type and collect unique values
    for placeholder_name in placeholder_names:
        try:
            # Get all possible queries for this placeholder
            queries = get_value_extraction_query(placeholder_name)

            if isinstance(queries, dict):
                # Handle multiple resource types
                for resource_type, query in queries.items():
                    if query:  # Skip empty queries
                        result = rust_evaluate_query(bundle_dir, patient_id_hash, query)
                        if result and result.strip():
                            # Parse the result (assuming it's a JSON array of values)
                            try:
                                values = json.loads(result)
                                if isinstance(values, list):
                                    valueset_key = placeholder_to_valueset[
                                        placeholder_name
                                    ]
                                    patient_valuesets[valueset_key].extend(values)
                            except json.JSONDecodeError:
                                # If not JSON, treat as single value or comma-separated
                                if "," in result:
                                    values = [
                                        v.strip().strip('"') for v in result.split(",")
                                    ]
                                else:
                                    values = [result.strip().strip('"')]
                                valueset_key = placeholder_to_valueset[placeholder_name]
                                patient_valuesets[valueset_key].extend(values)
            elif isinstance(queries, str) and queries:
                # Handle single query
                result = rust_evaluate_query(bundle_dir, patient_id_hash, queries)
                if result and result.strip():
                    try:
                        values = json.loads(result)
                        if isinstance(values, list):
                            valueset_key = placeholder_to_valueset[placeholder_name]
                            patient_valuesets[valueset_key].extend(values)
                    except json.JSONDecodeError:
                        if "," in result:
                            values = [v.strip().strip('"') for v in result.split(",")]
                        else:
                            values = [result.strip().strip('"')]
                        valueset_key = placeholder_to_valueset[placeholder_name]
                        patient_valuesets[valueset_key].extend(values)

        except Exception as e:
            print(
                f"Warning: Error querying {placeholder_name} for patient {patient_id}: {e}"
            )
            continue

    # Remove duplicates and empty values from each valueset
    for key in patient_valuesets:
        patient_valuesets[key] = list(set(filter(None, patient_valuesets[key])))

    # Filter out purely numeric codes from each valueset
    for key in patient_valuesets:
        patient_valuesets[key] = filter_numeric_codes(patient_valuesets[key])

    # Optionally filter against EHR-SQL valuesets
    if filter_against_ehrsql:
        # Valuesets are already imported at the top of the file

        # Map patient valueset keys to EHR-SQL valuesets
        ehrsql_mapping = {
            "drug_names": DRUG_NAME_VALUESET,
            "procedure_names": PROCEDURE_NAME_VALUESET,
            "admission_routes": ADMISSION_ROUTE_VALUESET,
            "care_units": CAREUNIT_VALUESET,
            "diagnosis_names": DIAGNOSIS_NAME_VALUESET,
            "drug_routes": DRUG_ROUTE_VALUESET,
            "genders": GENDER_VALUESET,
            "input_names": INPUT_NAME_VALUESET,
            "lab_names": LAB_NAME_VALUESET,
            "output_names": OUTPUT_NAME_VALUESET,
            "spec_names": SPEC_NAME_VALUESET,
            "vital_names": VITAL_NAME_VALUESET,
        }

        # Apply EHR-SQL filtering to each valueset
        for key, ehrsql_valueset in ehrsql_mapping.items():
            if key in patient_valuesets:
                patient_valuesets[key] = filter_against_ehrsql_valuesets(
                    patient_valuesets[key], ehrsql_valueset
                )

    # Create the GenerationContext with patient-specific data
    context = GenerationContext(
        patient_id=patient_id,
        seed=seed,
        now=current_datetime,
        date_range=date_range,
        use_paraphrases=use_paraphrases,
        paraphrase_file=paraphrase_file,
        drug_names=patient_valuesets["drug_names"] or DRUG_NAME_VALUESET,
        procedure_names=patient_valuesets["procedure_names"] or PROCEDURE_NAME_VALUESET,
        admission_routes=patient_valuesets["admission_routes"]
        or ADMISSION_ROUTE_VALUESET,
        care_units=patient_valuesets["care_units"] or CAREUNIT_VALUESET,
        diagnosis_names=patient_valuesets["diagnosis_names"] or DIAGNOSIS_NAME_VALUESET,
        drug_routes=patient_valuesets["drug_routes"] or DRUG_ROUTE_VALUESET,
        genders=patient_valuesets["genders"] or GENDER_VALUESET,
        input_names=patient_valuesets["input_names"] or INPUT_NAME_VALUESET,
        lab_names=patient_valuesets["lab_names"] or LAB_NAME_VALUESET,
        output_names=patient_valuesets["output_names"] or OUTPUT_NAME_VALUESET,
        spec_names=patient_valuesets["spec_names"] or SPEC_NAME_VALUESET,
        vital_names=patient_valuesets["vital_names"] or VITAL_NAME_VALUESET,
    )

    return context
