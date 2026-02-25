#!/usr/bin/env python3
"""
Filter a .jsonl dataset by:
  1. Keeping only entries whose paraphrase split is in --splits (train, val, test).
     Split is determined from paraphrase_splits.json. Entries with split 'unknown' are dropped unless 'unknown' is in --splits.
  2. Excluding all questions whose question_template_id is in --exclude-template-ids

Usage:
    python filter_dataset.py [--input-file FILE] [--output-file FILE]
        [--splits train,val,...] [--exclude-template-ids ID1,ID2,...]

Defaults (same as add_splits_to_dataset.py):
    --input-file: output/fhirpath-qa-large.jsonl
    --output-file: output/filtered-dataset.jsonl
    --splits: train,val (i.e. exclude test and unknown)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Set

# Reuse paraphrase split logic from add_splits_to_dataset
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_splits_to_dataset import (
    determine_split_from_template,
    load_paraphrase_splits,
)

VALID_SPLITS = {"train", "val", "test", "unknown"}


def filter_dataset(
    input_file: str,
    output_file: str,
    allow_splits: Set[str],
    exclude_template_ids: Set[str],
) -> None:
    """Filter dataset: keep only allowed splits and exclude specified template_ids."""

    print("Loading paraphrase splits...")
    splits = load_paraphrase_splits()

    print(f"Keeping splits: {sorted(allow_splits)}")
    if exclude_template_ids:
        print(f"Excluding template_ids: {sorted(exclude_template_ids)}")

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

    n_before = len(entries)
    print(f"Loaded {n_before} entries")

    filtered = []
    removed_split = 0
    removed_template_id = 0
    for entry in entries:
        template_id = entry.get("question_template_id", "")
        question_template = entry.get("question_template", "")

        # Remove if paraphrase split is not in allowed splits
        split = determine_split_from_template(question_template, template_id, splits)
        if split not in allow_splits:
            removed_split += 1
            continue

        # Remove if template_id is in exclude list
        if template_id in exclude_template_ids:
            removed_template_id += 1
            continue

        filtered.append(entry)

    n_after = len(filtered)
    print(f"Removed {removed_split} entries (split not in {sorted(allow_splits)})")
    print(f"Removed {removed_template_id} entries (excluded template_id)")
    print(f"Keeping {n_after} entries")

    print(f"Writing filtered dataset to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in filtered:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Done. Wrote {n_after} entries to {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filter dataset by allowed splits (train/val/test) and excluded template_ids"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="output/fhirpath-qa-large.jsonl",
        help="Path to input dataset (default: output/fhirpath-qa-large.jsonl)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="output/filtered-dataset.jsonl",
        help="Path to output dataset (default: output/filtered-dataset.jsonl)",
    )
    parser.add_argument(
        "--splits",
        type=str,
        default="train,val",
        metavar="SPLIT1,SPLIT2,...",
        help="Comma-separated splits to keep: train, val, test, unknown (default: train,val)",
    )
    parser.add_argument(
        "--exclude-template-ids",
        type=str,
        default=None,
        metavar="ID1,ID2,...",
        help="Comma-separated template_ids to exclude (all questions from these templates are removed)",
    )

    args = parser.parse_args()

    allow_splits = {s.strip().lower() for s in args.splits.split(",") if s.strip()}
    invalid = allow_splits - VALID_SPLITS
    if invalid:
        print(f"Error: Invalid split(s): {invalid}. Allowed: {VALID_SPLITS}")
        sys.exit(1)

    exclude_ids = set()
    if args.exclude_template_ids:
        exclude_ids = {tid.strip() for tid in args.exclude_template_ids.split(",") if tid.strip()}

    input_path = Path(args.input_file)
    output_path = Path(args.output_file) if args.output_file else input_path

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    filter_dataset(str(input_path), str(output_path), allow_splits, exclude_ids)


if __name__ == "__main__":
    main()
