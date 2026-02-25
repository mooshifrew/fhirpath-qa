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
from ..utils import rust_analyze_query

template_ids = template_registry.list_templates()

PATIENT_IDS = get_valueset("patient_id")


@pytest.mark.parametrize("template_id", template_ids)
def test_random_generation(template_id):
    ctx = GenerationContext(patient_id="10019917")  # the smallest patient bundle
    template = template_registry.new_template(template_id, gen_ctx=ctx)
    generated = template.generate_qa_pair()
    for i in range(10):
        template.regenerate_qa_pair()


@pytest.mark.parametrize("template_id", template_ids)
def test_fhirpath_validity(template_id):
    ctx = GenerationContext(patient_id="10019917")
    template_cls = template_registry.get_template_class(template_id)

    sp_allowed = template_cls.sp_allowed
    t_allowed = template_cls.t_allowed
    op_allowed = template_cls.op_allowed

    for p_slot, p_idents in sp_allowed.items():
        for p_ident in p_idents:
            p = simple_placeholder_registry.gen_placeholder(p_ident, ctx)
            template = template_cls(gen_ctx=ctx, simple_placeholders={p_slot: p})
            query = template.compile_query()
            assert rust_analyze_query(query) == ""

    for t_slot, t_idents in t_allowed.items():
        for t_ident in t_idents:
            t = time_expression_registry.gen_time_expression(t_ident, ctx)
            template = template_cls(gen_ctx=ctx, time_placeholders={t_slot: t})
            query = template.compile_query()
            assert rust_analyze_query(query) == ""

    for op_slot, op_idents in op_allowed.items():
        for op_ident in op_idents:
            op = operation_registry.gen_operation(op_ident, ctx)
            template = template_cls(gen_ctx=ctx, operation_placeholders={op_slot: op})
            query = template.compile_query()
            assert rust_analyze_query(query) == ""  # returns "" or the error
