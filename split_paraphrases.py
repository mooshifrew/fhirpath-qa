#!/usr/bin/env python3
"""
Script to split paraphrases into train/val/test groups based on template_id.

For each template_id, randomly splits paraphrases into:
- Train: 80%
- Val: 8%
- Test: 12%

The output is a mapping where each paraphrase is mapped to its split assignment.
"""

import json
import random
import math
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def load_paraphrases(clinical_file: str, patient_file: str) -> Dict[str, List[str]]:
    """
    Load paraphrases from both clinical and patient files.

    Args:
        clinical_file: Path to clinical paraphrase file
        patient_file: Path to patient paraphrase file

    Returns:
        Dictionary mapping template_id to list of all paraphrases (clinical + patient combined)
    """
    all_paraphrases = defaultdict(list)

    # Load clinical paraphrases
    if Path(clinical_file).exists():
        with open(clinical_file, "r", encoding="utf-8") as f:
            clinical_paraphrases = json.load(f)
        for template_id, paraphrases in clinical_paraphrases.items():
            all_paraphrases[template_id].extend(paraphrases)
        print(f"Loaded {len(clinical_paraphrases)} templates from clinical file")
    else:
        print(f"Warning: Clinical paraphrase file not found: {clinical_file}")

    # Load patient paraphrases
    if Path(patient_file).exists():
        with open(patient_file, "r", encoding="utf-8") as f:
            patient_paraphrases = json.load(f)
        for template_id, paraphrases in patient_paraphrases.items():
            all_paraphrases[template_id].extend(paraphrases)
        print(f"Loaded {len(patient_paraphrases)} templates from patient file")
    else:
        print(f"Warning: Patient paraphrase file not found: {patient_file}")

    return dict(all_paraphrases)


def calculate_split_sizes(total: int) -> Tuple[int, int, int]:
    """
    Calculate the number of paraphrases for each split.
    Rounds up for val and test, train gets the remainder.

    Args:
        total: Total number of paraphrases

    Returns:
        Tuple of (test_count, val_count, train_count)
    """
    test_count = math.ceil(total * 0.12)
    val_count = math.ceil(total * 0.08)
    train_count = total - test_count - val_count

    return test_count, val_count, train_count


def split_paraphrases_for_template(
    template_id: str, paraphrases: List[str], seed: int = 42
) -> Dict[str, str]:
    """
    Split paraphrases for a single template_id into train/val/test.

    Args:
        template_id: Template ID
        paraphrases: List of paraphrase strings
        seed: Random seed for reproducibility

    Returns:
        Dictionary mapping paraphrase text to split assignment ('train', 'val', or 'test')
    """
    if not paraphrases:
        return {}

    # Shuffle paraphrases deterministically
    rng = random.Random(seed)
    shuffled = paraphrases.copy()
    rng.shuffle(shuffled)

    # Calculate split sizes
    total = len(shuffled)
    test_count, val_count, train_count = calculate_split_sizes(total)

    # Assign paraphrases to splits
    split_mapping = {}

    # Test set (first test_count items)
    for i in range(test_count):
        split_mapping[shuffled[i]] = "test"

    # Val set (next val_count items)
    for i in range(test_count, test_count + val_count):
        split_mapping[shuffled[i]] = "val"

    # Train set (remaining items)
    for i in range(test_count + val_count, total):
        split_mapping[shuffled[i]] = "train"

    print(
        f"  {template_id}: {total} total -> {train_count} train, {val_count} val, {test_count} test"
    )

    return split_mapping


def create_split_mapping(
    all_paraphrases: Dict[str, List[str]], seed: int = 42
) -> Dict[str, Dict[str, str]]:
    """
    Create split mapping for all template_ids.

    Args:
        all_paraphrases: Dictionary mapping template_id to list of paraphrases
        seed: Random seed for reproducibility

    Returns:
        Nested dictionary: {template_id: {paraphrase_text: 'train'|'val'|'test'}}
    """
    split_mapping = {}

    print(f"\nSplitting paraphrases for {len(all_paraphrases)} templates...")

    for template_id, paraphrases in sorted(all_paraphrases.items()):
        template_mapping = split_paraphrases_for_template(
            template_id, paraphrases, seed=seed
        )
        split_mapping[template_id] = template_mapping

    return split_mapping


def save_split_mapping(split_mapping: Dict[str, Dict[str, str]], output_file: str):
    """
    Save split mapping to JSON file.

    Args:
        split_mapping: The split mapping dictionary
        output_file: Path to output file
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(split_mapping, f, indent=2, ensure_ascii=False)

    print(f"\nSaved split mapping to {output_path}")

    # Print summary statistics
    total_train = sum(
        1
        for template_mapping in split_mapping.values()
        for split in template_mapping.values()
        if split == "train"
    )
    total_val = sum(
        1
        for template_mapping in split_mapping.values()
        for split in template_mapping.values()
        if split == "val"
    )
    total_test = sum(
        1
        for template_mapping in split_mapping.values()
        for split in template_mapping.values()
        if split == "test"
    )
    total = total_train + total_val + total_test

    print(f"\nSummary:")
    print(f"  Total paraphrases: {total}")
    print(f"  Train: {total_train} ({100*total_train/total:.1f}%)")
    print(f"  Val: {total_val} ({100*total_val/total:.1f}%)")
    print(f"  Test: {total_test} ({100*total_test/total:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Split paraphrases into train/val/test groups by template_id"
    )
    parser.add_argument(
        "--clinical-file",
        type=str,
        default="paraphrasing/paraphrases_clinical_validated.json",
        help="Path to clinical paraphrase file",
    )
    parser.add_argument(
        "--patient-file",
        type=str,
        default="paraphrasing/paraphrases_patient_validated.json",
        help="Path to patient paraphrase file",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="paraphrasing/paraphrase_splits.json",
        help="Path to output file for split mapping",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    # Load paraphrases
    print("Loading paraphrases...")
    all_paraphrases = load_paraphrases(args.clinical_file, args.patient_file)

    if not all_paraphrases:
        print("Error: No paraphrases loaded. Check file paths.")
        return

    # Create split mapping
    split_mapping = create_split_mapping(all_paraphrases, seed=args.seed)

    # Save results
    save_split_mapping(split_mapping, args.output_file)


if __name__ == "__main__":
    main()
