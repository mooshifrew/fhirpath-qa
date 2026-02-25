#!/usr/bin/env python3
"""
Script to generate random questions for each template.

Usage:
    # Single patient mode (legacy)
    python generate_questions.py <patient_id> <num_questions_per_template> <output_filename> [options]

    # Dataset mode (new)
    python generate_questions.py --dataset <patient_ids_file> <num_questions_per_template> <output_filename> [options]

Arguments:
    patient_id: The patient ID to use for generation (single patient mode)
    patient_ids_file: File containing list of patient IDs, one per line (dataset mode)
    num_questions_per_template: Number of questions to generate per template
    output_filename: Output JSON file name
    --dataset: Enable dataset mode for multiple patients
    --templates: Comma-separated list of template names to use (optional)
    --evaluate: Optional flag to also evaluate questions using octofhir-fhirpath
    --filter-ehrsql: Filter patient values to only include those in EHR-SQL valuesets
    --annotated: Include full template and placeholder information (default: False)
    --paraphrase: Use paraphrased templates when generating questions (selects from paraphrase variants deterministically)
    --split: Split to use ('train', 'val', or 'test'). Filters paraphrases based on split assignment.

Examples:
    # Single patient
    python generate_questions.py 10019917 5 questions_output.json --evaluate

    # Dataset with all templates
    python generate_questions.py --dataset patient_ids.txt 3 dataset_output.json --evaluate

    # Dataset with specific templates
    python generate_questions.py --dataset patient_ids.txt 2 dataset_output.json --templates "count-drugs-prescribed,has-diagnosis" --evaluate

    # Dataset with paraphrasing enabled
    python generate_questions.py --dataset patient_ids.txt 2 dataset_output.json --paraphrase --evaluate
"""

import argparse
import json
import hashlib
import time
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import os

# Add the fhirpath_gen module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "fhirpath_gen"))

# Import the main module to trigger registration of all components
import fhirpath_gen


from fhirpath_gen.base import template_registry
from fhirpath_gen.generator import GenerationContext, create_patient_specific_context
from fhirpath_gen.utils import (
    rust_evaluate_query,
    ID2NUM,
    NUM2ID,
)
from config import OUTPUT_DIR


def serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def generate_question_hash(data: Dict[str, Any]) -> str:
    """
    Generate a unique hash for a question based on all its data.

    Args:
        data: Dictionary containing all question data

    Returns:
        SHA-256 hash as a hex string
    """
    # Create a deterministic string representation of the data
    # Sort keys to ensure consistent ordering
    data_str = json.dumps(
        data, sort_keys=True, separators=(",", ":"), default=serialize_datetime
    )

    # Generate SHA-256 hash
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def strip_patient_context_prefix(question: str) -> str:
    """
    Strip the "Context: patient #######." prefix from a question.

    This prefix is needed for slot filling during generation, but should be
    removed from the final output since patient_id is stored separately.

    Args:
        question: Question string that may contain the context prefix

    Returns:
        Question string with the context prefix removed (if present)
    """
    # Pattern to match "Context: patient {any characters}. " at the start
    pattern = r"^Context: patient [^.]+\."
    # Remove the prefix and any trailing space
    stripped = re.sub(pattern, "", question, count=1).strip()
    return stripped


def get_patient_id_hash(patient_id: str) -> str:
    """
    Get the hash string for a patient ID.

    Args:
        patient_id: Patient ID (can be numeric or hash string)

    Returns:
        The hash string version of the patient ID
    """
    # If it's already a hash string, return it
    if patient_id in ID2NUM:
        return patient_id

    # If it's a numeric ID, convert to hash
    if patient_id in NUM2ID:
        return NUM2ID[patient_id]

    # If neither, assume it's a hash string and return as-is
    return patient_id


def create_context_with_fallback(
    patient_id: str,
    filter_against_ehrsql: bool = False,
    use_paraphrases: bool = False,
    paraphrase_file: Optional[str] = None,
):
    """
    Create a generation context, trying patient-specific first, then falling back to default.

    Args:
        patient_id: The patient ID to create context for
        filter_against_ehrsql: Whether to filter against EHR-SQL valuesets
        use_paraphrases: Whether to enable paraphrasing for template selection
        paraphrase_file: Path to the paraphrase file to use (if None, uses default)

    Returns:
        tuple: (context, context_type) where context_type is "patient_specific" or "default"
    """
    from config import PATIENT_BUNDLES_DIR

    try:
        # Try to create patient-specific context
        ctx = create_patient_specific_context(
            patient_id,
            bundle_dir=str(PATIENT_BUNDLES_DIR),
            filter_against_ehrsql=filter_against_ehrsql,
            use_paraphrases=use_paraphrases,
            paraphrase_file=paraphrase_file,
        )
        return ctx, "patient_specific"
    except FileNotFoundError:
        # Patient bundle not found, fall back to default context
        print(f"Patient bundle not found for {patient_id}, using default context")
        ctx = GenerationContext(
            patient_id=patient_id,
            use_paraphrases=use_paraphrases,
            paraphrase_file=paraphrase_file,
        )
        return ctx, "default"
    except Exception as e:
        # Other errors, still fall back to default context
        print(f"Error creating patient-specific context for {patient_id}: {e}")
        print("Falling back to default context")
        ctx = GenerationContext(
            patient_id=patient_id,
            use_paraphrases=use_paraphrases,
            paraphrase_file=paraphrase_file,
        )
        return ctx, "default"


def generate_questions_for_patient(
    patient_id: str,
    num_questions_per_template: int,
    output_filename: str,
    evaluate: bool = False,
    filter_ehrsql: bool = False,
    annotated: bool = False,
    template_names: List[str] = None,
    paraphrase: bool = False,
    paraphrase_file: Optional[str] = None,
) -> None:
    """
    Generate random questions for each template for a given patient.

    Args:
        patient_id: Patient ID to use for generation
        num_questions_per_template: Number of questions to generate per template
        output_filename: Output JSON file name
        evaluate: Whether to evaluate questions using octofhir-fhirpath
        filter_ehrsql: Whether to filter patient values against EHR-SQL valuesets
        annotated: Whether to include full template and placeholder information
        template_names: List of template names to use (None for all templates)
        paraphrase: Whether to use paraphrased templates
        paraphrase_file: Path to the paraphrase file to use (if None, uses default)
    """
    print(
        f"Generating {num_questions_per_template} questions per template for patient {patient_id}"
    )
    print(f"Evaluation enabled: {evaluate}")
    print(f"EHR-SQL filtering enabled: {filter_ehrsql}")
    print(f"Paraphrasing enabled: {paraphrase}")

    # Get patient hash
    patient_id_hash = get_patient_id_hash(patient_id)

    # Create generation context with fallback
    print("Creating generation context...")
    start_time = time.time()

    ctx, context_type = create_context_with_fallback(
        patient_id,
        filter_against_ehrsql=filter_ehrsql,
        use_paraphrases=paraphrase,
        paraphrase_file=paraphrase_file,
    )

    end_time = time.time()
    context_creation_time = end_time - start_time
    print(f"Context creation took {context_creation_time:.2f} seconds")
    print(f"Context type: {context_type}")

    # Debug: Print generation context details
    print("\n" + "=" * 60)
    print(f"GENERATION CONTEXT ({context_type.upper()}):")
    print("=" * 60)
    print(f"Patient ID: {ctx.patient_id}")
    print(f"Current datetime: {ctx.now}")
    print(f"Seed: {ctx.seed}")
    print()

    # Display patient-specific valuesets
    valuesets = {
        "Drug Names": ctx.drug_names,
        "Procedure Names": ctx.procedure_names,
        "Admission Routes": ctx.admission_routes,
        "Care Units": ctx.care_units,
        "Diagnosis Names": ctx.diagnosis_names,
        "Drug Routes": ctx.drug_routes,
        "Genders": ctx.genders,
        "Input Names": ctx.input_names,
        "Lab Names": ctx.lab_names,
        "Output Names": ctx.output_names,
        "Spec Names": ctx.spec_names,
        "Vital Names": ctx.vital_names,
    }

    for name, values in valuesets.items():
        if values:
            print(f"{name}: {len(values)} values")
            # Show first few values as examples
            if len(values) <= 3:
                print(f"  {values}")
            else:
                print(f"  {values[:3]} ... (and {len(values) - 3} more)")
        else:
            print(f"{name}: No values found")
    print("=" * 60 + "\n")

    # Get templates to use
    if template_names is None:
        template_ids = template_registry.list_templates()
        print(f"Using all {len(template_ids)} available templates")
    else:
        # Validate that all specified templates exist
        available_templates = template_registry.list_templates()
        invalid_templates = [
            name for name in template_names if name not in available_templates
        ]
        if invalid_templates:
            print(
                f"Error: The following templates are not implemented: {invalid_templates}"
            )
            print(f"Available templates: {available_templates}")
            sys.exit(1)
        template_ids = template_names
        print(f"Using {len(template_ids)} specified templates: {template_ids}")

    all_questions = []

    for template_id in template_ids:
        print(f"Processing template: {template_id}")

        try:
            # Create template instance
            template = template_registry.new_template(template_id, gen_ctx=ctx)

            for i in range(num_questions_per_template):
                # Generate a new question-answer pair
                generated = template.regenerate_qa_pair()

                # Extract placeholders
                placeholders = generated.get("placeholders", {})
                s_placeholders = placeholders.get("simple", {})
                op_placeholders = placeholders.get("operation", {})
                t_placeholders = placeholders.get("time", {})

                # Convert placeholders to serializable dictionaries
                def serialize_placeholders(placeholder_dict):
                    """Convert placeholder objects to dictionaries."""
                    if not placeholder_dict:
                        return placeholder_dict
                    result = {}
                    for key, placeholder_obj in placeholder_dict.items():
                        if hasattr(placeholder_obj, "model_dump"):
                            result[key] = placeholder_obj.model_dump()
                        else:
                            result[key] = placeholder_obj
                    return result

                # Create the question data structure
                question_data = {
                    "patient_id": patient_id,
                    "question": generated["question"],
                    "query": generated["query"],
                }

                # Add annotated information if requested
                if annotated:
                    question_data.update(
                        {
                            "patient_id_hash": patient_id_hash,
                            "question_template_id": template_id,
                            "question_template": generated["template"],
                            "s_placeholders": serialize_placeholders(s_placeholders),
                            "op_placeholders": serialize_placeholders(op_placeholders),
                            "t_placeholders": serialize_placeholders(t_placeholders),
                        }
                    )

                # Add answer if evaluation is enabled
                if evaluate:
                    try:
                        # Prepare template debugging information
                        template_info = {
                            "template_id": template_id,
                            "template_sentence": generated.get(
                                "question", "Unknown template"
                            ),
                            "placeholders": {
                                **s_placeholders,
                                **op_placeholders,
                                **t_placeholders,
                            },
                        }

                        from config import PATIENT_BUNDLES_DIR

                        answer = rust_evaluate_query(
                            str(PATIENT_BUNDLES_DIR),
                            patient_id_hash,
                            generated["query"],
                            template_info,
                        )
                        question_data["answer"] = answer
                    except Exception as e:
                        print(
                            f"Warning: Failed to evaluate query for {template_id} question {i+1}: {e}"
                        )
                        question_data["answer"] = None

                # Generate unique hash for this question

                question_hash = generate_question_hash(question_data)
                question_data["id"] = question_hash

                all_questions.append(question_data)

        except Exception as e:
            print(f"processing template {template_id}: {e}")
            continue

    # Save to output file (JSONL format)
    output_path = OUTPUT_DIR / output_filename
    # Ensure .jsonl extension
    if output_path.suffix == ".json":
        output_path = output_path.with_suffix(".jsonl")
    elif output_path.suffix != ".jsonl":
        # If no extension or different extension, add .jsonl
        output_path = output_path.with_suffix(".jsonl")
    print(f"Saving {len(all_questions)} questions to {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        for question in all_questions:
            json_line = json.dumps(
                question, ensure_ascii=False, default=serialize_datetime
            )
            f.write(json_line + "\n")

    print(f"Successfully generated {len(all_questions)} questions")
    print(f"Output saved to: {output_path}")


def load_split_mapping(split_file: str) -> Dict[str, Dict[str, str]]:
    """
    Load paraphrase split mapping from JSON file.

    Args:
        split_file: Path to paraphrase splits JSON file

    Returns:
        Dictionary mapping template_id to {paraphrase_text: 'train'|'val'|'test'}
    """
    if not os.path.exists(split_file):
        print(f"Warning: Split file not found: {split_file}")
        return {}

    with open(split_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_paraphrases(
    clinical_file: str,
    patient_file: str,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Load all paraphrases from both clinical and patient files without filtering.

    Args:
        clinical_file: Path to clinical paraphrase file
        patient_file: Path to patient paraphrase file

    Returns:
        Dictionary: {template_id: {'clinical_paraphrases': [...], 'patient_paraphrases': [...]}}
    """
    all_paraphrases = {}

    # Load clinical paraphrases
    if os.path.exists(clinical_file):
        with open(clinical_file, "r", encoding="utf-8") as f:
            clinical_paraphrases = json.load(f)
        for template_id, paraphrases in clinical_paraphrases.items():
            if template_id not in all_paraphrases:
                all_paraphrases[template_id] = {
                    "clinical_paraphrases": [],
                    "patient_paraphrases": [],
                }
            all_paraphrases[template_id]["clinical_paraphrases"] = paraphrases

    # Load patient paraphrases
    if os.path.exists(patient_file):
        with open(patient_file, "r", encoding="utf-8") as f:
            patient_paraphrases = json.load(f)
        for template_id, paraphrases in patient_paraphrases.items():
            if template_id not in all_paraphrases:
                all_paraphrases[template_id] = {
                    "clinical_paraphrases": [],
                    "patient_paraphrases": [],
                }
            all_paraphrases[template_id]["patient_paraphrases"] = paraphrases

    return all_paraphrases


def filter_paraphrases_by_split(
    clinical_file: str,
    patient_file: str,
    split: str,
    split_mapping: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, List[str]]]:
    """
    Filter paraphrases based on split assignment.

    Args:
        clinical_file: Path to clinical paraphrase file
        patient_file: Path to patient paraphrase file
        split: Split to filter for ('train', 'val', or 'test')
        split_mapping: Split mapping dictionary

    Returns:
        Dictionary: {template_id: {'clinical_paraphrases': [...], 'patient_paraphrases': [...]}}
    """
    filtered = {}

    # Load clinical paraphrases
    if os.path.exists(clinical_file):
        with open(clinical_file, "r", encoding="utf-8") as f:
            clinical_paraphrases = json.load(f)
        for template_id, paraphrases in clinical_paraphrases.items():
            if template_id not in filtered:
                filtered[template_id] = {
                    "clinical_paraphrases": [],
                    "patient_paraphrases": [],
                }
            # Filter paraphrases that match the split
            if template_id in split_mapping:
                template_splits = split_mapping[template_id]
                filtered_paraphrases = [
                    p
                    for p in paraphrases
                    if p in template_splits and template_splits[p] == split
                ]
                filtered[template_id]["clinical_paraphrases"] = filtered_paraphrases

    # Load patient paraphrases
    if os.path.exists(patient_file):
        with open(patient_file, "r", encoding="utf-8") as f:
            patient_paraphrases = json.load(f)
        for template_id, paraphrases in patient_paraphrases.items():
            if template_id not in filtered:
                filtered[template_id] = {
                    "clinical_paraphrases": [],
                    "patient_paraphrases": [],
                }
            # Filter paraphrases that match the split
            if template_id in split_mapping:
                template_splits = split_mapping[template_id]
                filtered_paraphrases = [
                    p
                    for p in paraphrases
                    if p in template_splits and template_splits[p] == split
                ]
                filtered[template_id]["patient_paraphrases"] = filtered_paraphrases

    return filtered


def get_paraphrase_split(
    template_id: str,
    paraphrase: str,
    split_mapping: Dict[str, Dict[str, str]],
) -> Optional[str]:
    """
    Get the split assignment for a given paraphrase.

    Args:
        template_id: Template ID
        paraphrase: Paraphrase text
        split_mapping: Split mapping dictionary

    Returns:
        Split assignment ('train', 'val', 'test') or None if not found
    """
    if template_id not in split_mapping:
        return None
    return split_mapping[template_id].get(paraphrase)


def generate_question_for_paraphrase(
    template_id: str,
    perspective: str,
    ctx: GenerationContext,
    patient_id: str,
    patient_id_hash: str,
    evaluate: bool,
    annotated: bool,
    selected_paraphrase: Optional[str] = None,
    split_mapping: Optional[Dict[str, Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate a question-answer pair for a specific paraphrase.

    This is similar to the function in generate_final_dataset.py but adapted for generate_questions.py.

    Args:
        template_id: Template ID
        perspective: 'clinical' or 'patient'
        ctx: Generation context
        patient_id: Patient ID
        patient_id_hash: Patient ID hash
        evaluate: Whether to evaluate the query
        annotated: Whether to include annotated fields
        selected_paraphrase: Optional specific paraphrase to use.

    Returns:
        Question data dictionary if successful, None otherwise
    """
    from config import PATIENT_BUNDLES_DIR

    try:
        # Create template instance
        template = template_registry.new_template(template_id, gen_ctx=ctx)
        # Set the specific paraphrase BEFORE regenerating placeholders
        template._selected_paraphrase = selected_paraphrase

        # Manually regenerate placeholders without calling _select_paraphrase()
        template.simple_placeholders = {}
        template.time_placeholders = {}
        template.operation_placeholders = {}
        template._validate_and_autofill()

        # Generate question-answer pair
        generated = template.generate_qa_pair()

        # Extract placeholders
        placeholders = generated.get("placeholders", {})
        s_placeholders = placeholders.get("simple", {})
        op_placeholders = placeholders.get("operation", {})
        t_placeholders = placeholders.get("time", {})

        # Convert placeholders to serializable dictionaries
        def serialize_placeholders(placeholder_dict):
            """Convert placeholder objects to dictionaries."""
            if not placeholder_dict:
                return placeholder_dict
            result = {}
            for key, placeholder_obj in placeholder_dict.items():
                if hasattr(placeholder_obj, "model_dump"):
                    result[key] = placeholder_obj.model_dump()
                else:
                    result[key] = placeholder_obj
            return result

        # Strip the "Context: patient #######." prefix from the question
        cleaned_question = strip_patient_context_prefix(generated["question"])

        # Create the question data structure
        question_data = {
            "patient_id": patient_id,
            "question": cleaned_question,
            "query": generated["query"],
            "now": ctx.now.isoformat(),
            "perspective": perspective,
            "patient_id_hash": patient_id_hash,
            "question_template_id": template_id,
            "question_template": generated["template"],
        }

        # Add split if we have the mapping and paraphrase
        if split_mapping and selected_paraphrase:
            paraphrase_split = get_paraphrase_split(
                template_id, selected_paraphrase, split_mapping
            )
            if paraphrase_split:
                question_data["split"] = paraphrase_split

        # Add answer if evaluation is enabled
        if evaluate:
            try:
                # Prepare template debugging information
                template_info = {
                    "template_id": template_id,
                    "template_sentence": generated.get("question", "Unknown template"),
                    "placeholders": {
                        **s_placeholders,
                        **op_placeholders,
                        **t_placeholders,
                    },
                }

                answer = rust_evaluate_query(
                    str(PATIENT_BUNDLES_DIR),
                    patient_id_hash,
                    generated["query"],
                    template_info,
                )

                # Check if answer is null
                if answer in ["[]", "[0]"]:
                    return None

                question_data["answer"] = answer

            except Exception as e:
                print(f"Warning: Failed to evaluate query for {template_id}: {e}")
                return None

        # Add annotated information if requested
        if annotated:
            question_data.update(
                {
                    "s_placeholders": serialize_placeholders(s_placeholders),
                    "op_placeholders": serialize_placeholders(op_placeholders),
                    "t_placeholders": serialize_placeholders(t_placeholders),
                }
            )

        # Generate unique hash for this question
        question_hash = generate_question_hash(question_data)
        question_data["id"] = question_hash

        return question_data

    except Exception as e:
        print(f"Error generating question for {template_id}: {e}")
        return None


def generate_dataset(
    patient_ids_file: str,
    num_questions_per_template: int,
    output_filename: str,
    evaluate: bool = False,
    filter_ehrsql: bool = False,
    annotated: bool = False,
    template_names: List[str] = None,
    paraphrase: bool = False,
    paraphrase_file: Optional[str] = None,
    split: Optional[str] = None,
    split_file: str = "paraphrasing/paraphrase_splits.json",
    clinical_paraphrase_file: str = "paraphrasing/paraphrases_clinical_validated.json",
    patient_paraphrase_file: str = "paraphrasing/paraphrases_patient_validated.json",
) -> None:
    """
    Generate questions for multiple patients to create a dataset.

    Args:
        patient_ids_file: File containing patient IDs, one per line
        num_questions_per_template: Number of questions to generate per template
        output_filename: Output JSON file name
        evaluate: Whether to evaluate questions using octofhir-fhirpath
        filter_ehrsql: Whether to filter patient values against EHR-SQL valuesets
        annotated: Whether to include full template and placeholder information
        template_names: List of template names to use (None for all templates)
        paraphrase: Whether to use paraphrased templates
        paraphrase_file: Path to the paraphrase file to use (if None, uses default)
        split: Split to use ('train', 'val', or 'test'). If provided, filters paraphrases.
        split_file: Path to paraphrase splits JSON file
        clinical_paraphrase_file: Path to clinical paraphrase file
        patient_paraphrase_file: Path to patient paraphrase file
    """
    # Read patient IDs from file
    try:
        with open(patient_ids_file, "r", encoding="utf-8") as f:
            patient_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Patient IDs file '{patient_ids_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading patient IDs file: {e}")
        sys.exit(1)

    if not patient_ids:
        print("Error: No patient IDs found in file")
        sys.exit(1)

    # Always load split mapping if using paraphrases (to include split field in output)
    split_mapping = {}
    all_paraphrases = {}
    filtered_paraphrases = {}
    if paraphrase:
        print(f"Loading split mapping from {split_file}")
        split_mapping = load_split_mapping(split_file)
        if not split_mapping:
            print(
                f"Warning: Could not load split mapping from {split_file}. Split field will not be included."
            )
        else:
            print(f"Loaded split mapping for {len(split_mapping)} templates")

    # If split is specified, filter paraphrases
    if split:
        if split not in ["train", "val", "test"]:
            print(f"Error: Split must be 'train', 'val', or 'test', got '{split}'")
            sys.exit(1)
        if not paraphrase:
            print(
                "Warning: Split specified but paraphrase is not enabled. Enabling paraphrase mode."
            )
            paraphrase = True
            # Load split mapping if we just enabled paraphrases
            if not split_mapping:
                split_mapping = load_split_mapping(split_file)
        if split_mapping:
            filtered_paraphrases = filter_paraphrases_by_split(
                clinical_paraphrase_file,
                patient_paraphrase_file,
                split,
                split_mapping,
            )
            print(f"Filtered paraphrases for {split} split")
        else:
            print(f"Error: Could not load split mapping to filter paraphrases")
            sys.exit(1)
    elif paraphrase:
        # Load all paraphrases when split is not specified (to determine split for each)
        print("Loading all paraphrases (split not specified)")
        all_paraphrases = load_all_paraphrases(
            clinical_paraphrase_file,
            patient_paraphrase_file,
        )
        print(f"Loaded paraphrases for {len(all_paraphrases)} templates")

    print(f"Generating dataset for {len(patient_ids)} patients")
    print(f"Questions per template: {num_questions_per_template}")
    print(f"Evaluation enabled: {evaluate}")
    print(f"EHR-SQL filtering enabled: {filter_ehrsql}")
    print(f"Annotated mode: {annotated}")
    print(f"Paraphrasing enabled: {paraphrase}")
    if split:
        print(f"Split: {split}")
    if template_names:
        print(f"Templates: ({len(template_names)}) {template_names}")
    else:
        print("Templates: All available")

    # Validate templates early if specified
    if template_names:
        available_templates = template_registry.list_templates()
        invalid_templates = [
            name for name in template_names if name not in available_templates
        ]
        if invalid_templates:
            print(
                f"Error: The following templates are not implemented: {invalid_templates}"
            )
            print(f"Available templates: {available_templates}")
            sys.exit(1)

    all_questions = []
    total_questions = 0
    successful_patients = 0
    failed_patients = 0
    question_index = 0

    for i, patient_id in enumerate(patient_ids, 1):
        print(f"\n--- Processing patient {i}/{len(patient_ids)}: {patient_id} ---")

        try:
            # Generate questions for this patient
            patient_questions = []

            # Get patient hash
            patient_id_hash = get_patient_id_hash(patient_id)

            # Create generation context with fallback
            print(f"Creating context for patient {patient_id}...")
            start_time = time.time()

            ctx, context_type = create_context_with_fallback(
                patient_id,
                filter_against_ehrsql=filter_ehrsql,
                use_paraphrases=paraphrase,
                paraphrase_file=paraphrase_file,
            )

            end_time = time.time()
            context_creation_time = end_time - start_time
            print(f"Context creation took {context_creation_time:.2f} seconds")
            print(f"Context type: {context_type}")

            # Get templates to use
            if template_names is None:
                template_ids = template_registry.list_templates()
            else:
                template_ids = template_names

            # Generate questions for each template
            for template_id in template_ids:
                template_id_time_start = time.time()
                try:
                    # Determine which paraphrases to use
                    template_paraphrases = None
                    if paraphrase:
                        if split and template_id in filtered_paraphrases:
                            # Use filtered paraphrases when split is specified
                            template_paraphrases = filtered_paraphrases[template_id]
                        elif not split and template_id in all_paraphrases:
                            # Use all paraphrases when split is not specified
                            template_paraphrases = all_paraphrases[template_id]

                    # If we have paraphrases, use them to generate questions
                    if template_paraphrases:
                        clinical_paraphrases = template_paraphrases.get(
                            "clinical_paraphrases", []
                        )
                        patient_paraphrases = template_paraphrases.get(
                            "patient_paraphrases", []
                        )

                        # Try to generate questions using paraphrases
                        for j in range(num_questions_per_template):
                            # Randomly select perspective and paraphrase
                            import random

                            rng = random.Random()
                            perspectives = []
                            if clinical_paraphrases:
                                perspectives.append(("clinical", clinical_paraphrases))
                            if patient_paraphrases:
                                perspectives.append(("patient", patient_paraphrases))

                            if not perspectives:
                                # No paraphrases available for this template
                                if split:
                                    print(
                                        f"Warning: No paraphrases available for template {template_id} in {split} split"
                                    )
                                else:
                                    print(
                                        f"Warning: No paraphrases available for template {template_id}"
                                    )
                                break

                            perspective, paraphrases_list = rng.choice(perspectives)
                            selected_paraphrase = rng.choice(paraphrases_list)

                            # Create context with paraphrases enabled if not already
                            if not ctx.use_paraphrases:
                                ctx.use_paraphrases = True

                            question_data = generate_question_for_paraphrase(
                                template_id,
                                perspective,
                                ctx,
                                patient_id,
                                patient_id_hash,
                                evaluate,
                                annotated,
                                selected_paraphrase,
                                split_mapping,
                            )

                            if question_data:
                                question_data["index"] = question_index
                                question_index += 1
                                patient_questions.append(question_data)
                    else:
                        # If not using paraphrases (or no paraphrases available), use template regeneration
                        # Original behavior: use template regeneration
                        template = template_registry.new_template(
                            template_id, gen_ctx=ctx
                        )

                        for j in range(num_questions_per_template):
                            # Generate a new question-answer pair
                            generated = template.regenerate_qa_pair()

                            # Extract placeholders
                            placeholders = generated.get("placeholders", {})
                            s_placeholders = placeholders.get("simple", {})
                            op_placeholders = placeholders.get("operation", {})
                            t_placeholders = placeholders.get("time", {})

                            # Convert placeholders to serializable dictionaries
                            def serialize_placeholders(placeholder_dict):
                                """Convert placeholder objects to dictionaries."""
                                if not placeholder_dict:
                                    return placeholder_dict
                                result = {}
                                for key, placeholder_obj in placeholder_dict.items():
                                    if hasattr(placeholder_obj, "model_dump"):
                                        result[key] = placeholder_obj.model_dump()
                                    else:
                                        result[key] = placeholder_obj
                                return result

                            # Create the question data structure
                            # When annotated is False, still include required fields
                            question_data = {
                                "patient_id": patient_id,
                                "question": generated["question"],
                                "query": generated["query"],
                                "now": ctx.now.isoformat(),
                                "perspective": "clinical",  # Default to clinical if not using paraphrases
                                "patient_id_hash": patient_id_hash,
                                "question_template_id": template_id,
                                "question_template": generated["template"],
                                "index": question_index,
                            }
                            question_index += 1

                            # Note: split field is only included when using paraphrases (handled in generate_question_for_paraphrase)

                            # Add annotated information if requested
                            if annotated:
                                question_data.update(
                                    {
                                        "s_placeholders": serialize_placeholders(
                                            s_placeholders
                                        ),
                                        "op_placeholders": serialize_placeholders(
                                            op_placeholders
                                        ),
                                        "t_placeholders": serialize_placeholders(
                                            t_placeholders
                                        ),
                                    }
                                )

                            # Add answer if evaluation is enabled
                            if evaluate:
                                try:
                                    # Prepare template debugging information
                                    template_info = {
                                        "template_id": template_id,
                                        "template_sentence": generated.get(
                                            "question", "Unknown template"
                                        ),
                                        "placeholders": {
                                            **s_placeholders,
                                            **op_placeholders,
                                            **t_placeholders,
                                        },
                                    }

                                    from config import PATIENT_BUNDLES_DIR

                                    answer = rust_evaluate_query(
                                        str(PATIENT_BUNDLES_DIR),
                                        patient_id_hash,
                                        generated["query"],
                                        template_info,
                                    )

                                    question_data["answer"] = answer
                                except Exception as e:
                                    print(
                                        f"Warning: Failed to evaluate query for {template_id}: {e}"
                                    )
                                    question_data["answer"] = None

                            # Generate unique hash for this question
                            question_hash = generate_question_hash(question_data)
                            question_data["id"] = question_hash

                            patient_questions.append(question_data)

                except Exception as e:
                    print(
                        f"Error processing template {template_id} for patient {patient_id}: {e}"
                    )
                    continue

                template_id_time_end = time.time()
                template_id_time = template_id_time_end - template_id_time_start
                print(f"Template {template_id} took: {template_id_time:.2f} s")

            all_questions.extend(patient_questions)
            total_questions += len(patient_questions)
            successful_patients += 1
            print(
                f"Generated {len(patient_questions)} questions for patient {patient_id}"
            )

        except Exception as e:
            print(f"Error processing patient {patient_id}: {e}")
            failed_patients += 1
            continue

    # Save to output file (JSONL format)
    output_path = OUTPUT_DIR / output_filename
    # Ensure .jsonl extension
    if output_path.suffix == ".json":
        output_path = output_path.with_suffix(".jsonl")
    elif output_path.suffix != ".jsonl":
        # If no extension or different extension, add .jsonl
        output_path = output_path.with_suffix(".jsonl")
    print(f"\nSaving {total_questions} questions to {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        for question in all_questions:
            json_line = json.dumps(
                question, ensure_ascii=False, default=serialize_datetime
            )
            f.write(json_line + "\n")

    print(f"\nDataset generation complete!")
    print(f"Total questions generated: {total_questions}")
    print(f"Successful patients: {successful_patients}")
    print(f"Failed patients: {failed_patients}")
    print(f"Output saved to: {output_path}")


def main():
    """Main function to parse arguments and run the script."""
    parser = argparse.ArgumentParser(
        description="Generate random questions for each template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single patient mode
  python generate_questions.py 10019917 5 questions_output.json
  python generate_questions.py 10019917 3 questions_with_answers.json --evaluate
  
  # Dataset mode
  python generate_questions.py --dataset patient_ids.txt 3 dataset_output.json --evaluate
  python generate_questions.py --dataset patient_ids.txt 2 dataset_output.json --templates "count-drugs-prescribed,has-diagnosis" --evaluate
  python generate_questions.py --dataset patient_ids.txt 2 dataset_output.json --paraphrase --evaluate
        """,
    )

    # Dataset mode flag
    parser.add_argument(
        "--dataset",
        action="store_true",
        help="Enable dataset mode for multiple patients (requires patient_ids_file argument)",
    )

    # Positional arguments (conditional based on dataset mode)
    parser.add_argument(
        "patient_id_or_file",
        help="Patient ID (single mode) or patient IDs file (dataset mode)",
    )

    parser.add_argument(
        "num_questions_per_template",
        type=int,
        help="Number of questions to generate per template",
    )

    parser.add_argument("output_filename", help="Output JSON file name")

    # Optional arguments
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Also evaluate questions using octofhir-fhirpath (slower)",
    )

    parser.add_argument(
        "--filter-ehrsql",
        action="store_true",
        help="Filter patient values to only include those that are also in EHR-SQL valuesets",
    )

    parser.add_argument(
        "--annotated",
        action="store_true",
        help="Include full template and placeholder information (default: False for dataset mode, True for single patient mode)",
    )

    parser.add_argument(
        "--templates",
        type=str,
        help="Comma-separated list of template names to use (optional, uses all templates if not specified)",
    )

    parser.add_argument(
        "--paraphrase",
        action="store_true",
        help="Use paraphrased templates when generating questions (selects from paraphrase variants deterministically)",
    )

    parser.add_argument(
        "--paraphrase-file",
        type=str,
        help="Path to the paraphrase file to use (default: fhirpath_gen/template_paraphrases_clinical.json)",
    )

    parser.add_argument(
        "--split",
        type=str,
        choices=["train", "val", "test"],
        help="Split to use ('train', 'val', or 'test'). Filters paraphrases based on split assignment.",
    )

    parser.add_argument(
        "--split-file",
        type=str,
        default="paraphrasing/paraphrase_splits.json",
        help="Path to paraphrase splits JSON file (default: paraphrasing/paraphrase_splits.json)",
    )

    parser.add_argument(
        "--clinical-paraphrase-file",
        type=str,
        default="paraphrasing/paraphrases_clinical_validated.json",
        help="Path to clinical paraphrase file (default: paraphrasing/paraphrases_clinical_validated.json)",
    )

    parser.add_argument(
        "--patient-paraphrase-file",
        type=str,
        default="paraphrasing/paraphrases_patient_validated.json",
        help="Path to patient paraphrase file (default: paraphrasing/paraphrases_patient_validated.json)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.num_questions_per_template <= 0:
        print("Error: num_questions_per_template must be positive")
        sys.exit(1)

    if not (
        args.output_filename.endswith(".json")
        or args.output_filename.endswith(".jsonl")
    ):
        print(
            "Warning: output filename should end with .json or .jsonl (will be saved as .jsonl)"
        )

    # Parse template names if provided
    template_names = None
    if args.templates:
        template_names = [
            name.strip() for name in args.templates.split(",") if name.strip()
        ]

    try:
        if args.dataset:
            # Dataset mode
            generate_dataset(
                args.patient_id_or_file,
                args.num_questions_per_template,
                args.output_filename,
                args.evaluate,
                args.filter_ehrsql,
                args.annotated,  # Default False for dataset mode
                template_names,
                args.paraphrase,
                args.paraphrase_file,
                args.split,
                args.split_file,
                args.clinical_paraphrase_file,
                args.patient_paraphrase_file,
            )
        else:
            # Single patient mode
            generate_questions_for_patient(
                args.patient_id_or_file,
                args.num_questions_per_template,
                args.output_filename,
                args.evaluate,
                args.filter_ehrsql,
                args.annotated,
                template_names,
                args.paraphrase,
                args.paraphrase_file,
            )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
