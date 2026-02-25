#!/usr/bin/env python3
"""
Script to generate paraphrases for question templates using LLMs.

Usage:
    python generate_paraphrases.py [--dry-run] [--resume] [--templates TEMPLATE_IDS] [--max-paraphrases N]

Examples:
    # Generate paraphrases for all templates
    python generate_paraphrases.py

    # Dry run (test without API calls)
    python generate_paraphrases.py --dry-run

    # Resume from existing output file
    python generate_paraphrases.py --resume

    # Generate for specific templates only
    python generate_paraphrases.py --templates "count-drugs-prescribed,has-diagnosis"

    # Customize max paraphrases per template
    python generate_paraphrases.py --max-paraphrases 20
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from dotenv import load_dotenv

load_dotenv()

try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

    # Dummy tqdm for progress tracking
    def tqdm(iterable, *args, **kwargs):
        return iterable


from paraphrasing.config import (
    TEMPLATES_FILE,
    OUTPUT_FILE,
    MAX_PARAPHRASES_PER_TEMPLATE,
    MIN_EDIT_DISTANCE,
    SIMILARITY_THRESHOLD,
)
from paraphrasing.token_masking import mask_template, unmask_template, extract_slots
from paraphrasing.llm_generator import generate_paraphrases_for_template
from paraphrasing.quality_filter import filter_paraphrases, _get_semantic_model

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_templates(file_path: Path) -> Dict[str, str]:
    """Load templates from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_paraphrases(file_path: Path) -> Dict[str, List[str]]:
    """Load existing paraphrases from output file if it exists."""
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse existing paraphrases file: {e}")
            return {}
    return {}


def save_paraphrases(paraphrases: Dict[str, List[str]], file_path: Path) -> None:
    """Save paraphrases to JSON file."""
    # Ensure output directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate structure before saving
    for template_id, template_list in paraphrases.items():
        if not isinstance(template_list, list):
            raise ValueError(
                f"Template {template_id} value is not a list: {type(template_list)}"
            )
        if not template_list:
            raise ValueError(f"Template {template_id} has empty list")
        for item in template_list:
            if not isinstance(item, str):
                raise ValueError(
                    f"Template {template_id} contains non-string: {type(item)}"
                )

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(paraphrases, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved paraphrases to {file_path}")


def validate_output(paraphrases: Dict[str, List[str]]) -> bool:
    """Validate output structure before saving."""
    if not isinstance(paraphrases, dict):
        logger.error("Output is not a dictionary")
        return False

    for template_id, template_list in paraphrases.items():
        if not isinstance(template_list, list):
            logger.error(f"Template {template_id} value is not a list")
            return False
        if not template_list:
            logger.warning(f"Template {template_id} has empty list")
        for item in template_list:
            if not isinstance(item, str):
                logger.error(f"Template {template_id} contains non-string")
                return False

    return True


def process_template(
    template_id: str,
    template: str,
    max_paraphrases: int,
    dry_run: bool = False,
    verbose: bool = False,
    perspective: str = "clinical",
) -> List[str]:
    """
    Process a single template: mask, generate, filter, unmask.

    Returns:
        List of paraphrases (unmasked) including original
    """
    logger.info(f"Processing template: {template_id}")

    if dry_run:
        logger.info(f"[DRY RUN] Would process: {template_id}")
        return [template]  # Return original only in dry run

    try:
        # Step 1: Mask slots
        masked_template, slot_mapping = mask_template(template)
        required_slots = set(slot_mapping.keys())

        logger.debug(f"Masked template: {masked_template}")
        logger.debug(f"Required slots: {required_slots}")

        # Step 2: Generate paraphrases via LLM
        logger.info(f"Generating paraphrases for {template_id}...")
        generated_paraphrases = generate_paraphrases_for_template(
            template_id,
            masked_template,
            required_slots,
            max_paraphrases=max_paraphrases,
            perspective=perspective,
        )

        logger.info(
            f"Generated {len(generated_paraphrases)} raw paraphrases for {template_id}"
        )

        # Step 3: Apply quality filters
        logger.info(
            f"Filtering {len(generated_paraphrases)} paraphrases for {template_id}..."
        )
        filtered_paraphrases, removal_reasons = filter_paraphrases(
            generated_paraphrases,
            masked_template,
            required_slots,
            min_edit_distance=MIN_EDIT_DISTANCE,
            similarity_threshold=SIMILARITY_THRESHOLD,
            verbose=verbose,
            template_id=template_id,
        )

        num_removed = len(generated_paraphrases) - len(filtered_paraphrases)
        if verbose and num_removed > 0:
            logger.info(
                f"Filtered to {len(filtered_paraphrases)} valid paraphrases for {template_id} (removed {num_removed}):"
            )
            for removed_masked, reason in removal_reasons.items():
                # Unmask for readability
                try:
                    removed_unmasked = unmask_template(removed_masked, slot_mapping)
                    logger.info(f"  - REMOVED ({reason}): {removed_unmasked}")
                except Exception:
                    # Fallback to masked if unmasking fails
                    logger.info(f"  - REMOVED ({reason}) [masked]: {removed_masked}")
        else:
            logger.info(
                f"Filtered to {len(filtered_paraphrases)} valid paraphrases for {template_id} (removed {num_removed})"
            )

        # Step 4: Unmask slots
        unmasked_paraphrases = []
        for p in filtered_paraphrases:
            try:
                unmasked = unmask_template(p, slot_mapping)
                unmasked_paraphrases.append(unmasked)
            except Exception as e:
                logger.warning(f"Error unmasking paraphrase for {template_id}: {e}")
                continue

        # Step 5: Include original template as first item
        result = [template] + unmasked_paraphrases

        # Deduplicate (in case original was generated)
        seen = set()
        unique_result = []
        for p in result:
            if p not in seen:
                unique_result.append(p)
                seen.add(p)

        logger.info(f"Final result: {len(unique_result)} paraphrases for {template_id}")
        return unique_result

    except Exception as e:
        logger.error(f"Error processing template {template_id}: {e}", exc_info=True)
        # Return original template only on error
        return [template]


def main():
    """Main function to orchestrate the paraphrase generation pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate paraphrases for question templates using LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test the pipeline without making API calls",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip templates that already exist in output file",
    )

    parser.add_argument(
        "--templates",
        type=str,
        help="Comma-separated list of template IDs to process (default: all)",
    )

    parser.add_argument(
        "--max-paraphrases",
        type=int,
        default=MAX_PARAPHRASES_PER_TEMPLATE,
        help=f"Maximum paraphrases per template (default: {MAX_PARAPHRASES_PER_TEMPLATE})",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging, including detailed filtering information",
    )

    parser.add_argument(
        "--perspective",
        type=str,
        choices=["clinical", "patient"],
        default="clinical",
        help="Perspective for paraphrasing: 'clinical' (default) or 'patient'",
    )

    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Validate file paths
    if not TEMPLATES_FILE.exists():
        logger.error(f"Templates file not found: {TEMPLATES_FILE}")
        sys.exit(1)

    # Load templates
    logger.info(f"Loading templates from {TEMPLATES_FILE}")
    all_templates = load_templates(TEMPLATES_FILE)
    logger.info(f"Loaded {len(all_templates)} templates")

    # Filter templates if specified
    template_ids_to_process: Optional[Set[str]] = None
    if args.templates:
        template_ids_to_process = set(
            tid.strip() for tid in args.templates.split(",") if tid.strip()
        )
        # Validate all specified templates exist
        invalid = template_ids_to_process - set(all_templates.keys())
        if invalid:
            logger.error(f"Invalid template IDs: {invalid}")
            sys.exit(1)
        logger.info(f"Processing {len(template_ids_to_process)} specified templates")

    # Load existing paraphrases if resuming
    existing_paraphrases: Dict[str, List[str]] = {}
    if args.resume and OUTPUT_FILE.exists():
        logger.info(f"Loading existing paraphrases from {OUTPUT_FILE}")
        existing_paraphrases = load_existing_paraphrases(OUTPUT_FILE)
        logger.info(f"Found {len(existing_paraphrases)} existing templates")

    # Initialize semantic model (for quality filtering)
    if not args.dry_run:
        logger.info("Loading semantic similarity model...")
        try:
            _get_semantic_model()
            logger.info("Semantic model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            sys.exit(1)

    # Process templates
    results: Dict[str, List[str]] = {}

    # Start with existing paraphrases if resuming
    if args.resume:
        results.update(existing_paraphrases)

    # Determine which templates to process
    templates_to_process = {
        tid: template
        for tid, template in all_templates.items()
        if (template_ids_to_process is None or tid in template_ids_to_process)
        and (not args.resume or tid not in existing_paraphrases)
    }

    if not templates_to_process:
        logger.info("No templates to process")
        return

    logger.info(f"Processing {len(templates_to_process)} templates")

    # Process with progress bar if available
    iterator = (
        tqdm(templates_to_process.items(), desc="Generating paraphrases")
        if HAS_TQDM
        else templates_to_process.items()
    )

    for template_id, template in iterator:
        paraphrases = process_template(
            template_id,
            template,
            args.max_paraphrases,
            dry_run=args.dry_run,
            verbose=args.verbose,
            perspective=args.perspective,
        )
        results[template_id] = paraphrases

        # Save incrementally (after each template) to avoid losing work on failure
        if not args.dry_run:
            try:
                save_paraphrases(results, OUTPUT_FILE)
            except Exception as e:
                logger.error(f"Error saving intermediate results: {e}")

    # Final validation
    if not validate_output(results):
        logger.error("Output validation failed")
        sys.exit(1)

    # Save final results
    if not args.dry_run:
        save_paraphrases(results, OUTPUT_FILE)
        logger.info("Pipeline complete!")

        # Print summary statistics
        total_paraphrases = sum(len(paraphrases) for paraphrases in results.values())
        avg_paraphrases = total_paraphrases / len(results) if results else 0
        logger.info(
            f"Summary: {len(results)} templates, {total_paraphrases} total paraphrases, {avg_paraphrases:.1f} average per template"
        )
    else:
        logger.info("[DRY RUN] Pipeline test complete (no API calls made)")


if __name__ == "__main__":
    main()
