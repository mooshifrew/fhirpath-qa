# FHIRPath-QA

Code + data for FHIRPath-QA.

## Released datasets

The datasets are JSONL in `output/`:

- **`output/fhirpath-qa-benchmark.jsonl`**: benchmark-style dataset (includes **answers**).
- **`output/fhirpath-qa-large.jsonl`**: larger dataset (does **not** include answers).

### Record schema (high level)

Both datasets include (at least) the following fields:

- **`patient_id`**: patient identifier (string)
- **`question`**: natural language question (string)
- **`query`**: FHIRPath query (string)
- **`perspective`**: `clinical` or `patient`
- **`question_template_id`**: template ID (string)
- **`question_template`**: the paraphrased template text used (string)
- **`split`**: `train` / `val` / `test` (derived from paraphrase split mapping)
- **`holdout`**: integer holdout group label (see `add_splits_to_dataset.py`)
- **`s_placeholders` / `t_placeholders` / `op_placeholders`**: placeholder metadata used during generation

Benchmark-only:

- **`answer`**: result of FHIRPath query evaluation.


## Reproducing the datasets

### Prerequisites

- Python 3.9+ recommended
- Docker + Docker Compose (only needed to import/export FHIR data via HAPI)

### Install

```bash
pip install -r requirements.txt
pip install -e .
```

### Validate basic setup

```bash
python validate_setup.py
```

At this point you will see failures related to Patient bundles and the FHIRPath executable.

### Setup (FHIR server + patient bundles)

The generation scripts expect to run queries against **Patient/$everything bundles** stored locally in `patient_bundles/`.

#### Download MIMIC-IV on FHIR Demo

Download the MIMIC-IV on FHIR data and place .ndjson files in `compose/data/`

**Option A: Using wget**
```bash
# Download the demo dataset
wget -r -N -c -np https://physionet.org/files/mimic-iv-fhir-demo/2.1.0/
```

**Option B: Manual download**
Visit [MIMIC-IV on FHIR Demo](https://physionet.org/content/mimic-iv-fhir-demo/2.1.0/) and download the ZIP file.


#### Start HAPI Server

```bash
# Start the FHIR server
cd compose
docker-compose up -d

# Verify it's running
curl http://localhost:8080/fhir/metadata
```

This starts:
- PostgreSQL database (port 5432)
- HAPI FHIR server (port 8080)

#### Import Data

In a second terminal, start file server (so Docker can access NDJSON files):

```bash
python setup/start_file_server.py
```

Import NDJSON into HAPI:

```bash
python setup/import_data.py
```

Once this completes, the fileserver in the second terminal can be closed.

#### Export Patient Bundles:

```bash
python setup/export_all_patient_bundles.py
```

#### Evaluation

If you want to evaluate FHIRPath queries and attach answers, install `octofhir-fhirpath` and point `FHIRPATH_EXE` in [`config.py` (line 34)](config.py#L34) (or via env var).

- Install via Cargo:

```bash
cargo install octofhir-fhirpath
```

- Or download a release binary from `https://github.com/octofhir/octofhir-fhirpath/releases`

### Scripts overview

| Script | Purpose |
|--------|---------|
| `generate_final_dataset.py` | Generates a benchmark-style dataset. Cycles through patients, randomly sampling paraphrases until each paraphrase has been used at least once per patient. Used to produce `fhirpath-qa-benchmark.jsonl`. |
| `generate_questions.py` | Generates a fixed number of questions per template across patients. Paraphrase selection is random. Used to produce `fhirpath-qa-large.jsonl`. |
| `add_splits_to_dataset.py` | Post-processes an existing `.jsonl` dataset to add `split` (train/val/test, derived from `paraphrasing/paraphrase_splits.json`) and `holdout` (template-group label) fields. |
| `filter_dataset.py` | Filters a `.jsonl` dataset by split and/or template ID. Useful for creating subsets for fine-tuning or evaluation (e.g. keep only train+val, exclude certain holdout templates). |

### Generating `fhirpath-qa-large.jsonl`

`generate_questions.py` produces a fixed-size dataset by generating a set number of questions per template for every patient in the provided list. Paraphrases are selected but there is no constraint ensuring uniform coverage across paraphrases or patients (Generates two questions per template per patient: 2*61*100=12200).

```bash
python generate_questions.py --dataset patient_ids.txt 2 output/fhirpath-qa-large.jsonl --paraphrase
```

After generation, add split and holdout metadata:

```bash
python add_splits_to_dataset.py --input-file output/fhirpath-qa-large.jsonl --output-file output/fhirpath-qa-large.jsonl
```

### Generating `fhirpath-qa-benchmark.jsonl`

`generate_final_dataset.py` produces the benchmark dataset. It iterates through patients in cycles, sampling paraphrases so that each paraphrase appears at least once per patient. This gives more controlled coverage than `generate_questions.py`.

```bash
python generate_final_dataset.py --output-file output/fhirpath-qa-benchmark.jsonl --evaluate
```

After generation, add split and holdout metadata:

```bash
python add_splits_to_dataset.py --input-file output/fhirpath-qa-benchmark.jsonl --output-file output/fhirpath-qa-benchmark.jsonl
```

### Filtering

`filter_dataset.py` can produce subsets of either dataset. For example, to keep only the training and validation splits and exclude specific template IDs:

```bash
python filter_dataset.py --input-file output/fhirpath-qa-large.jsonl --output-file output/filtered.jsonl --splits train,val --exclude-template-ids count-drugs-prescribed,has-diagnosis
```


## Documentation

- `docs/TEMPLATE_REFERENCE.md`: template catalog + placeholder conventions
- `docs/ARCHITECTURE.md`: high-level code structure
- `docs/EXTENDING.md`: how to add templates/placeholders/valuesets
- `docs/PARAPHRASING.md`: paraphrase pipeline

## License

MIT License. See `LICENSE`.

## Citation

If you use this dataset or code, please cite our paper (coming soon):

```bibtex
@misc{frew2026fhirpathqa,
  title        = {FHIRPath-QA: Executable Question Answering over FHIR Electronic Health Records},
  author       = {Frew, Michael and Bheda, Nishit and Tripp, Bryan},
  year         = {2026},
  note         = {Under review},
  institution  = {University of British Columbia and University of Waterloo}
}
```
