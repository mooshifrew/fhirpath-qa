#!/usr/bin/env python3
"""
Script to generate final dataset ensuring one positive question per paraphrase.

This script cycles through patients, generating 10 questions per patient per cycle,
ensuring each paraphrase gets at least 1 (max 2) positive question. It supports
checkpointing and resuming for long-running generation processes.

Usage:
    python generate_final_dataset.py [options]

Examples:
    # Basic usage with defaults
    python generate_final_dataset.py

    # Custom paths
    python generate_final_dataset.py --patient-ids-file patient_ids.txt --output-file output/final.json

    # Resume from checkpoint
    python generate_final_dataset.py --resume

    # Reset and start fresh
    python generate_final_dataset.py --reset-checkpoint
"""

import argparse
import json
import hashlib
import sys
import os
import time
import re
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add the fhirpath_gen module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "fhirpath_gen"))

# Import the main module to trigger registration of all components
import fhirpath_gen

from fhirpath_gen.base import template_registry
from fhirpath_gen.generator import GenerationContext, create_patient_specific_context
from fhirpath_gen.utils import rust_evaluate_query, ID2NUM, NUM2ID
from config import OUTPUT_DIR, PATIENT_IDS_FILE, PATIENT_BUNDLES_DIR


# Reuse functions from generate_questions.py
from generate_questions import (
    serialize_datetime,
    generate_question_hash,
    get_patient_id_hash,
    create_context_with_fallback,
    load_split_mapping,
    get_paraphrase_split,
)


def load_paraphrase_tracking(
    clinical_file: str, patient_file: str, skip_diagnosis_name: bool = False
) -> Dict[str, Dict[str, List[str]]]:
    """
    Load clinical and patient paraphrase files into nested dictionary structure.

    Args:
        clinical_file: Path to clinical paraphrase file
        patient_file: Path to patient paraphrase file
        skip_diagnosis_name: Whether to skip loading diagnosis name paraphrases (they take a long time to evaluate)
    Returns:
        Dictionary: {template_id: {'clinical_paraphrases': [...], 'patient_paraphrases': [...]}}
    """
    tracking = {}

    # Load clinical paraphrases
    if os.path.exists(clinical_file):
        with open(clinical_file, "r", encoding="utf-8") as f:
            clinical_paraphrases = json.load(f)
        for template_id, paraphrases in clinical_paraphrases.items():
            if template_id not in tracking:
                tracking[template_id] = {
                    "clinical_paraphrases": [],
                    "patient_paraphrases": [],
                }
            tracking[template_id]["clinical_paraphrases"] = paraphrases
    else:
        print(f"Warning: Clinical paraphrase file not found: {clinical_file}")

    # Load patient paraphrases
    if os.path.exists(patient_file):
        with open(patient_file, "r", encoding="utf-8") as f:
            patient_paraphrases = json.load(f)
        for template_id, paraphrases in patient_paraphrases.items():
            if template_id not in tracking:
                tracking[template_id] = {
                    "clinical_paraphrases": [],
                    "patient_paraphrases": [],
                }
            tracking[template_id]["patient_paraphrases"] = paraphrases
    else:
        print(f"Warning: Patient paraphrase file not found: {patient_file}")

    if skip_diagnosis_name:
        tracking = {k: v for k, v in tracking.items() if k != "diagnosis-name"}

    return tracking


def load_checkpoint(
    checkpoint_file: str,
) -> Tuple[Dict[str, Dict[str, List[str]]], int, int, int]:
    """
    Load checkpoint file if it exists.

    Args:
        checkpoint_file: Path to checkpoint file

    Returns:
        Tuple of (paraphrase_tracking_dict, last_patient_index, last_question_index, cycle_number)
    """
    if not os.path.exists(checkpoint_file):
        return {}, 0, 0, 0

    try:
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)
        tracking = checkpoint.get("paraphrase_tracking", {})
        patient_index = checkpoint.get("last_patient_index", 0)
        question_index = checkpoint.get("last_question_index", 0)
        cycle_number = checkpoint.get("cycle_number", 0)
        return tracking, patient_index, question_index, cycle_number
    except Exception as e:
        print(f"Warning: Failed to load checkpoint: {e}")
        return {}, 0, 0, 0


def save_checkpoint(
    checkpoint_file: str,
    tracking_dict: Dict[str, Dict[str, List[str]]],
    patient_index: int,
    question_index: int,
    cycle_number: int,
):
    """
    Save current state to checkpoint file.

    Args:
        checkpoint_file: Path to checkpoint file
        tracking_dict: Paraphrase tracking dictionary
        patient_index: Current patient index in cycle
        question_index: Global question counter
        cycle_number: Current cycle number
    """
    checkpoint = {
        "paraphrase_tracking": tracking_dict,
        "last_patient_index": patient_index,
        "last_question_index": question_index,
        "cycle_number": cycle_number,
        "timestamp": datetime.now().isoformat(),
    }

    # Ensure directory exists
    checkpoint_dir = os.path.dirname(checkpoint_file)
    if checkpoint_dir:
        os.makedirs(checkpoint_dir, exist_ok=True)

    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(
            checkpoint, f, indent=2, ensure_ascii=False, default=serialize_datetime
        )


def is_null_answer(answer: str) -> bool:
    """
    Check if answer is null.

    Args:
        answer: Answer string

    Returns:
        True if answer is null ([] or [0]), False otherwise
    """
    return answer in ["[]", "[0]"]


def get_available_paraphrases(
    template_id: str,
    perspective: str,
    tracking_dict: Dict[str, Dict[str, List[str]]],
) -> List[str]:
    """
    Get available paraphrases for a template and perspective.

    Args:
        template_id: Template ID
        perspective: 'clinical' or 'patient'
        tracking_dict: Paraphrase tracking dictionary

    Returns:
        List of available paraphrases
    """
    if template_id not in tracking_dict:
        return []

    perspective_key = f"{perspective}_paraphrases"
    if perspective_key not in tracking_dict[template_id]:
        return []

    paraphrases = tracking_dict[template_id][perspective_key]
    return paraphrases if paraphrases else []


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
) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Generate a question-answer pair for a specific paraphrase.

    Args:
        template_id: Template ID
        perspective: 'clinical' or 'patient'
        ctx: Generation context
        patient_id: Patient ID
        patient_id_hash: Patient ID hash
        evaluate: Whether to evaluate the query
        annotated: Whether to include annotated fields
        selected_paraphrase: Optional specific paraphrase to use. If None, randomly selects from available_paraphrases.

    Returns:
        Tuple of (question_data_dict, used_paraphrase) if answer is non-null, None otherwise
    """

    try:

        # Create template instance
        template = template_registry.new_template(template_id, gen_ctx=ctx)
        # Set the specific paraphrase BEFORE regenerating placeholders
        template._selected_paraphrase = selected_paraphrase

        # Manually regenerate placeholders without calling _select_paraphrase()
        # (which would overwrite our manually set paraphrase)
        template.simple_placeholders = {}
        template.time_placeholders = {}
        template.operation_placeholders = {}
        template._validate_and_autofill()

        # Generate question-answer pair (this will use our manually set paraphrase)
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

        # Create the question data structure if evaluation was successful
        question_data = {
            "patient_id": patient_id,
            "question": generated["question"],
            "query": generated["query"],
            "now": ctx.now.isoformat(),
            "perspective": perspective,
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
                if is_null_answer(answer):
                    return None

                question_data["answer"] = answer

            except Exception as e:
                print(f"Warning: Failed to evaluate query for {template_id}: {e}")
                return None

        # Strip the "Context: patient #######." prefix from the question
        # This prefix is needed for slot filling but shouldn't be in the final output
        cleaned_question = strip_patient_context_prefix(generated["question"])
        question_data["question"] = cleaned_question

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

        # Generate unique hash for this question
        question_hash = generate_question_hash(question_data)
        question_data["id"] = question_hash

        return question_data

    except Exception as e:
        print(f"Error generating question for {template_id}: {e}")
        return None


def append_question_to_dataset(
    output_file: str, question_data: Dict[str, Any], index: int
):
    """
    Append question to output JSONL file (JSON Lines format).

    Args:
        output_file: Path to output file (will use .jsonl extension)
        question_data: Question data dictionary
        index: Question index
    """
    question_data["index"] = index

    # Convert .json to .jsonl extension for JSON Lines format
    if output_file.endswith(".json"):
        jsonl_file = output_file[:-5] + ".jsonl"
    elif not output_file.endswith(".jsonl"):
        jsonl_file = output_file + ".jsonl"
    else:
        jsonl_file = output_file

    # Ensure directory exists
    output_dir = os.path.dirname(jsonl_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Append as a single JSON line (JSONL format)
    # This is O(1) instead of O(n) - much more efficient for large datasets
    with open(jsonl_file, "a", encoding="utf-8") as f:
        json_line = json.dumps(
            question_data, ensure_ascii=False, default=serialize_datetime
        )
        f.write(json_line + "\n")


def remove_paraphrase_from_tracking(
    tracking_dict: Dict[str, Dict[str, List[str]]],
    template_id: str,
    perspective: str,
    paraphrase: str,
):
    """
    Remove used paraphrase from tracking dictionary.
    Also removes the template entry if both clinical and patient lists become empty.

    Args:
        tracking_dict: Paraphrase tracking dictionary
        template_id: Template ID
        perspective: 'clinical' or 'patient'
        paraphrase: Paraphrase to remove
    """
    if template_id not in tracking_dict:
        return

    perspective_key = f"{perspective}_paraphrases"
    if perspective_key not in tracking_dict[template_id]:
        return

    paraphrases = tracking_dict[template_id][perspective_key]
    if paraphrase in paraphrases:
        paraphrases.remove(paraphrase)

    # Check if both lists are now empty, and remove the template entry if so
    clinical_empty = not tracking_dict[template_id].get("clinical_paraphrases", [])
    patient_empty = not tracking_dict[template_id].get("patient_paraphrases", [])

    if clinical_empty and patient_empty:
        del tracking_dict[template_id]


def select_random_template_and_paraphrase(
    tracking_dict: Dict[str, Dict[str, List[str]]],
    rng,
) -> Optional[Tuple[str, str, str]]:
    """
    Randomly select a template ID, perspective, and paraphrase from available options.
    Efficiently selects from the tracking dict without building large lists.

    Args:
        tracking_dict: Paraphrase tracking dictionary
        rng: Random number generator

    Returns:
        Tuple of (template_id, perspective, paraphrase) if available, None otherwise
    """
    if not tracking_dict:
        return None

    # First, randomly select a template_id that has available paraphrases
    template_ids = list(tracking_dict.keys())
    if not template_ids:
        return None

    # Keep trying until we find a template with available paraphrases
    # (This should be rare since we remove empty templates, but handle it safely)
    max_attempts = len(template_ids) * 2
    for _ in range(max_attempts):
        template_id = rng.choice(template_ids)
        template_data = tracking_dict[template_id]

        # Collect available perspectives for this template
        available_perspectives = []
        if template_data.get("clinical_paraphrases"):
            available_perspectives.append("clinical")
        if template_data.get("patient_paraphrases"):
            available_perspectives.append("patient")

        if not available_perspectives:
            # This template has no paraphrases (shouldn't happen if cleanup works)
            continue

        # Randomly select a perspective
        perspective = rng.choice(available_perspectives)

        # Get paraphrases for this perspective
        paraphrases = template_data.get(f"{perspective}_paraphrases", [])
        if not paraphrases:
            continue

        # Randomly select a paraphrase
        paraphrase = rng.choice(paraphrases)

        return (template_id, perspective, paraphrase)

    # If we couldn't find anything after max attempts, return None
    return None


def count_remaining_paraphrases(
    tracking_dict: Dict[str, Dict[str, List[str]]],
) -> Tuple[int, int]:
    """
    Count remaining paraphrases.

    Args:
        tracking_dict: Paraphrase tracking dictionary

    Returns:
        Tuple of (total_clinical, total_patient) remaining paraphrases
    """
    total_clinical = 0
    total_patient = 0

    for template_id, perspectives in tracking_dict.items():
        total_clinical += len(perspectives.get("clinical_paraphrases", []))
        total_patient += len(perspectives.get("patient_paraphrases", []))

    return total_clinical, total_patient


def generate_final_dataset(
    patient_ids_file: str,
    clinical_paraphrases_file: str,
    patient_paraphrases_file: str,
    output_file: str,
    checkpoint_file: str,
    questions_per_patient: int = 10,
    evaluate: bool = True,
    annotated: bool = True,
    filter_ehrsql: bool = False,
    resume: bool = True,
    reset_checkpoint: bool = False,
    skip_diagnosis_name: bool = False,
    seed: int = 42,
    split_file: str = "paraphrasing/paraphrase_splits.json",
):
    """
    Main function to generate final dataset.

    Args:
        patient_ids_file: Path to patient IDs file
        clinical_paraphrases_file: Path to clinical paraphrase file
        patient_paraphrases_file: Path to patient paraphrase file
        output_file: Path to output dataset file
        checkpoint_file: Path to checkpoint file
        questions_per_patient: Number of questions per patient per cycle
        evaluate: Whether to evaluate queries
        annotated: Whether to include annotated fields
        filter_ehrsql: Whether to filter against EHR-SQL valuesets
        resume: Whether to resume from checkpoint
        reset_checkpoint: Whether to reset checkpoint and start fresh
        split_file: Path to paraphrase splits JSON file for train/val/test split assignment
    """
    print("=" * 60)
    print("Final Dataset Generation")
    print("=" * 60)
    print(f"Patient IDs file: {patient_ids_file}")
    print(f"Clinical paraphrases: {clinical_paraphrases_file}")
    print(f"Patient paraphrases: {patient_paraphrases_file}")
    print(f"Output file: {output_file}")
    print(f"Checkpoint file: {checkpoint_file}")
    print(f"Questions per patient: {questions_per_patient}")
    print(f"Evaluate: {evaluate}")
    print(f"Annotated: {annotated}")
    print(f"Filter EHR-SQL: {filter_ehrsql}")
    print(f"Skip diagnosis name: {skip_diagnosis_name}")
    print("=" * 60)

    # Load patient IDs
    try:
        with open(patient_ids_file, "r", encoding="utf-8") as f:
            patient_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Patient IDs file '{patient_ids_file}' not found")
        sys.exit(1)

    if not patient_ids:
        print("Error: No patient IDs found in file")
        sys.exit(1)

    print(f"Loaded {len(patient_ids)} patient IDs")

    # Load split mapping for train/val/test split assignment
    print(f"Loading split mapping from {split_file}...")
    split_mapping = load_split_mapping(split_file)
    if split_mapping:
        print(f"Loaded split mapping for {len(split_mapping)} templates")
    else:
        print("Warning: Could not load split mapping. Split field will not be included.")

    # Load paraphrase tracking
    print("Loading paraphrase files...")
    tracking = load_paraphrase_tracking(
        clinical_paraphrases_file,
        patient_paraphrases_file,
        skip_diagnosis_name=skip_diagnosis_name,
    )
    total_clinical, total_patient = count_remaining_paraphrases(tracking)
    print(f"Initial paraphrases: {total_clinical} clinical, {total_patient} patient")

    # Load checkpoint
    if reset_checkpoint and os.path.exists(checkpoint_file):
        print("Resetting checkpoint...")
        os.remove(checkpoint_file)
        patient_index = 0
        question_index = 0
        cycle_number = 0
    elif resume:
        print("Loading checkpoint...")
        checkpoint_tracking, patient_index, question_index, cycle_number = (
            load_checkpoint(checkpoint_file)
        )
        if checkpoint_tracking:
            # Rebuild tracking from current files, then remove paraphrases that were already answered
            # This ensures we're using the same paraphrase files as the context
            print("Rebuilding tracking dictionary from current paraphrase files...")
            fresh_tracking = load_paraphrase_tracking(
                clinical_paraphrases_file,
                patient_paraphrases_file,
                skip_diagnosis_name=skip_diagnosis_name,
            )

            # For each template, remove paraphrases from fresh_tracking that are NOT in checkpoint_tracking
            # (i.e., keep only the paraphrases that haven't been answered yet)
            for template_id in fresh_tracking:
                if template_id in checkpoint_tracking:
                    # Clinical paraphrases: keep only those still in checkpoint
                    fresh_clinical = set(
                        fresh_tracking[template_id].get("clinical_paraphrases", [])
                    )
                    checkpoint_clinical = set(
                        checkpoint_tracking[template_id].get("clinical_paraphrases", [])
                    )
                    fresh_tracking[template_id]["clinical_paraphrases"] = list(
                        fresh_clinical & checkpoint_clinical
                    )

                    # Patient paraphrases: keep only those still in checkpoint
                    fresh_patient = set(
                        fresh_tracking[template_id].get("patient_paraphrases", [])
                    )
                    checkpoint_patient = set(
                        checkpoint_tracking[template_id].get("patient_paraphrases", [])
                    )
                    fresh_tracking[template_id]["patient_paraphrases"] = list(
                        fresh_patient & checkpoint_patient
                    )
                # If template not in checkpoint, keep all paraphrases (new template)

            tracking = fresh_tracking
            print(
                f"Resuming from cycle {cycle_number}, patient {patient_index}, question {question_index}"
            )
            total_clinical, total_patient = count_remaining_paraphrases(tracking)
            print(
                f"Remaining paraphrases: {total_clinical} clinical, {total_patient} patient"
            )
        else:
            print("No checkpoint found, starting fresh")
            patient_index = 0
            question_index = 0
            cycle_number = 0
    else:
        patient_index = 0
        question_index = 0
        cycle_number = 0

    # Get all template IDs
    template_ids = template_registry.list_templates()
    print(f"Using {len(template_ids)} templates")

    # Create a single shared RNG for continuous randomization across all patients
    # This ensures questions are selected in a truly random order throughout
    # the entire generation process, not resetting for each patient
    shared_rng = random.Random(seed)
    print(f"Initialized shared RNG for continuous randomization")

    # Main generation loop
    print("\nStarting generation...")
    print("=" * 60)

    while True:
        # Check if all paraphrases are answered
        total_clinical, total_patient = count_remaining_paraphrases(tracking)
        if total_clinical == 0 and total_patient == 0:
            print("\n" + "=" * 60)
            print("All paraphrases have questions!")
            print("=" * 60)
            break

        cycle_number += 1
        print(f"\n--- Cycle {cycle_number} ---")
        print(
            f"Remaining: {total_clinical} clinical, {total_patient} patient paraphrases"
        )

        # Cycle through patients
        cycle_start_patient_index = patient_index if cycle_number == 1 else 0

        for i in range(cycle_start_patient_index, len(patient_ids)):
            patient_id = patient_ids[i]
            patient_index = i

            print(
                f"\nCycle {cycle_number}, Patient {i+1}/{len(patient_ids)}: {patient_id}"
            )

            try:
                patient_id_hash = get_patient_id_hash(patient_id)

                # Create contexts once per patient (one for clinical, one for patient perspective)
                context_start_time = time.time()
                ctx_clinical, context_type_clinical = create_context_with_fallback(
                    patient_id,
                    filter_against_ehrsql=filter_ehrsql,
                    use_paraphrases=True,
                    paraphrase_file=clinical_paraphrases_file,
                )

                ctx_patient, context_type_patient = create_context_with_fallback(
                    patient_id,
                    filter_against_ehrsql=filter_ehrsql,
                    use_paraphrases=True,
                    paraphrase_file=patient_paraphrases_file,
                )

                # Replace the RNG in both contexts with the shared RNG
                # This ensures continuous randomization across all patients
                ctx_clinical.rng = shared_rng
                ctx_patient.rng = shared_rng

                context_elapsed = time.time() - context_start_time
                print(f"  Context creation took {context_elapsed:.2f} seconds")

                # If context creation took more than 9 seconds, exclude 'diagnosis-name' template
                # for this patient (only process it for patients with small bundles)
                patient_tracking = tracking
                if context_elapsed > 9.0:
                    # Create a filtered copy of tracking that excludes 'diagnosis-name'
                    patient_tracking = {
                        k: v for k, v in tracking.items() if k != "diagnosis-name"
                    }
                    if "diagnosis-name" in tracking:
                        print(
                            "  Context creation > 9 seconds: excluding 'diagnosis-name' template for this patient"
                        )

                question_start_time = (
                    time.time()
                )  # care about the time for a valid question, not invidual

                # Generate questions_per_patient questions
                questions_generated = 0
                max_attempts = questions_per_patient * 2  # Safety limit
                attempts = 0

                while (
                    questions_generated < questions_per_patient
                    and attempts < max_attempts
                ):
                    attempts += 1

                    # Directly select a random template and paraphrase from available options
                    # Use a shared RNG (from clinical context) for selection
                    # Use patient_tracking (filtered if context > 9s) for selection
                    selection = select_random_template_and_paraphrase(
                        patient_tracking, ctx_clinical.rng
                    )

                    if selection is None:
                        # No more paraphrases available
                        break

                    template_id, perspective, selected_paraphrase = selection

                    # Use the appropriate context for this perspective
                    ctx = ctx_clinical if perspective == "clinical" else ctx_patient

                    # Generate question for this template/perspective/paraphrase
                    question_data = generate_question_for_paraphrase(
                        template_id,
                        perspective,
                        ctx,
                        patient_id,
                        patient_id_hash,
                        evaluate,
                        annotated,
                        selected_paraphrase=selected_paraphrase,
                        split_mapping=split_mapping,
                    )

                    if question_data is not None:
                        question_elapsed = time.time() - question_start_time

                        # Non-null answer - add to dataset
                        append_question_to_dataset(
                            output_file, question_data, question_index
                        )
                        question_index += 1
                        questions_generated += 1

                        # Remove paraphrase from tracking
                        remove_paraphrase_from_tracking(
                            tracking, template_id, perspective, selected_paraphrase
                        )

                        # Save checkpoint periodically (every 50 questions)
                        if question_index % 50 == 0:
                            save_checkpoint(
                                checkpoint_file,
                                tracking,
                                patient_index,
                                question_index,
                                cycle_number,
                            )
                            print(f"  Checkpoint saved (question {question_index})")

                        print(
                            f"  Generated question {questions_generated}/{questions_per_patient}: '{template_id}' ({perspective}) in {question_elapsed:.2f} seconds. ({attempts} attempts)"
                        )

                        question_start_time = time.time()

                if attempts >= max_attempts:
                    print(
                        f"  Warning: Reached max attempts ({max_attempts}) without generating {questions_per_patient} questions, moving to next patient"
                    )

            except Exception as e:
                print(f"Error processing patient {patient_id}: {e}")
                continue

            # Check if all paraphrases are answered after this patient
            total_clinical, total_patient = count_remaining_paraphrases(tracking)
            if total_clinical == 0 and total_patient == 0:
                print("\n" + "=" * 60)
                print("All paraphrases have questions!")
                print("=" * 60)
                break

        # Reset patient index for next cycle
        patient_index = 0

        # Final checkpoint save
        save_checkpoint(
            checkpoint_file, tracking, patient_index, question_index, cycle_number
        )

    # Final summary
    # Determine the actual JSONL file path
    if output_file.endswith(".json"):
        jsonl_file = output_file[:-5] + ".jsonl"
    elif not output_file.endswith(".jsonl"):
        jsonl_file = output_file + ".jsonl"
    else:
        jsonl_file = output_file

    print(f"\nGeneration complete!")
    print(f"Total questions generated: {question_index}")
    print(f"Output saved to: {jsonl_file} (JSONL format)")
    print(f"Checkpoint saved to: {checkpoint_file}")


def main():
    """Main function to parse arguments and run the script."""
    parser = argparse.ArgumentParser(
        description="Generate final dataset ensuring one positive question per paraphrase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--patient-ids-file",
        type=str,
        default=str(PATIENT_IDS_FILE),
        help="Path to patient IDs file (default: patient_ids.txt)",
    )

    parser.add_argument(
        "--clinical-paraphrases",
        type=str,
        default="paraphrasing/paraphrases_clinical_validated.json",
        help="Path to clinical paraphrase file",
    )

    parser.add_argument(
        "--patient-paraphrases",
        type=str,
        default="paraphrasing/paraphrases_patient_validated.json",
        help="Path to patient paraphrase file",
    )

    parser.add_argument(
        "--output-file",
        type=str,
        default="output/final_dataset.jsonl",
        help="Output dataset file in JSONL format (default: output/final_dataset.jsonl)",
    )

    parser.add_argument(
        "--checkpoint-file",
        type=str,
        default="output/final_dataset_checkpoint.json",
        help="Checkpoint file path (default: output/final_dataset_checkpoint.json)",
    )

    parser.add_argument(
        "--questions-per-patient",
        type=int,
        default=10,
        help="Number of questions to generate per patient per cycle (default: 10)",
    )

    parser.add_argument(
        "--evaluate",
        action="store_true",
        default=True,
        help="Enable query evaluation (default: True)",
    )

    parser.add_argument(
        "--no-evaluate",
        dest="evaluate",
        action="store_false",
        help="Disable query evaluation",
    )

    parser.add_argument(
        "--annotated",
        action="store_true",
        default=True,
        help="Include annotated fields (default: True)",
    )

    parser.add_argument(
        "--no-annotated",
        dest="annotated",
        action="store_false",
        help="Exclude annotated fields",
    )

    parser.add_argument(
        "--filter-ehrsql",
        action="store_true",
        help="Filter against EHR-SQL valuesets",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from checkpoint (default: True)",
    )

    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Do not resume from checkpoint",
    )

    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="Reset checkpoint and start fresh",
    )

    parser.add_argument(
        "--skip-diagnosis-name",
        action="store_true",
        help="Skip diagnosis name paraphrases (they take a long time to evaluate)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for random number generator (default: 42)",
    )

    parser.add_argument(
        "--split-file",
        type=str,
        default="paraphrasing/paraphrase_splits.json",
        help="Path to paraphrase splits JSON file (default: paraphrasing/paraphrase_splits.json)",
    )

    args = parser.parse_args()

    try:
        generate_final_dataset(
            args.patient_ids_file,
            args.clinical_paraphrases,
            args.patient_paraphrases,
            args.output_file,
            args.checkpoint_file,
            args.questions_per_patient,
            args.evaluate,
            args.annotated,
            args.filter_ehrsql,
            args.resume,
            args.reset_checkpoint,
            args.skip_diagnosis_name,
            args.seed,
            args.split_file,
        )
    except KeyboardInterrupt:
        print("\n\nGeneration interrupted by user")
        print("Checkpoint saved - you can resume with --resume")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
