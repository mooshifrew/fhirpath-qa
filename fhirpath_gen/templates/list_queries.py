from typing import ClassVar, Dict, List

from fhirpath_gen.base import (
    register_template,
    Template,
)

from fhirpath_gen.enums import ResourceType


@register_template
class Template027(Template):
    """List admission times"""

    template_id: ClassVar[str] = "list-admission-times"
    description: ClassVar[str] = "List the hospital admission times of a patient"
    tags: ClassVar[list[str]] = ["admission", "list", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "List the hospital admission times of patient {patient_id} [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = {
        "time_filter_global1": [
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
            "rel-year-in-last",
            "rel-year-until-last",
            "rel-year-since-last",
            "rel-year-in-this",
            "rel-year-until",
            "rel-year-since",
            "rel-month-in-last",
            "rel-month-until-last",
            "rel-month-since-last",
            "rel-month-in-this",
            "rel-month-until",
            "rel-month-since",
            "rel-day-in-last",
            "rel-day-until-last",
            "rel-day-since-last",
            "rel-day-in-this",
            "rel-day-until",
            "rel-day-since",
            "blank",
        ]
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.ENCOUNTER.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""

        where_parts = [f"resourceType='{resource}'", "partOf.empty()"]
        if time_expr:
            where_parts.append(time_expr)

        return f"Bundle.entry.resource.where({' and '.join(where_parts)}).period.start"
