from pydantic import Field
from typing import ClassVar
from datetime import datetime

from ..base import TimeExpression, register_time_expression
from ..enums import (
    TimeFilterType,
    TimeExpressionType,
    TimeUnit,
    IntervalType,
    Option,
    ResourceType,
)
from ..generator import GenerationContext

SORT_KEYS = {  # TODO: add polymorphic keys if octofhir-fhirpath supports it
    "Observation": "effectiveDateTime",
    "MedicationAdministration": "effectiveDateTime",  # sometimes could be effectivePeriod
    "MedicationRequest": "authoredOn",
    "Procedure": "performed.start",  # alternatively performed.start/end
    "Encounter": "period.start",  # or period.end
    "Condition": "encounter.resolve().period.start",
}


@register_time_expression
class ExactFirst(TimeExpression):
    """When interested in the first resource."""

    time_exp_id: ClassVar[str] = "exact-first"

    filter_type: ClassVar[TimeFilterType] = TimeFilterType.EXACT
    exp_type: ClassVar[TimeExpressionType] = TimeExpressionType.RELATIVE
    option: ClassVar[Option] = Option.NA
    unit: ClassVar[TimeUnit] = TimeUnit.EXACT
    interval_type: ClassVar[IntervalType] = IntervalType.AT

    def get_fhirpath_expression(self, params):
        resource = params.get("resource_type")

        if resource in SORT_KEYS:
            key = SORT_KEYS[resource]
            return (
                f"sort({key}).first()"  # note that some implementations use 'orderBy()'
            )
        else:
            raise ValueError(f"resource type {resource} is not valid.")

    def get_nl_expr(self) -> str:
        return "first"

    @classmethod
    def random_instance(cls, ctx: GenerationContext):
        return cls()


@register_time_expression
class ExactLast(TimeExpression):
    """When interested in the first resource."""

    time_exp_id: ClassVar[str] = "exact-last"

    filter_type: ClassVar[TimeFilterType] = TimeFilterType.EXACT
    exp_type: ClassVar[TimeExpressionType] = TimeExpressionType.RELATIVE
    option: ClassVar[Option] = Option.NA
    unit: ClassVar[TimeUnit] = TimeUnit.EXACT
    interval_type: ClassVar[IntervalType] = IntervalType.AT

    def get_fhirpath_expression(self, params):
        resource = params.get("resource_type")

        if resource in SORT_KEYS:
            key = SORT_KEYS[resource]
            return (
                f"sort({key}).last()"  # note that some implementations use 'orderBy()'
            )
        else:
            raise ValueError(f"resource type {resource} is not valid.")

    def get_nl_expr(self) -> str:
        return "last"

    @classmethod
    def random_instance(cls, ctx: GenerationContext):
        return cls()
