"""Quality control filters for paraphrases."""

import logging
from typing import List, Set, Optional
import Levenshtein
from sentence_transformers import SentenceTransformer
import numpy as np

from .config import (
    SIMILARITY_THRESHOLD,
    MIN_EDIT_DISTANCE,
    MIN_NORMALIZED_DISTANCE,
    SEMANTIC_MODEL_NAME,
)

logger = logging.getLogger(__name__)

# Global model cache (loaded once)
_semantic_model: SentenceTransformer = None


def _get_semantic_model() -> SentenceTransformer:
    """Get or initialize the semantic similarity model."""
    global _semantic_model
    if _semantic_model is None:
        _semantic_model = SentenceTransformer(SEMANTIC_MODEL_NAME)
    return _semantic_model


def check_slot_integrity(
    paraphrase: str, required_slots: Set[str], verbose: bool = False
) -> tuple[bool, Optional[str]]:
    """
    Verify all required slots are present in the paraphrase.

    Args:
        paraphrase: Generated paraphrase (may be masked)
        required_slots: Set of required masked slot tokens (e.g., {"X_PATIENT_ID_X"})
        verbose: If True, return reason string for failures

    Returns:
        Tuple of (is_valid, reason) where reason is None if valid, or explanation if invalid
    """
    from .token_masking import extract_masked_slots

    found_slots = extract_masked_slots(paraphrase)
    if found_slots == required_slots:
        return True, None

    missing = required_slots - found_slots
    extra = found_slots - required_slots
    reason_parts = []
    if missing:
        reason_parts.append(f"missing slots: {sorted(missing)}")
    if extra:
        reason_parts.append(f"extra slots: {sorted(extra)}")
    reason = "; ".join(reason_parts)
    return False, reason


def is_sufficiently_different(
    text1: str,
    text2: str,
    min_edit_distance: int = MIN_EDIT_DISTANCE,
    min_normalized_distance: float = MIN_NORMALIZED_DISTANCE,
    verbose: bool = False,
) -> tuple[bool, Optional[str]]:
    """
    Check if two texts are sufficiently different.

    Args:
        text1: First text to compare
        text2: Second text to compare
        min_edit_distance: Minimum absolute edit distance required
        min_normalized_distance: Minimum normalized edit distance required (0.0-1.0)
        verbose: If True, return reason string for failures

    Returns:
        Tuple of (is_different, reason) where reason is None if different, or explanation if too similar
    """
    distance = Levenshtein.distance(text1, text2)

    # Check absolute distance
    if distance < min_edit_distance:
        if verbose:
            return False, f"edit distance too low: {distance} < {min_edit_distance}"
        return False, None

    # Check normalized distance
    max_len = max(len(text1), len(text2))
    if max_len == 0:
        return False, "empty text" if verbose else None

    normalized = distance / max_len
    if normalized < min_normalized_distance:
        if verbose:
            return (
                False,
                f"normalized distance too low: {normalized:.3f} < {min_normalized_distance}",
            )
        return False, None

    return True, None


def deduplicate_paraphrases(
    paraphrases: List[str],
    original: str,
    min_edit_distance: int = MIN_EDIT_DISTANCE,
    verbose: bool = False,
    template_id: Optional[str] = None,
) -> tuple[List[str], List[tuple[str, str]]]:
    """
    Remove duplicates and near-duplicates from paraphrases.

    Also removes paraphrases too similar to the original.

    Args:
        paraphrases: List of paraphrases to deduplicate
        original: Original template to compare against
        min_edit_distance: Minimum edit distance required
        verbose: If True, return list of filtered items with reasons
        template_id: Template ID for logging

    Returns:
        Tuple of (deduplicated_list, filtered_items) where filtered_items is list of (paraphrase, reason) tuples
    """
    if not paraphrases:
        return [], []

    filtered_out = []

    # Filter out paraphrases too similar to original
    filtered = []
    for p in paraphrases:
        is_diff, reason = is_sufficiently_different(
            p, original, min_edit_distance, MIN_NORMALIZED_DISTANCE, verbose=True
        )
        if is_diff:
            filtered.append(p)
        else:
            filtered_out.append(
                (p, f"too similar to original: {reason or 'edit distance too low'}")
            )

    # Deduplicate within the list
    unique = []
    for paraphrase in filtered:
        is_unique = True
        duplicate_of = None
        for existing in unique:
            is_diff, reason = is_sufficiently_different(
                paraphrase,
                existing,
                min_edit_distance,
                MIN_NORMALIZED_DISTANCE,
                verbose=True,
            )
            if not is_diff:
                is_unique = False
                duplicate_of = existing
                filtered_out.append(
                    (
                        paraphrase,
                        f"duplicate of existing paraphrase: {reason or 'edit distance too low'}",
                    )
                )
                break
        if is_unique:
            unique.append(paraphrase)

    return unique, filtered_out


def check_semantic_similarity(
    original: str,
    paraphrase: str,
    threshold: float = SIMILARITY_THRESHOLD,
    verbose: bool = False,
) -> tuple[bool, Optional[float]]:
    """
    Verify semantic similarity using sentence embeddings.

    Args:
        original: Original template
        paraphrase: Generated paraphrase
        threshold: Minimum cosine similarity required (0.0-1.0)
        verbose: If True, return similarity score

    Returns:
        Tuple of (is_similar, similarity_score) where similarity_score is None if not verbose or invalid
    """
    model = _get_semantic_model()

    # Compute embeddings
    embeddings = model.encode([original, paraphrase])

    # Compute cosine similarity
    similarity = np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    )

    is_similar = similarity >= threshold
    return is_similar, similarity if verbose else None


def filter_paraphrases(
    paraphrases: List[str],
    original_masked: str,
    required_slots: Set[str],
    min_edit_distance: int = MIN_EDIT_DISTANCE,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    verbose: bool = False,
    template_id: Optional[str] = None,
) -> tuple[List[str], dict[str, str]]:
    """
    Apply all quality filters in sequence.

    Filters applied:
    1. Slot integrity check
    2. Deduplication (against original and each other)
    3. Semantic similarity check

    Args:
        paraphrases: List of generated paraphrases (masked)
        original_masked: Original template (masked)
        required_slots: Set of required masked slot tokens
        min_edit_distance: Minimum edit distance for deduplication
        similarity_threshold: Minimum semantic similarity
        verbose: If True, log detailed filtering information
        template_id: Template ID for logging

    Returns:
        Tuple of (filtered_list, removal_reasons) where removal_reasons maps
        removed paraphrase -> reason string
    """
    if verbose:
        logger.debug(
            f"[{template_id}] Starting filter with {len(paraphrases)} paraphrases"
        )

    # Track removal reasons for all removed paraphrases
    removal_reasons: dict[str, str] = {}

    # Step 1: Slot integrity check
    valid_slots = []
    slot_filtered = []
    for p in paraphrases:
        is_valid, reason = check_slot_integrity(p, required_slots, verbose=True)
        if is_valid:
            valid_slots.append(p)
        else:
            removal_reasons[p] = f"slot integrity: {reason or 'missing/extra slots'}"
            if verbose:
                slot_filtered.append((p, reason))
                logger.debug(
                    f"[{template_id}] FILTERED (slot integrity): {p[:80]}... | Reason: {reason}"
                )

    if verbose:
        logger.debug(
            f"[{template_id}] Slot integrity: {len(valid_slots)}/{len(paraphrases)} passed ({len(slot_filtered)} filtered)"
        )

    # Step 2: Deduplication
    unique, dedup_filtered = deduplicate_paraphrases(
        valid_slots,
        original_masked,
        min_edit_distance,
        verbose=verbose,
        template_id=template_id,
    )

    # Add deduplication removal reasons
    for p, reason in dedup_filtered:
        removal_reasons[p] = f"deduplication: {reason}"
        if verbose:
            logger.debug(
                f"[{template_id}] FILTERED (deduplication): {p[:80]}... | Reason: {reason}"
            )

    if verbose:
        logger.debug(
            f"[{template_id}] Deduplication: {len(unique)}/{len(valid_slots)} passed ({len(dedup_filtered)} filtered)"
        )

    # Step 3: Semantic similarity check
    semantically_similar = []
    similarity_filtered = []
    for p in unique:
        is_similar, score = check_semantic_similarity(
            original_masked, p, similarity_threshold, verbose=True
        )
        if is_similar:
            semantically_similar.append(p)
            if verbose and score is not None:
                logger.debug(
                    f"[{template_id}] KEPT (semantic): similarity={score:.3f} | {p[:80]}..."
                )
        else:
            removal_reasons[p] = (
                f"semantic similarity: {score:.3f} < {similarity_threshold}"
                if score is not None
                else f"semantic similarity: < {similarity_threshold}"
            )
            if verbose:
                similarity_filtered.append((p, score))
                logger.debug(
                    f"[{template_id}] FILTERED (semantic similarity): similarity={score:.3f} < {similarity_threshold} | {p[:80]}..."
                )

    if verbose:
        logger.debug(
            f"[{template_id}] Semantic similarity: {len(semantically_similar)}/{len(unique)} passed ({len(similarity_filtered)} filtered)"
        )
        total_filtered = (
            len(slot_filtered) + len(dedup_filtered) + len(similarity_filtered)
        )
        logger.debug(
            f"[{template_id}] Final: {len(semantically_similar)}/{len(paraphrases)} paraphrases passed ({total_filtered} total filtered)"
        )

    return semantically_similar, removal_reasons
