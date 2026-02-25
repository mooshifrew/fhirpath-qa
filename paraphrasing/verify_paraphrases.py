"""Verification script to generate CSV samples and analyze paraphrase metrics."""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path to allow imports when run as script
if __name__ == "__main__":
    script_dir = Path(__file__).parent
    parent_dir = script_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

import Levenshtein
import numpy as np
from sentence_transformers import SentenceTransformer

from paraphrasing.config import OUTPUT_FILE, SEMANTIC_MODEL_NAME


# Global model cache
_semantic_model: SentenceTransformer = None


def _get_semantic_model() -> SentenceTransformer:
    """Get or initialize the semantic similarity model."""
    global _semantic_model
    if _semantic_model is None:
        print("Loading semantic similarity model...")
        _semantic_model = SentenceTransformer(SEMANTIC_MODEL_NAME)
        print("Model loaded successfully")
    return _semantic_model


def compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity between two texts using sentence embeddings.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Cosine similarity score (0.0-1.0)
    """
    model = _get_semantic_model()
    embeddings = model.encode([text1, text2])
    similarity = np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    )
    return float(similarity)


def compute_normalized_edit_distance(text1: str, text2: str) -> float:
    """
    Compute normalized edit distance between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Normalized edit distance (0.0-1.0), where 0.0 = identical, 1.0 = completely different
    """
    distance = Levenshtein.distance(text1, text2)
    max_len = max(len(text1), len(text2))
    if max_len == 0:
        return 0.0
    return distance / max_len


def analyze_paraphrases(paraphrases: Dict[str, List[str]]) -> Tuple[Dict, Dict]:
    """
    Analyze all paraphrases and compute metrics.

    Args:
        paraphrases: Dictionary mapping template_id to list of paraphrases (first is original)

    Returns:
        Tuple of (overall_stats, per_template_stats) where each contains:
        - semantic_similarity: list of scores
        - normalized_edit_distance: list of scores
        - counts: number of paraphrases analyzed
    """
    overall_semantic_scores = []
    overall_edit_distances = []

    per_template_stats: Dict[str, Dict] = defaultdict(
        lambda: {"semantic_similarity": [], "normalized_edit_distance": [], "count": 0}
    )

    print("\nAnalyzing paraphrases...")
    total_paraphrases = 0

    for template_id, template_list in paraphrases.items():
        if len(template_list) < 2:
            continue  # Skip templates with no paraphrases

        original = template_list[0]  # First item is always original

        for paraphrase in template_list[1:]:  # Skip original
            # Compute semantic similarity
            semantic_score = compute_semantic_similarity(original, paraphrase)
            overall_semantic_scores.append(semantic_score)
            per_template_stats[template_id]["semantic_similarity"].append(
                semantic_score
            )

            # Compute normalized edit distance
            edit_distance = compute_normalized_edit_distance(original, paraphrase)
            overall_edit_distances.append(edit_distance)
            per_template_stats[template_id]["normalized_edit_distance"].append(
                edit_distance
            )

            per_template_stats[template_id]["count"] += 1
            total_paraphrases += 1

        if total_paraphrases % 100 == 0:
            print(f"  Processed {total_paraphrases} paraphrases...")

    print(
        f"Analyzed {total_paraphrases} paraphrases across {len(per_template_stats)} templates\n"
    )

    overall_stats = {
        "semantic_similarity": overall_semantic_scores,
        "normalized_edit_distance": overall_edit_distances,
        "count": total_paraphrases,
    }

    return overall_stats, dict(per_template_stats)


def compute_statistics(scores: List[float]) -> Dict[str, float]:
    """
    Compute mean and standard deviation for a list of scores.

    Args:
        scores: List of numeric scores

    Returns:
        Dictionary with 'mean' and 'std' keys
    """
    if not scores:
        return {"mean": 0.0, "std": 0.0}
    scores_array = np.array(scores)
    return {
        "mean": float(np.mean(scores_array)),
        "std": float(np.std(scores_array)),
    }


def print_statistics(overall_stats: Dict, per_template_stats: Dict) -> None:
    """
    Print statistics for overall dataset and per template.

    Args:
        overall_stats: Overall statistics dictionary
        per_template_stats: Per-template statistics dictionary
    """
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)

    semantic_stats = compute_statistics(overall_stats["semantic_similarity"])
    edit_stats = compute_statistics(overall_stats["normalized_edit_distance"])

    print(f"\nTotal paraphrases analyzed: {overall_stats['count']}")
    print(f"\nSemantic Similarity:")
    print(f"  Mean: {semantic_stats['mean']:.4f}")
    print(f"  Std:  {semantic_stats['std']:.4f}")
    print(f"  Min:  {min(overall_stats['semantic_similarity']):.4f}")
    print(f"  Max:  {max(overall_stats['semantic_similarity']):.4f}")

    print(f"\nNormalized Edit Distance:")
    print(f"  Mean: {edit_stats['mean']:.4f}")
    print(f"  Std:  {edit_stats['std']:.4f}")
    print(f"  Min:  {min(overall_stats['normalized_edit_distance']):.4f}")
    print(f"  Max:  {max(overall_stats['normalized_edit_distance']):.4f}")

    print("\n" + "=" * 80)
    print("PER-TEMPLATE STATISTICS")
    print("=" * 80)

    # Sort templates by count (descending)
    sorted_templates = sorted(
        per_template_stats.items(), key=lambda x: x[1]["count"], reverse=True
    )

    for template_id, stats in sorted_templates:
        semantic_stats_template = compute_statistics(stats["semantic_similarity"])
        edit_stats_template = compute_statistics(stats["normalized_edit_distance"])

        print(f"\nTemplate: {template_id} ({stats['count']} paraphrases)")
        print(
            f"  Semantic Similarity:     mean={semantic_stats_template['mean']:.4f}, std={semantic_stats_template['std']:.4f}"
        )
        print(
            f"  Normalized Edit Distance: mean={edit_stats_template['mean']:.4f}, std={edit_stats_template['std']:.4f}"
        )


def load_paraphrases(file_path: Path) -> Dict[str, List[str]]:
    """Load paraphrases from JSON file."""
    if not file_path.exists():
        print(f"Error: Paraphrases file not found: {file_path}")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_paraphrase_pairs(
    paraphrases: Dict[str, List[str]],
) -> List[Tuple[str, str, str]]:
    """
    Get all (template_id, original, paraphrase) pairs.

    Args:
        paraphrases: Dictionary mapping template_id to list of paraphrases

    Returns:
        List of (template_id, question_template, paraphrase) tuples
    """
    all_pairs = []
    for template_id, template_list in paraphrases.items():
        if len(template_list) < 2:
            continue  # Skip templates with no paraphrases (only original)

        original = template_list[0]  # First item is always original
        for paraphrase in template_list[1:]:  # Skip original
            all_pairs.append((template_id, original, paraphrase))

    return all_pairs


def write_csv(pairs: List[Tuple[str, str, str]], output_path: Path) -> None:
    """Write all paraphrase pairs to CSV file."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["template_id", "question_template", "paraphrase"])
        writer.writerows(pairs)

    print(f"Saved {len(pairs)} paraphrase pairs to {output_path}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Analyze paraphrase metrics and generate CSV samples for manual review",
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=OUTPUT_FILE,
        help=f"Input paraphrases JSON file (default: {OUTPUT_FILE})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output") / "paraphrase_samples.csv",
        help="Output CSV file (default: output/paraphrase_samples.csv)",
    )

    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only run analysis, skip CSV generation",
    )

    args = parser.parse_args()

    # Load paraphrases
    print(f"Loading paraphrases from {args.input}")
    paraphrases = load_paraphrases(args.input)
    print(f"Loaded {len(paraphrases)} templates")

    # Analyze all paraphrases
    overall_stats, per_template_stats = analyze_paraphrases(paraphrases)

    # Print statistics
    print_statistics(overall_stats, per_template_stats)

    # Generate CSV with all paraphrases if not analyze-only
    if not args.analyze_only:
        print("\n" + "=" * 80)
        print("GENERATING CSV WITH ALL PARAPHRASES")
        print("=" * 80)

        # Get all pairs
        print(f"\nCollecting all paraphrase pairs...")
        all_pairs = get_all_paraphrase_pairs(paraphrases)
        print(f"Found {len(all_pairs)} paraphrase pairs")

        # Ensure output directory exists
        args.output.parent.mkdir(parents=True, exist_ok=True)

        # Write CSV
        write_csv(all_pairs, args.output)

    print("\nDone!")


if __name__ == "__main__":
    main()
