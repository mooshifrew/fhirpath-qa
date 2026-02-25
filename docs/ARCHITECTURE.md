# Architecture (high level)

This document is a **conceptual map** of how FHIRPath-QA is structured. It’s meant to help you find the right part of the code when extending or debugging generation.

## Big picture

FHIRPath-QA generates a dataset by repeatedly producing a **(question, FHIRPath query)** pair from a **template**, plus any metadata required to reproduce the generation (placeholders, time expressions, etc.).

At a high level:

- **Templates** define the *shape* of a question and its corresponding query.
- A **generation context** provides patient-specific values and sampling utilities.
- **Placeholders** (simple, time, operation) are expanded into concrete values.
- Optionally, a generated query can be **evaluated** against a Patient `$everything` bundle to produce an **answer**.

## Key folders

### `fhirpath_gen/`

Core generation library.

- **`fhirpath_gen/templates/`**: template definitions for the benchmark (each template yields a question/query pair)
- **`fhirpath_gen/time_expressions/`**: date/time filter objects (absolute + relative)
- **`fhirpath_gen/simple_placeholders/`**: placeholder slot filling (drug names, labs, procedures, etc.)
- **`fhirpath_gen/operations/`**: operation placeholders (e.g., comparisons)
- **`fhirpath_gen/valuesets/`**: JSON valuesets backing placeholder sampling

Importing `fhirpath_gen` triggers registration so templates/placeholders are discoverable through the registry.

### Top-level scripts

These scripts orchestrate dataset creation and post-processing:

- **`generate_final_dataset.py`**: benchmark-oriented generation loop (cycles patients and paraphrases until coverage criteria are met)
- **`generate_questions.py`**: fixed-size dataset generation (simple “generate N per template” loop)
- **`add_splits_to_dataset.py`**: post-process a `.jsonl` file to add `split` + `holdout`
- **`filter_dataset.py`**: filter a `.jsonl` by split and/or template IDs

### `setup/` + `compose/`

Scripts and Docker configuration used to:

- import NDJSON data into a local HAPI FHIR server
- export per-patient **Patient `$everything` bundles** into `patient_bundles/`

### `paraphrasing/` (optional)

LLM-based paraphrase generation utilities used to create paraphrased versions of question templates.

## Data files used by generation

- **`patient_ids.txt`**: list of patient IDs to iterate over in dataset mode
- **`patient_bundles/`**: exported `$everything` bundles (required for evaluation and patient-specific value extraction)
- **`paraphrasing/paraphrases_*_validated.json`**: paraphrases used by the dataset generation scripts
- **`paraphrasing/paraphrase_splits.json`**: mapping from paraphrase text to `train`/`val`/`test` (used to assign dataset split)

