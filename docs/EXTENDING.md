# Extending FHIRPath-QA

This doc outlines the typical extension points for generating *new* question/query types.

If you’re only using the released datasets, you can ignore this.

## Extension surface area

Most extensions fall into one of these categories:

- **New template** (new question + query type)
- **New placeholder type** (new slot to fill)
- **New valueset entries** (more candidate values for an existing slot)
- **New time expression** (new temporal phrasing and matching query filter)

## Add a new template (typical)

1. **Pick a template category**
   - Count / boolean / list / specific date / specific value (see `fhirpath_gen/templates/`)

2. **Implement the template**
   - Add a new template class alongside similar templates in `fhirpath_gen/templates/`
   - Follow existing patterns for:
     - required placeholders
     - query construction
     - returned metadata (template id, placeholder bindings, etc.)

3. **Add canonical template text**
   - Update `id2question_templates.json` to include the canonical (non-paraphrased) question template text for your new `question_template_id`.

4. **(Optional) Add to the template reference**
   - Update `docs/TEMPLATE_REFERENCE.md` with your new template’s ID and text.

## Add / update a valueset

Valuesets live under `fhirpath_gen/valuesets/` as JSON files.

Typical workflow:

1. Edit or add a JSON file for the placeholder you care about (e.g. `drug_name.json`, `lab_name.json`).
2. Run the relevant generation script and verify that sampling behaves as expected.

## Add a new placeholder

Placeholders are generally implemented in:

- `fhirpath_gen/simple_placeholders/` (string-like slots)
- `fhirpath_gen/operations/` (operators / comparisons)
- `fhirpath_gen/time_expressions/` (time filters)

You typically need:

1. A placeholder implementation (sampling + rendering)
2. Any required valuesets (JSON files)
3. Integration into the templates that use it

## Some more advice

- Start by copying the closest existing template and modifying incrementally.
- Use `validate_setup.py` and the existing tests under `fhirpath_gen/tests/` to catch registry/template issues early.
- Keep template IDs stable once published (they are used for filtering, splits, and holdout definitions).

