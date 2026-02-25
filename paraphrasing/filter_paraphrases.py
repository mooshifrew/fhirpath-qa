#!/usr/bin/env python3
"""
Script to filter paraphrases from a CSV file based on manual review.

Reads a CSV with columns: template_id, question_template, paraphrase, good
- Calculates and prints the rejection rate
- Outputs a JSON file with only the accepted paraphrases (marked 'y')
"""

import argparse
import csv
import json
from collections import defaultdict


def main():
    parser = argparse.ArgumentParser(
        description="Filter paraphrases based on manual review and output to JSON"
    )
    parser.add_argument("--input", help="Input CSV file with paraphrase reviews")
    parser.add_argument("--output", help="Output JSON file for accepted paraphrases")
    args = parser.parse_args()

    # Read the CSV and collect statistics
    accepted_paraphrases = defaultdict(list)
    total_count = 0
    rejected_count = 0

    with open(args.input, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_count += 1
            template_id = row["template_id"]
            paraphrase = row["paraphrase"]
            good = row["good"].strip().lower()

            if good == "y":
                accepted_paraphrases[template_id].append(paraphrase)
            elif good == "n":
                rejected_count += 1
            else:
                print(
                    f"Warning: Unknown value '{row['good']}' for template {template_id}"
                )

    # Calculate and print rejection statistics
    if total_count > 0:
        rejection_rate = (rejected_count / total_count) * 100
        accepted_count = total_count - rejected_count
        print(f"Total paraphrases: {total_count}")
        print(f"Rejected: {rejected_count} ({rejection_rate:.2f}%)")
        print(f"Accepted: {accepted_count} ({100 - rejection_rate:.2f}%)")
    else:
        print("No entries found in CSV file.")
        return

    # Write accepted paraphrases to JSON
    # Sort keys for consistent output
    output_dict = dict(sorted(accepted_paraphrases.items()))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2)

    print(f"\nOutput written to: {args.output}")
    print(f"Number of templates with accepted paraphrases: {len(output_dict)}")


if __name__ == "__main__":
    main()
