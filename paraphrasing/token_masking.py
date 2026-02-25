"""Token masking utilities for preserving slots during LLM generation."""

import re
from typing import Dict, Set, Tuple


def extract_slots(template: str) -> Set[str]:
    """
    Extract all slot names from a template.

    Extracts both {name} and [name] patterns, as well as the special Has_verb token.

    Args:
        template: Template string with slots

    Returns:
        Set of slot names found in the template
    """
    slots = set()

    # Extract {name} placeholders
    curly_pattern = r"\{([a-z_0-9]+)\}"
    for match in re.finditer(curly_pattern, template):
        slots.add(f"{{{match.group(1)}}}")

    # Extract [name] placeholders
    bracket_pattern = r"\[([a-z_0-9]+)\]"
    for match in re.finditer(bracket_pattern, template):
        slots.add(f"[{match.group(1)}]")

    # Check for Has_verb token
    # if "Has_verb" in template:
    #     slots.add("Has_verb")

    return slots


def mask_template(template: str) -> Tuple[str, Dict[str, str]]:
    """
    Mask slots in a template to make them LLM-friendly.

    Converts {name} -> X_NAME_X and [name] -> X_NAME_X format.
    Also masks Has_verb -> X_HAS_VERB_X.

    Args:
        template: Original template with slots

    Returns:
        Tuple of (masked_template, slot_mapping) where slot_mapping
        maps masked tokens back to original slot names
    """
    masked = template
    slot_mapping: Dict[str, str] = {}

    # Mask {name} placeholders
    curly_pattern = r"\{([a-z_0-9]+)\}"
    for match in re.finditer(curly_pattern, template):
        original_slot = match.group(0)  # e.g., "{patient_id}"
        slot_name = match.group(1).upper()  # e.g., "PATIENT_ID"
        masked_token = f"X_{slot_name}_X"
        masked = masked.replace(original_slot, masked_token, 1)
        slot_mapping[masked_token] = original_slot

    # Mask [name] placeholders
    bracket_pattern = r"\[([a-z_0-9]+)\]"
    # Need to process in reverse to avoid index issues when replacing
    matches = list(re.finditer(bracket_pattern, masked))
    for match in reversed(matches):
        original_slot = match.group(0)  # e.g., "[time_filter_global1]"
        slot_name = match.group(1).upper()  # e.g., "TIME_FILTER_GLOBAL1"
        masked_token = f"X_{slot_name}_X"
        masked = masked[: match.start()] + masked_token + masked[match.end() :]
        slot_mapping[masked_token] = original_slot

    # Mask Has_verb token
    # if "Has_verb" in masked:
    #     masked_token = "X_HAS_VERB_X"
    #     masked = masked.replace("Has_verb", masked_token)
    #     slot_mapping[masked_token] = "Has_verb"

    return masked, slot_mapping


def unmask_template(masked_template: str, slot_mapping: Dict[str, str]) -> str:
    """
    Restore original slots from a masked template.

    Args:
        masked_template: Template with masked tokens (X_NAME_X format)
        slot_mapping: Dictionary mapping masked tokens to original slot names

    Returns:
        Template with original slot names restored
    """
    unmasked = masked_template

    # Replace masked tokens with original slots
    # Sort by length (longest first) to avoid partial replacements
    sorted_mappings = sorted(
        slot_mapping.items(), key=lambda x: len(x[0]), reverse=True
    )

    for masked_token, original_slot in sorted_mappings:
        unmasked = unmasked.replace(masked_token, original_slot)

    return unmasked


def extract_masked_slots(masked_template: str) -> Set[str]:
    """
    Extract masked slot tokens from a masked template.

    Args:
        masked_template: Template with masked tokens (X_NAME_X format)

    Returns:
        Set of masked slot tokens found in the template
    """
    pattern = r"X_[A-Z0-9_]+_X"
    return set(re.findall(pattern, masked_template))
