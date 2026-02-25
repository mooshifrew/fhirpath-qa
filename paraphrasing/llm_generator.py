import json
import os
import time
import logging
from typing import List, Set
from openai import OpenAI
from pydantic import BaseModel, Field

from .config import (
    MODEL,
    TEMPERATURE,
    BATCH_SIZE,
    MAX_RETRIES,
    MAX_PARAPHRASES_PER_TEMPLATE,
)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
_client: OpenAI = None


class ParaphraseResponse(BaseModel):
    """
    Pydantic model for structured paraphrase generation response.

    Used with OpenAI's structured outputs feature (beta.parse API) to ensure
    type-safe, validated responses without manual JSON parsing.
    """

    paraphrases: List[str] = Field(
        ...,
        description="List of paraphrased question templates with masked slots preserved",
        min_length=1,
    )


def _get_client() -> OpenAI:
    """Get or initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = OpenAI(api_key=api_key)
    return _client


def _create_system_prompt(perspective: str) -> str:
    """Create the system prompt for paraphrase generation."""
    if perspective == "patient":
        return """ROLE: You are a patient or a family caregiver asking questions about your own health records (or a family member's). Your task is to paraphrase clinical query templates into natural, "consumer-health" language while strictly maintaining the logic slots.

OBJECTIVE:
Generate high-quality paraphrases of the rigid clinical template that reflect the way a real person would speak about themself/someone they are caring for. Use pronouns like I/my/his/hers.

CRITICAL SLOT RULES:
1. EXACT TOKENS: You must include X_TIME_FILTER_GLOBAL1_X exactly as provided.
2. PATIENT CONTEXT WRAPPER: Because you are using "I/My", you must preserve the patient ID in a context prefix. 
   - EVERY output must start with: Context: patient X_PATIENT_ID_X. "..."
   - Do NOT put X_PATIENT_ID_X inside the spoken quote.
3. THE "BLACK BOX" RULE: Treat X_TIME_FILTER_GLOBAL1_X as a solid block that implies its own preposition (e.g., "since 2023", "in 2022"). 
4. NO PREPOSITIONAL BRIDGES: Do not add 'in', 'during', 'for' immediately before X_TIME_FILTER_GLOBAL1_X.
   - CORRECT: "...have I had any surgeries X_TIME_FILTER_GLOBAL1_X?"
   - INCORRECT: "...have I had any surgeries in X_TIME_FILTER_GLOBAL1_X?"
5. EXACT TIME FILTER MENTAL TEST: X_TIME_FILTER_EXACT1_X will be replaced with "last" or "first", so this replacement must make sense. Typically, this means X_TIME_FILTER_EXACT1_X will be directly followed by the same noun as in the original question.

EXAMPLES:
Input: "Count the number of hospital visits of patient X_PATIENT_ID_X X_TIME_FILTER_GLOBAL1_X."
Output: "Context: patient X_PATIENT_ID_X. How many times have I been to the hospital X_TIME_FILTER_GLOBAL1_X?"

Input: "Has_verb patient X_PATIENT_ID_X been diagnosed with X_DIAGNOSIS_NAME_X X_TIME_FILTER_GLOBAL1_X?"
Output: "Context: patient X_PATIENT_ID_X. X_TIME_FILTER_GLOBAL1_X, did the doctors say anything about if my dad has X_DIAGNOSIS_NAME_X?"

Input: "What was the X_TIME_FILTER_EXACT1_X careunit of patient X_PATIENT_ID_X X_TIME_FILTER_GLOBAL1_X?"
Output: "Context: patient X_PATIENT_ID_X. What was the X_TIME_FILTER_EXACT1_X careunit I was assigned to X_TIME_FILTER_GLOBAL1_X?"


OUTPUT FORMAT:
Return the response in the exact format specified by the schema. Make sure each response is in the format: "Context: patient X_PATIENT_ID_X. PARAPHRASED_QUESTION_HERE". Do not include conversational filler.
"""
    elif perspective == "clinical":
        return """ROLE: You are a medical professional. Your task is to paraphrase clinical query templates into diverse, natural language while maintaining strict "Slot Integrity."

OBJECTIVE:
Generate high-quality, professional paraphrases of the provided medical question template. You must vary the sentence structure and word choices while ensuring the meaning of the question is preserved and the placeholder tokens remain functional for a downstream substitution system.

CRITICAL SLOT RULES:
1. EXACT TOKENS: Include ALL slot tokens (e.g., X_PATIENT_ID_X, X_TIME_FILTER_GLOBAL1_X) exactly as provided.
2. THE "BLACK BOX" RULE: Treat X_TIME_FILTER_GLOBAL1_X as a solid "Lego brick" that already contains its own preposition (e.g., "since 2023", "during 2022"). 
3. NO PREPOSITIONAL BRIDGES: Do not add any words (e.g., 'in', 'during', 'for', 'within', 'at') immediately before X_TIME_FILTER_GLOBAL1_X. 
   - INCORRECT: "...prescribed during X_TIME_FILTER_GLOBAL1_X"
   - CORRECT: "...prescribed X_TIME_FILTER_GLOBAL1_X"
4. MENTAL TEST: If you replace the X_TIME_FILTER_GLOBAL1_X token with "in 2020", your sentence must not result in a double preposition like "during in 2020".
5. X_TIME_FILTER_EXACT1_X will be replaced with "last" or "first", so do NOT change the placement of this slot token, or the noun it is followed by.

VARIETY & REORDERING RULES:
To ensure dataset diversity, you MUST vary the sentence structure. This will include reordering the slot tokens. Some examples are: 
1. Patient-first: Lead with the patient identifier token X_PATIENT_ID_X. Note that this will be a numeric ID, so you should say 'patient X_PATIENT_ID_X'.
2. Time-filter first: Lead with a time-filter token X_TIME_FILTER_GLOBAL1_X.
3. Action-first: Lead with a clinical verb (e.g., "Count," "Identify," "List").
4. Switch between commands and questions. For example, "Count the number..." could be replaced with "How many...".
You are free to come up with your own variations as well as long as they preserve the meaning of the question and the placeholder tokens remain functional for a downstream substitution system.

CLINICAL STYLE:
- Use professional medical terminology (e.g., "pharmacological interventions," "administered," "documented," "clinical encounters").
- Maintain a clinical tone, with a mix of formal and informal language. 

OUTPUT FORMAT:
Return the response in the exact format specified by the schema. Do not include conversational filler."""

    else:
        raise ValueError(f"Invalid perspective: {perspective}")


def generate_paraphrases_batch(
    masked_template: str,
    required_slots: List[str],
    count: int,
    model: str = MODEL,
    temperature: float = TEMPERATURE,
    perspective: str = "clinical",
) -> List[str]:
    """
    Generate a batch of paraphrases via LLM API.

    Args:
        masked_template: Original template with masked slots
        required_slots: List of required masked slot tokens
        count: Number of paraphrases to generate
        model: OpenAI model to use
        temperature: Sampling temperature
        perspective: Either "clinical" or "patient" to determine the perspective for paraphrasing

    Returns:
        List of generated paraphrases (masked)

    Raises:
        Exception: If API call fails after retries
    """
    client = _get_client()

    # Create user prompt as JSON
    user_prompt = json.dumps(
        {
            "original_sentence": masked_template,
            "required_slots": required_slots,
            "count": count,
        },
        indent=2,
    )

    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Use structured outputs with Pydantic model via beta.parse API
            response = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": _create_system_prompt(perspective)},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                response_format=ParaphraseResponse,
            )

            # Parse response using Pydantic - structured outputs handle validation automatically
            parsed_response = response.choices[0].message.parsed

            # Fallback to manual parsing if structured outputs didn't parse automatically
            if parsed_response is None:
                content = response.choices[0].message.content
                if content:
                    try:
                        parsed_dict = json.loads(content)
                        # Validate using Pydantic - this will raise ValidationError if invalid
                        parsed_response = ParaphraseResponse(**parsed_dict)
                    except (json.JSONDecodeError, ValueError) as e:
                        raise ValueError(f"Failed to parse response: {e}") from e
                else:
                    raise ValueError("Empty response from API")

            # Extract paraphrases - Pydantic ensures they're strings in a list
            return parsed_response.paraphrases

        except ValueError as e:
            # Pydantic validation errors or parsing errors
            last_error = e
            logger.warning(
                f"Validation/parsing error (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)  # Exponential backoff
            continue

        except Exception as e:
            # API errors or other exceptions
            last_error = e
            logger.warning(f"API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)  # Exponential backoff
            continue

    # All retries failed
    raise Exception(
        f"Failed to generate paraphrases after {MAX_RETRIES} attempts: {last_error}"
    )


def generate_paraphrases_for_template(
    template_id: str,
    masked_template: str,
    required_slots: Set[str],
    max_paraphrases: int = MAX_PARAPHRASES_PER_TEMPLATE,
    batch_size: int = BATCH_SIZE,
    perspective: str = "clinical",
) -> List[str]:
    """
    Generate target number of paraphrases with multiple API calls if needed.

    Args:
        template_id: Template identifier (for logging)
        masked_template: Original template with masked slots
        required_slots: Set of required masked slot tokens
        max_paraphrases: Target number of unique paraphrases
        batch_size: Number of paraphrases per API call
        perspective: Either "clinical" or "patient" to determine the perspective for paraphrasing

    Returns:
        List of generated paraphrases (masked), may be less than max_paraphrases
    """
    all_paraphrases = []
    required_slots_list = sorted(list(required_slots))  # Convert to sorted list for API

    # Generate in batches until we have enough
    attempts = 0
    max_attempts = (
        max_paraphrases // batch_size
    ) + 3  # Extra attempts to account for filtering

    while len(all_paraphrases) < max_paraphrases and attempts < max_attempts:
        try:
            batch = generate_paraphrases_batch(
                masked_template,
                required_slots_list,
                batch_size,
                perspective=perspective,
            )
            all_paraphrases.extend(batch)
            attempts += 1

            logger.debug(
                f"Generated batch of {len(batch)} paraphrases for {template_id}"
            )

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error generating paraphrases for {template_id}: {e}")
            # Continue with next batch attempt
            attempts += 1
            time.sleep(2)
            continue

    # Deduplicate immediately after generation
    unique_paraphrases = []
    seen = set()
    for p in all_paraphrases:
        if p not in seen:
            unique_paraphrases.append(p)
            seen.add(p)

    return unique_paraphrases[:max_paraphrases]
