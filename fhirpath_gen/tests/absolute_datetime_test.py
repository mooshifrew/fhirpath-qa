import pytest
from datetime import datetime
from typing import ClassVar, Literal

from fhirpath_gen.base import (
    time_expression_registry,
    simple_placeholder_registry,
    Template,
)
from fhirpath_gen.enums import TimeUnit, IntervalType, TimeFilterType, TimeExpressionType, Option

# Import the concrete preset classes (ensures decorators run and classes register)
from fhirpath_gen.time_expressions import (
    AbsoluteDateTime,
    AbsYearIn,
    BlankTimeExpr
)


# -----------------------------
# Registry presence
# -----------------------------
def test_presets_are_registered():
    expected_ids = {
        "abs-year-in",
        "abs-year-until",
        "abs-year-since",
        "abs-month-in",
        "abs-month-until",
        "abs-month-since",
        "abs-day-in",
        "abs-day-until",
        "abs-day-since",
        "abs-exact-in",
        "blank"
    }
    registered = set(time_expression_registry.list_time_expressions())
    for tid in expected_ids:
        assert tid in registered, f"{tid} should be registered but is missing"


# -----------------------------
# Factory construction via registry
# -----------------------------
@pytest.mark.parametrize(
    "time_id, unit, interval, date_kwargs",
    [
        ("abs-year-in",    TimeUnit.YEAR,  IntervalType.IN,     dict(date="2024-01-01")),
        ("abs-year-until", TimeUnit.YEAR,  IntervalType.UNTIL,  dict(date="2024-12-31")),
        ("abs-year-since", TimeUnit.YEAR,  IntervalType.SINCE,  dict(date="2024-01-01")),
        ("abs-month-in",   TimeUnit.MONTH, IntervalType.IN,     dict(date="2024-01-01")),
        ("abs-month-until",TimeUnit.MONTH, IntervalType.UNTIL,  dict(date="2024-01-01")),
        ("abs-month-since",TimeUnit.MONTH, IntervalType.SINCE,  dict(date="2024-12-01")),
        ("abs-day-in",     TimeUnit.DAY,   IntervalType.IN,     dict(date="2024-01-15")),
        ("abs-day-until",  TimeUnit.DAY,   IntervalType.UNTIL,  dict(date="2024-01-31")),
        ("abs-day-since",  TimeUnit.DAY,   IntervalType.SINCE,  dict(date="2024-01-01")),
        ("abs-exact-in",   TimeUnit.DAY,   IntervalType.AT,     dict(date="2024-01-15T14:30:00")),
    ],
)
def test_factory_instantiation(time_id, unit, interval, date_kwargs):
    # Construct via registry (factory)
    inst = time_expression_registry.get_time_expression(time_id, **date_kwargs)

    # Basic field checks: subclasses pin these via Literals, so they should match
    assert inst.unit == unit
    assert inst.interval_type == interval

    # These are set at class-level in presets
    assert inst.filter_type == TimeFilterType.GLOBAL
    assert inst.exp_type == TimeExpressionType.ABSOLUTE
    assert inst.option == Option.NA

    # FHIRPath generation should not crash with a sensible param
    # (resource_type must exist in TIME_PATHS for full coverage in your utils)
    inst.get_fhirpath_expression({"resource_type": "MedicationRequest"})


# -----------------------------
# Template identifier resolution (non-optional)
# -----------------------------
class _TemplateYearIn(Template):
    """
    Minimal template used in tests to verify that identifier-based t_allowed
    resolves through the registry and auto-generates a time expression when
    none is provided.
    """
    template_id: ClassVar[str] = "test_year_in"
    description: ClassVar[str] = "Test template for abs-year-in"
    tags: ClassVar[list[str]] = []
    question_template: ClassVar[str] = "Show meds [t_slot] for {patient_id1}"

    # Only one allowed time type; not optional -> must auto-fill using random_instance()
    t_allowed: ClassVar[dict[str, list[object]]] = {"t_slot": ["abs-year-in"]}
    sp_allowed: ClassVar[dict[str, list[object]]] = {"patient_id1": ["patient_id"]}
    op_allowed: ClassVar[dict[str, list[object]]] = {}

    def compile_query(self, filled_placeholders):
        t = self.time_placeholders["t_slot"]
        # Should be an instance of AbsYearIn
        assert isinstance(t, AbsYearIn)
        # Just return its fhirpath with a common resource_type

        return ("Bundle.entry.resource.where(resourceType='MedicationRequest'"
                " and "
                f"{t.get_fhirpath_expression({'resource_type': 'Procedure'})}"
                ").select(medicationReference.resolve() | medicationCodeableConcept)")
        


def test_template_resolves_identifier_and_autofills_time():
    sample_patient = simple_placeholder_registry.get_placeholder("patient_id", value="10009035")

    t = _TemplateYearIn(simple_placeholders={'patient_id1':sample_patient})  # no AbsYearIn -> should auto-generate AbsYearIn via random_instance() which is 2024-01-01
    assert isinstance(t.time_placeholders["t_slot"], AbsYearIn)

    # verify question rendering should autofill the template
    question = t.generate_question()
    year = t.time_placeholders['t_slot'].date.year
    assert question == f"Show meds in {year} for 10009035"
    print(question) # for debugging
    
    # verify compile_query works
    compiled_query = t.compile_query({})
    print(compiled_query)  # For debugging
    assert "select((performedDateTime | performedPeriod.start).first())" in compiled_query

# -----------------------------
# Template optional None behavior
# -----------------------------
class _TemplateOptionalDay(Template):
    """
    Minimal template to verify that optional time slots (None allowed) are set to
    None when not provided.
    """
    template_id: ClassVar[str] = "test_optional_day"
    description: ClassVar[str] = "Test template for optional time slot"
    tags: ClassVar[list[str]] = []
    question_template: ClassVar[str] = "Show meds [t_slot]"

    # Optional time slot: may be None or abs-day-in
    t_allowed: ClassVar[dict[str, list[object]]] = {"t_slot": ["blank", "abs-day-in"]}
    sp_allowed: ClassVar[dict[str, list[object]]] = {}
    op_allowed: ClassVar[dict[str, list[object]]] = {}

    def compile_query(self, filled_placeholders):
        t = self.time_placeholders.get("t_slot")
        return t.get_fhirpath_expression({"resource_type": "MedicationRequest"})


def test_template_optional_time_defaults_to_blank():
    t = _TemplateOptionalDay()  # no params -> since None is allowed, slot should default to blank
    assert isinstance(t.time_placeholders["t_slot"], BlankTimeExpr)
    # Should render without trying to fill [t_slot]
    q = t.generate_question()
    assert "[t_slot]" not in q  # fill_slots skips None entries
    # compile_query returns empty string when None
    assert t.compile_query({}) == ""
