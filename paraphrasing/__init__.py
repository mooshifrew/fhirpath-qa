"""Paraphrasing module for generating template variations."""

from .token_masking import mask_template, unmask_template, extract_slots
from .llm_generator import generate_paraphrases_for_template
from .quality_filter import filter_paraphrases

__all__ = [
    "mask_template",
    "unmask_template",
    "extract_slots",
    "generate_paraphrases_for_template",
    "filter_paraphrases",
]
