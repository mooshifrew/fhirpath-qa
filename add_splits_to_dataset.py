#!/usr/bin/env python3
"""
Script to add 'split' and 'holdout' keys to a .jsonl dataset based on question templates and paraphrases.

- split: from paraphrase_splits.json (train/val/test/unknown)
- holdout: 0 (default), 1 (template in --holdout1-template-ids), or 2 (template in --holdout2-template-ids)

Usage:
    python add_splits_to_dataset.py [--input-file FILE] [--output-file FILE]
        [--holdout1-template-ids ID1,ID2,...] [--holdout2-template-ids ID1,ID2,...]

Defaults:
    --input-file: output/dataset_evaluated.jsonl
    --output-file: output/dataset_evaluated.jsonl (overwrites input)
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Set

# Add the fhirpath_gen module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "fhirpath_gen"))

# Import template registry to get default templates
import fhirpath_gen
from fhirpath_gen.base import template_registry


def load_paraphrase_splits(
    split_file: str = "paraphrasing/paraphrase_splits.json",
) -> Dict[str, Dict[str, str]]:
    """
    Load paraphrase split mapping.

    Returns:
        Dictionary mapping template_id to {paraphrase_text: 'train'|'val'|'test'}
    """
    split_path = Path(split_file)
    if not split_path.exists():
        print(f"Warning: Split file not found: {split_file}")
        return {}

    with open(split_path, "r", encoding="utf-8") as f:
        return json.load(f)


def determine_split_from_template(
    question_template: str, template_id: str, splits: Dict[str, Dict[str, str]]
) -> str:
    """
    Determine the split for a question based on its template text.

    Args:
        question_template: The question template text
        template_id: The template ID
        splits: The paraphrase splits mapping

    Returns:
        'train', 'val', 'test', or 'unknown'
    """
    if template_id not in splits:
        return "unknown"

    template_splits = splits[template_id]
    # Try exact match first
    if question_template in template_splits:
        return template_splits[question_template]

    # If not found, return 'unknown'
    return "unknown"


def determine_holdout(
    template_id: str,
    holdout1_template_ids: Set[str],
    holdout2_template_ids: Set[str],
) -> int:
    """
    Determine holdout value for an entry based on template_id.

    Returns:
        1 if template_id is in holdout1_template_ids,
        2 if template_id is in holdout2_template_ids,
        0 otherwise.
    """
    if template_id in holdout1_template_ids:
        return 1
    if template_id in holdout2_template_ids:
        return 2
    return 0


def add_splits_to_dataset(
    input_file: str,
    output_file: str,
    holdout1_template_ids: Set[str] | None = None,
    holdout2_template_ids: Set[str] | None = None,
):
    """Add 'split' and 'holdout' keys to each entry in the dataset."""

    holdout1_ids = holdout1_template_ids or set()
    holdout2_ids = holdout2_template_ids or set()

    # Load paraphrase splits
    print("Loading paraphrase splits...")
    splits = load_paraphrase_splits()

    if holdout1_ids or holdout2_ids:
        print(f"Holdout1 template_ids: {len(holdout1_ids)} -> holdout=1")
        print(f"Holdout2 template_ids: {len(holdout2_ids)} -> holdout=2")

    # Load dataset
    print(f"Loading dataset from {input_file}...")
    entries = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {line_num}: {e}")
                    continue

    print(f"Loaded {len(entries)} entries")

    # Process each entry and add split
    print("Determining splits for each entry...")
    unknown_count = 0
    for entry in entries:
        template_id = entry.get("question_template_id", "")
        question_template = entry.get("question_template", "")

        # Determine holdout from template_id (0, 1, or 2)
        holdout = determine_holdout(template_id, holdout1_ids, holdout2_ids)

        if (
            holdout == 1 or holdout == 2
        ):  # just want to run the test on everything with the test flag
            split = "test"
        else:
            # Determine split from template
            split = determine_split_from_template(
                question_template, template_id, splits
            )

        # Add split and holdout to entry
        entry["split"] = split
        entry["holdout"] = holdout

        if split == "unknown":
            unknown_count += 1

    if unknown_count > 0:
        print(
            f"Warning: {unknown_count} entries could not be assigned a split (marked as 'unknown')"
        )

    # Write back to file
    print(f"Writing updated dataset to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in entries:
            json_line = json.dumps(entry, ensure_ascii=False)
            f.write(json_line + "\n")

    # Print statistics
    split_counts = {}
    for entry in entries:
        split = entry.get("split", "unknown")
        split_counts[split] = split_counts.get(split, 0) + 1

    print("\nSplit distribution:")
    for split in sorted(split_counts.keys()):
        print(f"  {split}: {split_counts[split]}")

    holdout_counts = {}
    for entry in entries:
        h = entry.get("holdout", 0)
        holdout_counts[h] = holdout_counts.get(h, 0) + 1
    print("\nHoldout distribution:")
    for h in sorted(holdout_counts.keys()):
        print(f"  {h}: {holdout_counts[h]}")

    print(f"\nSuccessfully added splits and holdout to {len(entries)} entries")


def main():
    parser = argparse.ArgumentParser(
        description="Add 'split' key to dataset_evaluated.jsonl"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="output/dataset_evaluated.jsonl",
        help="Path to input dataset file (default: output/dataset_evaluated.jsonl)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="output/dataset_evaluated_with_splits.jsonl",
        help="Path to output dataset file (default: overwrites input file)",
    )
    parser.add_argument(
        "--holdout1-template-ids",
        type=str,
        default="count-drugs-prescribed,has-hospital-admission,time-drug-route,procedure-name",
        metavar="ID1,ID2,...",
        help="Comma-separated template_ids for holdout=1",
    )
    parser.add_argument(
        "--holdout2-template-ids",
        type=str,
        default="careunit,count-input-intake-events,has-input-intake,time-intake,time-specific-intake",
        metavar="ID1,ID2,...",
        help="Comma-separated template_ids for holdout=2",
    )

    args = parser.parse_args()

    def parse_ids(s: str | None) -> Set[str]:
        if not s:
            return set()
        return {tid.strip() for tid in s.split(",") if tid.strip()}

    holdout1_ids = parse_ids(args.holdout1_template_ids)
    holdout2_ids = parse_ids(args.holdout2_template_ids)

    # Convert to absolute paths
    input_path = Path(args.input_file)
    output_path = Path(args.output_file) if args.output_file else input_path

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return

    add_splits_to_dataset(
        str(input_path),
        str(output_path),
        holdout1_template_ids=holdout1_ids,
        holdout2_template_ids=holdout2_ids,
    )


if __name__ == "__main__":
    main()
