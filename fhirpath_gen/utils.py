import re
from datetime import datetime, timezone
import calendar
import os
import sys
from datetime import datetime
import subprocess
from pathlib import Path
from typing import Any, Iterable, List, Union
import json
from fhirpath_gen.valuesets import get_valueset

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config import PATIENT_BUNDLES_DIR, FHIRPATH_EXE

    BUNDLES_DIR = str(PATIENT_BUNDLES_DIR)
except ImportError:
    BUNDLES_DIR = "patient_bundles"  # fallback
    FHIRPATH_EXE = r"C:\Users\micha\Downloads\octofhir-fhirpath.exe"  # fallback


def fill_slots(template: str, values: dict) -> str:
    """
    Replace [key] placeholders in template with matching values from dictionary.
    If key not in dictionary, leave placeholder unchanged.
    """

    def replacer(match):
        key = match.group(1)
        return values.get(key, match.group(0))  # Keep original if not in dict

    return re.sub(r"\[([^\]]+)\]", replacer, template)


TIME_PATHS = {
    "Observation": "effectiveDateTime.toDateTime()",  # could be "issued" instead
    "MedicationAdministration": "select((effectiveDateTime | effectivePeriod.start).sort().first().toDateTime())",
    "MedicationRequest": "authoredOn.toDateTime()",
    "Procedure": "select((performedDateTime | performedPeriod.start).sort().first().toDateTime())",
    "Encounter": "select((period.start | period.end).sort().first().toDateTime())",
    "Condition": "encounter.resolve().period.start.toDateTime()",  # or "period.end"
}

ENC_PATH = {
    # Most clinical events reference an Encounter
    "Observation": "encounter.resolve()",
    "MedicationAdministration": "encounter.resolve()",
    "MedicationRequest": "encounter.resolve()",
    "Procedure": "encounter.resolve()",
    "Condition": "encounter.resolve()",  # may be absent in some datasets
    "DiagnosticReport": "encounter.resolve()",
    "ImagingStudy": "encounter.resolve()",
    "Encounter": "this",  # identity
}


def last_day_of_month(dt: datetime) -> int:
    return calendar.monthrange(dt.year, dt.month)[1]


def _ensure_tzaware(dt: datetime, default_tz=timezone.utc) -> datetime:
    """Make dt timezone-aware if it isn't."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=default_tz)


def format_date(
    dt: datetime,
    granularity: str = "day",  # "year" | "month" | "day" | "exact"
    *,
    end_of_period: bool = False,
    fmt: str = "iso",  # "nl" or "iso"
    use_z_for_utc: bool = True,  # convert +00:00 -> Z in ISO time output
    default_tz=timezone.utc,  # used if dt is naive
) -> str:
    """
    Format datetime into NL or ISO strings.

    - year  -> NL: YYYY                 | ISO: YYYY-01-01 (or YYYY-12-31 if end_of_period)
    - month -> NL: MM/YYYY              | ISO: YYYY-MM-01 (or YYYY-MM-31 -- end ofif end_of_period=True)
    - day   -> NL: DD/MM/YYYY           | ISO: YYYY-MM-DD
    - time  -> NL: YYYY-MM-DD HH:MM:SS  | ISO: YYYY-MM-DDTHH:MM:SS.mmm±HH:MM (Z if UTC)
    """
    if granularity == "year":
        nl = dt.strftime("%Y")
        if end_of_period:
            base_dt = dt.replace(month=12, day=31)
        else:
            base_dt = dt.replace(month=1, day=1)

    elif granularity == "month":
        nl = dt.strftime("%m/%Y")
        if end_of_period:
            last = last_day_of_month(dt)
            base_dt = dt.replace(day=last)
        else:
            base_dt = dt.replace(day=1)

    elif granularity == "day":
        nl = dt.strftime("%d/%m/%Y")
        base_dt = dt      
    
    elif granularity == "exact":
        # Natural language: full timestamp without 'T'
        nl = dt.strftime("%Y-%m-%d %H:%M:%S")
        base_dt = dt
          
    else:
        raise ValueError(f"Unsupported granularity: {granularity}")

    # ISO: milliseconds + timezone with colon; ensure tz-aware
    dt_aware = _ensure_tzaware(base_dt, default_tz=default_tz)
    iso = dt_aware.isoformat(
        timespec="milliseconds"
    )  # e.g., 2020-02-12T15:30:45.123+00:00

    # Optionally convert +00:00 to Z for UTC
    if use_z_for_utc and iso.endswith("+00:00"):
        iso = iso[:-6] + "Z"

    if fmt == "nl":
        return nl
    if fmt == "iso":
        return iso
    
    raise ValueError(f"Unsupported fmt: {fmt} (choose 'nl' or 'iso')")


def rust_evaluate_query(
    bundle_dir: str,
    id: str,
    query: str,
    template_info: dict = None,
    print_result: bool = False,
):
    """
    Execute a FHIRPath query using the Rust FHIRPath evaluator.

    Args:
        bundle_dir: Directory containing patient bundle files
        id: Patient ID (hash)
        query: FHIRPath query to execute
        template_info: Optional dict with template debugging info containing:
            - template_id: Short template identifier
            - template_sentence: Human-readable template description
            - placeholders: Dict of placeholder values used

    Returns:
        Query result as string, or raises exception with detailed error info
    """
    filepath = os.path.join(bundle_dir, id + ".json")
    
    # Check if bundle file exists
    if not os.path.exists(filepath):
        error_msg = f"Patient bundle file not found: {filepath}"
        if template_info:
            _print_debug_error(error_msg, query, template_info)
        raise FileNotFoundError(error_msg)

    result = subprocess.run(
        [
            FHIRPATH_EXE,
            "evaluate",
            query,
            "--input",
            filepath,
            "--output-format",
            "raw",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if print_result:
        print(result)

    # Handle errors with detailed debugging information
    if result.returncode != 0:
        error_msg = f"FHIRPath query failed with return code {result.returncode}"
        stderr_output = result.stderr.strip() if result.stderr else "No stderr output"
        stdout_output = result.stdout.strip() if result.stdout else "No stdout output"

        if template_info:
            _print_debug_error(
                error_msg, query, template_info, stderr_output, stdout_output
            )

        # Create a comprehensive error message
        full_error = f"{error_msg}\nQuery: {query}\nStderr: {stderr_output}\nStdout: {stdout_output}"
        if template_info:
            full_error += f"\nTemplate: {template_info.get('template_id', 'Unknown')}"
            full_error += (
                f"\nDescription: {template_info.get('template_sentence', 'Unknown')}"
            )

        raise RuntimeError(full_error)

    # Handle case where stdout might be None (shouldn't happen with proper encoding, but be safe)
    if result.stdout is None:
        return ""

    return (
        result.stdout.removesuffix("\n")
        if result.stdout.endswith("\n")
        else result.stdout
    )


def _print_debug_error(
    error_msg: str,
    query: str,
    template_info: dict,
    stderr_output: str = None,
    stdout_output: str = None,
):
    """
    Print detailed debugging information for failed queries.

    Args:
        error_msg: Main error message
        query: The FHIRPath query that failed
        template_info: Template debugging information
        stderr_output: Error output from the subprocess
        stdout_output: Standard output from the subprocess
    """
    print("\n" + "=" * 80)
    print("🚨 FHIRPath QUERY ERROR")
    print("=" * 80)

    print(f"❌ Error: {error_msg}")
    print()

    print("📝 Query:")
    print(f"   {query}")
    print()

    if template_info:
        print("📋 Template Information:")
        print(f"   ID: {template_info.get('template_id', 'Unknown')}")
        print(f"   Description: {template_info.get('template_sentence', 'Unknown')}")
        print()

        placeholders = template_info.get("placeholders", {})
        if placeholders:
            print("🔧 Placeholders Used:")
            for key, value in placeholders.items():
                if hasattr(value, "value"):
                    print(f"   {key}: {value.value}")
                else:
                    print(f"   {key}: {value}")
            print()

    if stderr_output and stderr_output != "No stderr output":
        print("💥 Stderr Output:")
        print(f"   {stderr_output}")
        print()

    if stdout_output and stdout_output != "No stdout output":
        print("📄 Stdout Output:")
        print(f"   {stdout_output}")
        print()

    print("=" * 80)
    print()


def rust_analyze_query(query: str):
    result = subprocess.run(
        [FHIRPATH_EXE, "validate", query],
        capture_output=True,
        text=True,
    )
    return result.stderr


def rust_validate_query_with_data(bundle_dir: str, id: str, query: str):
    filepath = os.path.join(bundle_dir, id + ".json")
    result = subprocess.run(
        [FHIRPATH_EXE, "evaluate", query, "--input", filepath],
        capture_output=True,
        text=True,
    )
    return result.stderr


ID2NUM = {
    "0a8eebfd-a352-522e-89f0-1d4a13abdebc": "10000032",
    "0c2243d2-987b-5cbd-8eb1-170a80647693": "10005866",
    "13df78e7-150e-5eb7-be5f-5f62b2baee87": "10022880",
    "158f3a39-e3d7-5e7a-93aa-57af894aadd9": "10005909",
    "1ab119a5-aac8-5002-9d2f-b8ff69623387": "10038933",
    "1bb918ba-e04e-5e7a-87ca-dbcbbb4c72c3": "10032725",
    "1cf9e585-806c-513b-80af-4ca565a28231": "10015860",
    "22a3e422-663a-561c-b305-a0c04bf42235": "10021666",
    "23069939-0c4c-517b-a3ec-baae0d4e3988": "10013049",
    "23f959c1-6ac2-562b-9cbe-c111f338e27b": "10019777",
    "24450f28-a039-57d8-95c9-d7ba5508ecd4": "10010867",
    "27980ad8-77b7-5360-b211-bf4fac9c468c": "10020306",
    "28776290-4349-56d3-8c13-adc554feabb8": "10025463",
    "28dcf33b-0c52-587f-83ad-2a3270976719": "10007795",
    "2955c958-192a-50eb-b59d-23a29d7d374e": "10016742",
    "2edf1f64-2919-50e3-b98c-7a55dcfda00d": "10009035",
    "3886cafb-65f4-5789-9213-64678a202f82": "10005348",
    "3bbb6aec-41a3-5825-b6cf-422832002f96": "10031757",
    "42f0ed8f-d744-5edb-a05d-8e011c1fbd64": "10029484",
    "4365e125-c049-525a-9459-16d5e6947ad2": "10021487",
    "4c48ec6f-716c-5bfd-8cee-b9a6b7c6c765": "10004422",
    "4c9069e4-486b-53a6-8a49-b8520d49ef7e": "10001725",
    "4f773083-7f4d-5378-b839-c24ca1e15434": "10035631",
    "51d2190c-cc46-56c5-b2ea-363895cbea75": "10009628",
    "52462b6a-9b39-5460-9ee6-1a2d7a20394e": "10022041",
    "53b0f2d8-24dc-5c82-903c-1bf98e510e96": "10006580",
    "568cb149-804c-59e8-bdf5-816e8151cd22": "10004235",
    "5d0fc1da-e9bb-5b52-8e17-5930295afd2c": "10017492",
    "5ddeb201-5de6-5177-a116-fa82ce8ad2f2": "10008287",
    "5f3dcdb5-bd27-58f5-b990-859b6bcc2d73": "10038999",
    "5f74c4bf-681e-5123-ab4d-225c72be4f9f": "10015272",
    "63bce7d4-9224-5d5d-ab3c-2967424deb0d": "10022281",
    "71a27b6b-5e41-509f-83a8-8f47e8fb8d78": "10018328",
    "72d56b49-a7ee-5b9a-a679-25d1c836d3c3": "10018845",
    "735c5ea5-a995-5613-9c30-5421bcc2cf25": "10009049",
    "73eac996-32e6-5b25-96fb-7d7414180af9": "10027445",
    "73fb53d8-f1fa-53cd-a25c-2314caccbb99": "10007818",
    "740b7686-fa6d-5574-9779-f17ed7661cbe": "10031404",
    "74a2fd87-885b-5eca-9f8b-9141915dba51": "10007928",
    "76202c51-1b9d-5cc2-a7bc-3dfb2ac3ab32": "10019172",
    "77e10fd0-6a1c-5547-a130-fae1341acf36": "10003400",
    "7d61fb4e-dc5e-5b1b-a7a6-1d96a3818546": "10024043",
    "7ec7078a-0593-5a99-9862-ebbff47fd1c5": "10029291",
    "807d2a03-9c57-55e3-a443-09fc8f1de866": "10014078",
    "8326334a-d5e4-5339-8c54-8463f95786a7": "10012552",
    "837b0984-f3bf-5076-baf5-b727decb4bea": "10037975",
    "842680b3-e421-58cc-8050-3b29668b438c": "10037861",
    "8659a6be-db5c-5f66-b629-1a3b858a487a": "10004720",
    "86bce885-4646-59f1-8f95-d92545376ce6": "10023771",
    "87dd177c-b3f5-584e-bf76-86e2ee047c1f": "10002430",
    "88fcbf73-7d80-52ae-8f11-ee73c71df69b": "10019568",
    "8adbf3e4-47ff-561e-b1b6-746ee32e056d": "10020740",
    "8c3ba37b-ba80-576a-8028-5a58eccb6156": "10016810",
    "8d7b633e-0f92-5448-a56d-36c69210e860": "10004733",
    "9111ccb1-fc93-5599-ab7d-35f1e61d4214": "10026255",
    "91e0e410-0782-5478-90e0-1bedc3aa1525": "10038081",
    "91f25704-6153-5259-bdd7-2ca6478de14a": "10019003",
    "94abdf17-f13a-5eae-aac0-eca407bbfadd": "10007058",
    "95fa0da2-f5a6-5fc9-adcf-f66e05a8cf99": "10004113",
    "9c3ebb7e-d087-519e-bea4-31c3d4aac7ff": "10023117",
    "a0bcbbc0-b432-5f7d-ac63-28212f20dead": "10022017",
    "a2605b15-4f1b-5839-b4ce-fb7a6bc1005f": "10005817",
    "a3a12d01-dc21-565b-89e2-da60e7fc80dc": "10003046",
    "a5d4cb17-db8d-574b-bd88-71473088fd9a": "10002930",
    "a6e7e991-6801-5425-b435-4ca6b7decfcc": "10001217",
    "a7bbf9a2-f7fe-5815-a637-fa59bd70b374": "10006053",
    "a87c1099-8c87-5548-8fc0-56972a82cebf": "10020944",
    "a977f4b6-1eb6-5639-80da-3e025744c4ac": "10018501",
    "aeda7084-be35-510e-b171-f00596aed99f": "10020187",
    "af0e5009-d87d-52a8-ac8a-676e471c41f1": "10021938",
    "afa7c67f-82b9-5f51-bd04-8b7d7c4456c0": "10016150",
    "b410dd44-7d65-56f9-974f-2751e8aa80e2": "10004457",
    "b6769365-7062-53bf-850f-eddd09ebcf05": "10010058",
    "b7b92f05-c913-5a94-9a06-7b015e838f14": "10021118",
    "bbad4581-d089-54a7-b7a0-8d986c5fb5ec": "10018423",
    "bc2a74ce-4069-5983-9423-1c175f7854d9": "10023239",
    "c0d83ad6-0b65-5fd6-b241-f50cf552232c": "10019385",
    "c3412a5f-f8b9-57d2-9c70-53e3e40c91f0": "10026354",
    "c4c29979-f2f5-56db-af5b-1715887727b8": "10011398",
    "cb70e6ae-90b1-562b-8ab0-467c65d18d5e": "10014354",
    "cd462e42-c070-5235-ae76-c37733a451be": "10020786",
    "d378a59b-aa80-5bc5-812a-7d59b26e7df4": "10036156",
    "dc332fb6-61f8-552e-8743-765d626f0a4e": "10035185",
    "dd2bf984-33c3-5874-8f68-84113327877e": "10018081",
    "dd773280-4157-5168-9481-3d29a5ff82d8": "10008454",
    "de33a447-3c7f-541d-be72-a744dadcbbac": "10026406",
    "df756e08-6ea8-5d69-b918-67911945f827": "10010471",
    "e1de99bc-3bc5-565e-9ee6-69675b9cc267": "10002428",
    "e232ee4d-3042-51c6-b730-a79eb8579d42": "10019917",
    "e2beb281-c44f-579b-8211-a3749c549e92": "10027602",
    "e5408569-9931-5afe-b62d-4175e6b44784": "10020640",
    "e635f2dd-aaec-5fef-a100-b9dfb523cbb6": "10038992",
    "e7e213ac-81c0-5c7f-8d57-81519132353e": "10021312",
    "ece255e8-656b-5e09-8da9-33f88bc270a1": "10012438",
    "f3fc719c-f6e0-5c27-a18f-b4e5afaf279b": "10014729",
    "f572075b-186b-5565-b2d4-1567fe4f925c": "10025612",
    "f5a99b42-365c-5f7e-bcab-4fa33b3cc88e": "10015931",
    "f5efdf3f-5b53-5c9f-95a6-047275107c46": "10002495",
    "f77a5b72-65fd-5b20-8cef-6b6be4791265": "10012853",
    "fa5fbf9c-23e3-5ef3-9cfb-24d20a950314": "10037928",
    "8e77dd0b-932d-5790-9ba6-5c6df8434457": "10039708",
    "752d15e2-bd27-52ed-b055-ed79edb86aba": "10039831",
    "b9a9ae7b-2455-59fe-938d-ce19ef360dd1": "10039997",
    "adde1635-3110-5e92-b9f0-7a6d845a1784": "10040025",
}

NUM2ID = {
    "10000032": "0a8eebfd-a352-522e-89f0-1d4a13abdebc",
    "10001217": "a6e7e991-6801-5425-b435-4ca6b7decfcc",
    "10001725": "4c9069e4-486b-53a6-8a49-b8520d49ef7e",
    "10002428": "e1de99bc-3bc5-565e-9ee6-69675b9cc267",
    "10002430": "87dd177c-b3f5-584e-bf76-86e2ee047c1f",
    "10002495": "f5efdf3f-5b53-5c9f-95a6-047275107c46",
    "10002930": "a5d4cb17-db8d-574b-bd88-71473088fd9a",
    "10003046": "a3a12d01-dc21-565b-89e2-da60e7fc80dc",
    "10003400": "77e10fd0-6a1c-5547-a130-fae1341acf36",
    "10004113": "95fa0da2-f5a6-5fc9-adcf-f66e05a8cf99",
    "10004235": "568cb149-804c-59e8-bdf5-816e8151cd22",
    "10004422": "4c48ec6f-716c-5bfd-8cee-b9a6b7c6c765",
    "10004457": "b410dd44-7d65-56f9-974f-2751e8aa80e2",
    "10004720": "8659a6be-db5c-5f66-b629-1a3b858a487a",
    "10004733": "8d7b633e-0f92-5448-a56d-36c69210e860",
    "10005348": "3886cafb-65f4-5789-9213-64678a202f82",
    "10005817": "a2605b15-4f1b-5839-b4ce-fb7a6bc1005f",
    "10005866": "0c2243d2-987b-5cbd-8eb1-170a80647693",
    "10005909": "158f3a39-e3d7-5e7a-93aa-57af894aadd9",
    "10006053": "a7bbf9a2-f7fe-5815-a637-fa59bd70b374",
    "10006580": "53b0f2d8-24dc-5c82-903c-1bf98e510e96",
    "10007058": "94abdf17-f13a-5eae-aac0-eca407bbfadd",
    "10007795": "28dcf33b-0c52-587f-83ad-2a3270976719",
    "10007818": "73fb53d8-f1fa-53cd-a25c-2314caccbb99",
    "10007928": "74a2fd87-885b-5eca-9f8b-9141915dba51",
    "10008287": "5ddeb201-5de6-5177-a116-fa82ce8ad2f2",
    "10008454": "dd773280-4157-5168-9481-3d29a5ff82d8",
    "10009035": "2edf1f64-2919-50e3-b98c-7a55dcfda00d",
    "10009049": "735c5ea5-a995-5613-9c30-5421bcc2cf25",
    "10009628": "51d2190c-cc46-56c5-b2ea-363895cbea75",
    "10010058": "b6769365-7062-53bf-850f-eddd09ebcf05",
    "10010471": "df756e08-6ea8-5d69-b918-67911945f827",
    "10010867": "24450f28-a039-57d8-95c9-d7ba5508ecd4",
    "10011398": "c4c29979-f2f5-56db-af5b-1715887727b8",
    "10012438": "ece255e8-656b-5e09-8da9-33f88bc270a1",
    "10012552": "8326334a-d5e4-5339-8c54-8463f95786a7",
    "10012853": "f77a5b72-65fd-5b20-8cef-6b6be4791265",
    "10013049": "23069939-0c4c-517b-a3ec-baae0d4e3988",
    "10014078": "807d2a03-9c57-55e3-a443-09fc8f1de866",
    "10014354": "cb70e6ae-90b1-562b-8ab0-467c65d18d5e",
    "10014729": "f3fc719c-f6e0-5c27-a18f-b4e5afaf279b",
    "10015272": "5f74c4bf-681e-5123-ab4d-225c72be4f9f",
    "10015860": "1cf9e585-806c-513b-80af-4ca565a28231",
    "10015931": "f5a99b42-365c-5f7e-bcab-4fa33b3cc88e",
    "10016150": "afa7c67f-82b9-5f51-bd04-8b7d7c4456c0",
    "10016742": "2955c958-192a-50eb-b59d-23a29d7d374e",
    "10016810": "8c3ba37b-ba80-576a-8028-5a58eccb6156",
    "10017492": "5d0fc1da-e9bb-5b52-8e17-5930295afd2c",
    "10018081": "dd2bf984-33c3-5874-8f68-84113327877e",
    "10018328": "71a27b6b-5e41-509f-83a8-8f47e8fb8d78",
    "10018423": "bbad4581-d089-54a7-b7a0-8d986c5fb5ec",
    "10018501": "a977f4b6-1eb6-5639-80da-3e025744c4ac",
    "10018845": "72d56b49-a7ee-5b9a-a679-25d1c836d3c3",
    "10019003": "91f25704-6153-5259-bdd7-2ca6478de14a",
    "10019172": "76202c51-1b9d-5cc2-a7bc-3dfb2ac3ab32",
    "10019385": "c0d83ad6-0b65-5fd6-b241-f50cf552232c",
    "10019568": "88fcbf73-7d80-52ae-8f11-ee73c71df69b",
    "10019777": "23f959c1-6ac2-562b-9cbe-c111f338e27b",
    "10019917": "e232ee4d-3042-51c6-b730-a79eb8579d42",
    "10020187": "aeda7084-be35-510e-b171-f00596aed99f",
    "10020306": "27980ad8-77b7-5360-b211-bf4fac9c468c",
    "10020640": "e5408569-9931-5afe-b62d-4175e6b44784",
    "10020740": "8adbf3e4-47ff-561e-b1b6-746ee32e056d",
    "10020786": "cd462e42-c070-5235-ae76-c37733a451be",
    "10020944": "a87c1099-8c87-5548-8fc0-56972a82cebf",
    "10021118": "b7b92f05-c913-5a94-9a06-7b015e838f14",
    "10021312": "e7e213ac-81c0-5c7f-8d57-81519132353e",
    "10021487": "4365e125-c049-525a-9459-16d5e6947ad2",
    "10021666": "22a3e422-663a-561c-b305-a0c04bf42235",
    "10021938": "af0e5009-d87d-52a8-ac8a-676e471c41f1",
    "10022017": "a0bcbbc0-b432-5f7d-ac63-28212f20dead",
    "10022041": "52462b6a-9b39-5460-9ee6-1a2d7a20394e",
    "10022281": "63bce7d4-9224-5d5d-ab3c-2967424deb0d",
    "10022880": "13df78e7-150e-5eb7-be5f-5f62b2baee87",
    "10023117": "9c3ebb7e-d087-519e-bea4-31c3d4aac7ff",
    "10023239": "bc2a74ce-4069-5983-9423-1c175f7854d9",
    "10023771": "86bce885-4646-59f1-8f95-d92545376ce6",
    "10024043": "7d61fb4e-dc5e-5b1b-a7a6-1d96a3818546",
    "10025463": "28776290-4349-56d3-8c13-adc554feabb8",
    "10025612": "f572075b-186b-5565-b2d4-1567fe4f925c",
    "10026255": "9111ccb1-fc93-5599-ab7d-35f1e61d4214",
    "10026354": "c3412a5f-f8b9-57d2-9c70-53e3e40c91f0",
    "10026406": "de33a447-3c7f-541d-be72-a744dadcbbac",
    "10027445": "73eac996-32e6-5b25-96fb-7d7414180af9",
    "10027602": "e2beb281-c44f-579b-8211-a3749c549e92",
    "10029291": "7ec7078a-0593-5a99-9862-ebbff47fd1c5",
    "10029484": "42f0ed8f-d744-5edb-a05d-8e011c1fbd64",
    "10031404": "740b7686-fa6d-5574-9779-f17ed7661cbe",
    "10031757": "3bbb6aec-41a3-5825-b6cf-422832002f96",
    "10032725": "1bb918ba-e04e-5e7a-87ca-dbcbbb4c72c3",
    "10035185": "dc332fb6-61f8-552e-8743-765d626f0a4e",
    "10035631": "4f773083-7f4d-5378-b839-c24ca1e15434",
    "10036156": "d378a59b-aa80-5bc5-812a-7d59b26e7df4",
    "10037861": "842680b3-e421-58cc-8050-3b29668b438c",
    "10037928": "fa5fbf9c-23e3-5ef3-9cfb-24d20a950314",
    "10037975": "837b0984-f3bf-5076-baf5-b727decb4bea",
    "10038081": "91e0e410-0782-5478-90e0-1bedc3aa1525",
    "10038933": "1ab119a5-aac8-5002-9d2f-b8ff69623387",
    "10038992": "e635f2dd-aaec-5fef-a100-b9dfb523cbb6",
    "10038999": "5f3dcdb5-bd27-58f5-b990-859b6bcc2d73",
    "10039708": "8e77dd0b-932d-5790-9ba6-5c6df8434457",
    "10039831": "752d15e2-bd27-52ed-b055-ed79edb86aba",
    "10039997": "b9a9ae7b-2455-59fe-938d-ce19ef360dd1",
    "10040025": "adde1635-3110-5e92-b9f0-7a6d845a1784",
}


ISO_DT_RE = re.compile(
    r"\b"  # word boundary
    r"(\d{4}-\d{2}-\d{2}T"  # YYYY-MM-DDT
    r"\d{2}:\d{2}:\d{2}"  # HH:MM:SS
    r"(?:\.\d{1,6})?"  # optional .ffffff
    r"(?:Z|[+-]\d{2}:\d{2}))"  # Z or ±HH:MM
    r"\b"
)


def _iter_values(node: Any) -> Iterable[Any]:
    """Yield every value (strings included) by walking nested dicts/lists."""
    if isinstance(node, dict):
        for v in node.values():
            yield from _iter_values(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_values(v)
    else:
        yield node


def _parse_iso_dt(s: str) -> datetime:
    """Parse ISO-8601 datetimes with Z/offset; normalize Z to +00:00."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # datetime.fromisoformat supports ±HH:MM offsets
    return datetime.fromisoformat(s)


def extract_datetimes_from_bundle(
    bundle_or_path: Union[str, Path, dict, list],
) -> List[datetime]:
    """
    Load a JSON bundle (or accept an already-loaded object) and return a
    sorted unique list of timezone-aware datetimes found anywhere in it,
    excluding any that start with year 2025.
    """
    # Load if given a path / JSON string
    if isinstance(bundle_or_path, (str, Path)):
        p = Path(bundle_or_path)
        if p.exists():
            data = json.loads(Path(p).read_text(encoding="utf-8"))
        else:
            data = json.loads(str(bundle_or_path))  # treat as raw JSON string
    else:
        data = bundle_or_path

    # Find all datetime-like strings
    hits: set[str] = set()
    for v in _iter_values(data):
        if isinstance(v, str):
            for m in ISO_DT_RE.findall(v):
                # Skip metadata-style 2025 timestamps
                if m.startswith("2025-"):
                    continue
                hits.add(m)

    # Parse and sort, removing duplicates by normalized ISO string
    dts = []
    seen_norm = set()
    for s in hits:
        try:
            dt = _parse_iso_dt(s)
            # Normalize to a canonical string to ensure dedupe across variants
            norm = dt.isoformat()
            if norm not in seen_norm:
                seen_norm.add(norm)
                dts.append(dt)
        except ValueError:
            # Ignore anything that looks like a date but isn't fully valid
            continue

    dts.sort()
    return dts


def date_range_from_bundle(bundle_or_path: Union[str, Path, dict, list]):
    """Convenience: return (min_datetime, max_datetime) or (None, None) if empty."""
    dts = extract_datetimes_from_bundle(bundle_or_path)
    return (dts[0], dts[-1]) if dts else (None, None)


_PUNCT_FIXERS = [
    # Remove spaces before punctuation like .,?!:; and closing quotes
    (re.compile(r"\s+([,.;:!?])(?!\w)"), r"\1"),
    # Remove spaces before closing brackets/parens/braces
    (re.compile(r"\s+([\)\]\}])"), r"\1"),
    # Collapse multiple spaces
    (re.compile(r"[ \t]{2,}"), " "),
    # Fix stray space before possessive 's (e.g., "patient 's")
    (re.compile(r"\s+'s\b"), r"'s"),
]


def tidy_punctuation(s: str) -> str:
    out = s
    for pat, repl in _PUNCT_FIXERS:
        out = pat.sub(repl, out)
    return out.strip()
