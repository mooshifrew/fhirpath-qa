from typing import ClassVar, Dict, List

from fhirpath_gen.base import (
    register_template,
    Template,
)

from fhirpath_gen.enums import ResourceType
from fhirpath_gen.utils import TIME_PATHS


@register_template
class Template028(Template):
    """Get time of specific microbiology test"""

    template_id: ClassVar[str] = "time-micro-test-specific"
    description: ClassVar[str] = "Get the time of a specific microbiology test"
    tags: ClassVar[list[str]] = ["microbiology", "time", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was patient {patient_id}'s [time_filter_exact1] {spec_name} microbiology test [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "spec_name": ["spec_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.OBSERVATION.value
        spec_expr = self.simple_placeholders["spec_name"].get_fhirpath_expression(
            {"resource_type": resource}
        )
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [
            f"resourceType='{resource}'",
            "category.coding.code='laboratory'",
            spec_expr,
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template029(Template):
    """Get hospital admission time"""

    template_id: ClassVar[str] = "time-hospital-admission"
    description: ClassVar[str] = "Get the hospital admission time"
    tags: ClassVar[list[str]] = ["admission", "time", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] hospital admission time of patient {patient_id}?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = {
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ]
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.ENCOUNTER.value
        params = {"resource_type": resource}
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        query = (
            f"Bundle.entry.resource.where(resourceType='{resource}' and partOf.empty())"
        )
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template030(Template):
    """Get admission time by route"""

    template_id: ClassVar[str] = "time-admission-route"
    description: ClassVar[str] = "Get the hospital admission time by admission route"
    tags: ClassVar[list[str]] = ["admission", "route", "time", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] hospital admission time that patient {patient_id} was admitted via {admission_route}?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "admission_route": ["admission_route"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = {
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ]
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.ENCOUNTER.value
        route_expr = self.simple_placeholders[
            "admission_route"
        ].get_fhirpath_expression({"resource_type": resource})
        params = {"resource_type": resource}
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", "partOf.empty()", route_expr]

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += ".select((period.start | period.end).first())"

        return query


@register_template
class Template031(Template):
    """Get hospital discharge time"""

    template_id: ClassVar[str] = "time-hospital-discharge"
    description: ClassVar[str] = "Get the hospital discharge time"
    tags: ClassVar[list[str]] = ["discharge", "time", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] hospital discharge time of patient {patient_id}?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = {
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ]
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.ENCOUNTER.value
        params = {"resource_type": resource}
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        query = (
            f"Bundle.entry.resource.where(resourceType='{resource}' and partOf.empty())"
        )
        if exact_expr:
            query += f".{exact_expr}"
        query += ".period.end"

        return query


@register_template
class Template032(Template):
    """Get intake time"""

    template_id: ClassVar[str] = "time-intake"
    description: ClassVar[str] = "Get the intake time"
    tags: ClassVar[list[str]] = ["intake", "time", "MedicationAdministration", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] intake time of patient {patient_id} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.MEDICATION_ADMINISTRATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template033(Template):
    """Get lab test time"""

    template_id: ClassVar[str] = "time-lab-test"
    description: ClassVar[str] = "Get the lab test time"
    tags: ClassVar[list[str]] = ["lab", "time", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] lab test of patient {patient_id} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [
            f"resourceType='{resource}'",
            "category.coding.code.lower()='laboratory'",
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template034(Template):
    """Get microbiology test time"""

    template_id: ClassVar[str] = "time-micro-test"
    description: ClassVar[str] = "Get the microbiology test time"
    tags: ClassVar[list[str]] = ["microbiology", "time", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] microbiology test of patient {patient_id} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [
            f"resourceType='{resource}'",
            "code.coding.system='http://fhir.mimic.mit.edu/CodeSystem/microbiology-test'",
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template035(Template):
    """Get prescription time"""

    template_id: ClassVar[str] = "time-prescription"
    description: ClassVar[str] = "Get the prescription time"
    tags: ClassVar[list[str]] = ["prescription", "time", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] prescription time of patient {patient_id} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.MEDICATION_REQUEST.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template036(Template):
    """Get procedure time"""

    template_id: ClassVar[str] = "time-procedure"
    description: ClassVar[str] = "Get the procedure time"
    tags: ClassVar[list[str]] = ["procedure", "time", "Procedure", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] procedure time of patient {patient_id} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.PROCEDURE.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".performed"  # can be a period or a datetime

        return query


@register_template
class Template037(Template):
    """Get specific intake time"""

    template_id: ClassVar[str] = "time-specific-intake"
    description: ClassVar[str] = "Get the time of a specific intake"
    tags: ClassVar[list[str]] = ["intake", "time", "MedicationAdministration", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} had a {input_name} intake [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "input_name": ["input_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.MEDICATION_ADMINISTRATION.value
        params = {"resource_type": resource}
        input_expr = self.simple_placeholders["input_name"].get_fhirpath_expression(
            params
        )

        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", input_expr]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template038(Template):
    """Get specific output time"""

    template_id: ClassVar[str] = "time-specific-output"
    description: ClassVar[str] = "Get the time of a specific output"
    tags: ClassVar[list[str]] = ["output", "time", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} had a {output_name} output [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "output_name": ["output_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        output_expr = self.simple_placeholders["output_name"].get_fhirpath_expression(
            params
        )

        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [
            f"resourceType='{resource}'",
            "category.coding.code='Output'",
            output_expr,
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template039(Template):
    """Get vital measurement time"""

    template_id: ClassVar[str] = "time-vital-measurement"
    description: ClassVar[str] = "Get the time of a vital measurement"
    tags: ClassVar[list[str]] = ["vital", "time", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} had a {vital_name} measured [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "vital_name": ["vital_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        vital_expr = self.simple_placeholders["vital_name"].get_fhirpath_expression(
            params
        )

        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", vital_expr]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template040(Template):
    """Get specific lab test time"""

    template_id: ClassVar[str] = "time-specific-lab"
    description: ClassVar[str] = "Get the time of a specific lab test"
    tags: ClassVar[list[str]] = ["lab", "time", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} received a {lab_name} lab test [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "lab_name": ["lab_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        lab_expr = self.simple_placeholders["lab_name"].get_fhirpath_expression(params)
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", lab_expr]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template041(Template):
    """Get specific procedure time"""

    template_id: ClassVar[str] = "time-specific-procedure"
    description: ClassVar[str] = "Get the time of a specific procedure"
    tags: ClassVar[list[str]] = ["procedure", "time", "Procedure", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} received a {procedure_name} procedure [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "procedure_name": ["procedure_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.PROCEDURE.value
        params = {"resource_type": resource}

        procedure_expr = self.simple_placeholders[
            "procedure_name"
        ].get_fhirpath_expression(params)
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", procedure_expr]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"
        return query


@register_template
class Template042(Template):
    """Get specific diagnosis time"""

    template_id: ClassVar[str] = "time-specific-diagnosis"
    description: ClassVar[str] = "Get the time of a specific diagnosis"
    tags: ClassVar[list[str]] = ["diagnosis", "time", "Condition", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} was diagnosed with {diagnosis_name} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "diagnosis_name": ["diagnosis_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.CONDITION.value
        params = {"resource_type": resource}
        diagnosis_expr = self.simple_placeholders[
            "diagnosis_name"
        ].get_fhirpath_expression(params)

        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", diagnosis_expr]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template043(Template):
    """Get specific drug prescription time"""

    template_id: ClassVar[str] = "time-specific-drug"
    description: ClassVar[str] = "Get the time of a specific drug prescription"
    tags: ClassVar[list[str]] = ["drug", "time", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} was prescribed {drug_name} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "drug_name": ["drug_name"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.MEDICATION_REQUEST.value
        params = {"resource_type": resource}
        drug_expr = self.simple_placeholders["drug_name"].get_fhirpath_expression(
            params
        )

        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", drug_expr]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query


@register_template
class Template044(Template):
    """Get drug prescription time by route"""

    template_id: ClassVar[str] = "time-drug-route"
    description: ClassVar[str] = "Get the time of a drug prescription by route"
    tags: ClassVar[list[str]] = ["drug", "route", "time", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "When was the [time_filter_exact1] time that patient {patient_id} was prescribed a medication via {drug_route} route [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "drug_route": ["drug_route"],
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
        ],
        "time_filter_exact1": [
            "exact-first",
            "exact-last",
        ],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")
        resource = ResourceType.MEDICATION_REQUEST.value
        params = {"resource_type": resource}
        route_expr = self.simple_placeholders["drug_route"].get_fhirpath_expression(
            params
        )
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'", route_expr]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".{TIME_PATHS[resource]}"

        return query
