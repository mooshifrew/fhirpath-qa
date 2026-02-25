## Repository overview

This repo contains:

- **Released datasets** (`output/*.jsonl`)
- **Reproduction scripts** (top-level `*.py`)
- **Core generation library** (`fhirpath_gen/`)
- **FHIR data setup tooling** (`compose/`, `setup/`)
- **Optional paraphrasing pipeline** (`generate_paraphrases.py`, `paraphrasing/`)

## Project structure (current)

```
fhirpath-qa/
├── output/
│   ├── fhirpath-qa-benchmark.jsonl     # released benchmark dataset (includes answers)
│   └── fhirpath-qa-large.jsonl         # released large dataset (no answers)
├── fhirpath_gen/                       # core generation library (templates/placeholders/valuesets)
├── paraphrasing/                       # optional paraphrase generation + filtering utilities
├── compose/
│   └── docker-compose.yaml             # HAPI FHIR + Postgres (for importing/exporting bundles)
├── setup/                              # scripts to import NDJSON + export patient bundles
├── docs/
│   ├── TEMPLATE_REFERENCE.md           # template catalog
│   ├── ARCHITECTURE.md                 # high-level architecture (how generation works)
│   ├── EXTENDING.md                    # how to add templates/placeholders/valuesets
│   └── PARAPHRASING.md                 # paraphrase pipeline + file formats
├── generate_final_dataset.py           # benchmark generation script
├── generate_questions.py               # fixed-size dataset generation script
├── add_splits_to_dataset.py            # add split/holdout metadata to an existing .jsonl
├── filter_dataset.py                   # filter .jsonl by split and template holdouts
├── generate_paraphrases.py             # optional: generate new paraphrases via LLM
├── split_paraphrases.py                # optional: regenerate paraphrase train/val/test splits
├── validate_setup.py                   # sanity checks (imports, valuesets, templates, etc.)
├── config.py                           # paths + local configuration (FHIRPATH_EXE, dirs)
├── id2question_templates.json          # canonical template text by template_id
├── patient_ids.txt                     # patient IDs used for dataset generation
├── requirements.txt                    # python dependencies
└── setup.py                            # package install metadata
```

## Intended “public” workflow

For a step-by-step reproduction tutorial, see `README.md`. At a high level:

1. **Set up** HAPI FHIR + export `$everything` bundles into `patient_bundles/`
2. **Generate benchmark** with `generate_final_dataset.py`
3. **Generate large** with `generate_questions.py`
4. **Add splits/holdouts** with `add_splits_to_dataset.py`
5. **Filter** with `filter_dataset.py` (optional)

