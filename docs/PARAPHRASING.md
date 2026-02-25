# Paraphrasing pipeline (optional)

This repo includes an optional paraphrasing pipeline that was used to create paraphrased variants of the canonical templates in `id2question_templates.json`.

You do **not** need paraphrasing to use the released datasets, but it’s useful if you want to:

- generate new paraphrases for additional templates
- regenerate train/val/test paraphrase splits
- run ablations on paraphrase distribution

## Key files

- **Canonical templates**: `id2question_templates.json`
- **Paraphrase generator entry point**: `generate_paraphrases.py`
- **Paraphrasing package**: `paraphrasing/`
- **Validated paraphrases used by dataset generation**:
  - `paraphrasing/paraphrases_clinical_validated.json`
  - `paraphrasing/paraphrases_patient_validated.json`
- **Paraphrase split mapping**: `paraphrasing/paraphrase_splits.json`

## Generating paraphrases with an LLM

`generate_paraphrases.py` performs:

1. slot masking (so placeholder tokens are preserved)
2. LLM generation (clinical vs patient “perspective” prompts)
3. automatic quality filtering (slot integrity + similarity + edit distance)
4. saving results incrementally to avoid losing progress

Example:

```bash
python generate_paraphrases.py --perspective clinical
python generate_paraphrases.py --perspective patient
```

Environment:

- Set **`OPENAI_API_KEY`** for the OpenAI client.
- Install paraphrasing dependencies from `requirements.txt`.

## Manual review utilities

Paraphrase generation includes tools intended to support a manual review loop:

- **`paraphrasing/verify_paraphrases.py`**:
  - Computes similarity/edit-distance metrics
  - Writes CSV samples for inspection
  - Useful for sanity checking and selecting candidates for manual filtering

- **`paraphrasing/filter_paraphrases.py`**:
  - Consumes a manually-reviewed CSV (with a `good` column)
  - Produces a JSON file containing only accepted paraphrases

## Paraphrase splits (train/val/test)

Split assignment is stored per paraphrase text in:

- `paraphrasing/paraphrase_splits.json`

You can regenerate splits with:

```bash
python split_paraphrases.py
```

The dataset post-processing script `add_splits_to_dataset.py` uses this mapping to assign each dataset entry a `split`.

## How paraphrases connect to dataset generation

Both `generate_questions.py` and `generate_final_dataset.py` support using paraphrases during generation (see their CLI flags), and they accept file paths for:

- clinical paraphrases
- patient paraphrases
- paraphrase split mapping

