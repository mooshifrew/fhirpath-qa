import pytest
from datetime import datetime

# Right now we are just testing validity of templates and queries -- ie that the fhirpath expressions are valid.
# TODO: Test for correctness of the queries

from fhirpath_gen.base import (
    time_expression_registry,
    simple_placeholder_registry,
    operation_registry,
    template_registry,
)
from fhirpath_gen.generator import GenerationContext

from fhirpath_gen.valuesets import get_valueset
import os

template_ids = template_registry.list_templates()

PATIENT_IDS = get_valueset("patient_id")


@pytest.mark.preview
@pytest.mark.parametrize("template_id", template_ids)
def test_random_preview(template_id):
    patient_id = "10019917"  # the smallest patient bundle
    ctx = GenerationContext(patient_id=patient_id)
    template = template_registry.new_template(template_id, gen_ctx=ctx)

    # Generate once initially
    generated = template.generate_qa_pair()
    print("\n---")
    print(f"now: {ctx.now}")
    print(f"template: {template_id}")
    print(f"question: {generated['question']}")
    print(f"query: {generated['query']}")

    # Then regenerate multiple times
    for i in range(1):
        regenerated = template.regenerate_qa_pair()
        print("\n---")
        print(f"now: {ctx.now}")
        print(f"template: {template_id}")
        print(f"question: {regenerated['question']}")
        print(f"query: {regenerated['query']}")
