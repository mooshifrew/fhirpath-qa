from typing import ClassVar, Dict, List

from fhirpath_gen.base import (
    register_template,
    Template,
)

from fhirpath_gen.enums import ResourceType
from fhirpath_gen.utils import TIME_PATHS


@register_template
class Template045(Template):
    """Get patient birth date"""

    template_id: ClassVar[str] = "patient-birth-date"
    description: ClassVar[str] = "Get the birth date of a patient"
    tags: ClassVar[list[str]] = ["patient", "birth", "Patient", "ehrsql"]

    question_template: ClassVar[str] = (
        "What is the date of birth of patient {patient_id}?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = {}
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        resource = ResourceType.PATIENT.value
        return f"Bundle.entry.resource.where(resourceType='{resource}').birthDate"


@register_template
class Template046(Template):
    """Get patient gender"""

    template_id: ClassVar[str] = "patient-gender"
    description: ClassVar[str] = "Get the gender of a patient"
    tags: ClassVar[list[str]] = ["patient", "gender", "Patient", "ehrsql"]

    question_template: ClassVar[str] = "What is the gender of patient {patient_id}?"

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = {}
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        resource = ResourceType.PATIENT.value
        return f"Bundle.entry.resource.where(resourceType='{resource}').gender"


@register_template
class Template047(Template):
    """Get care unit"""

    template_id: ClassVar[str] = "careunit"
    description: ClassVar[str] = "Get the care unit of a patient"
    tags: ClassVar[list[str]] = ["careunit", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the [time_filter_exact1] careunit of patient {patient_id} [time_filter_global1]?"
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
        resource = ResourceType.ENCOUNTER.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += f".location.{exact_expr}.location.resolve().name"

        return query


@register_template
class Template048(Template):
    """Get admission type"""

    template_id: ClassVar[str] = "admission-type"
    description: ClassVar[str] = "Get the hospital admission type of a patient"
    tags: ClassVar[list[str]] = ["admission", "type", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the [time_filter_exact1] hospital admission type of patient {patient_id}?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
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
        params = {"resource_type": resource}
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        query = (
            f"Bundle.entry.resource.where(resourceType='{resource}' and partOf.empty())"
        )
        if exact_expr:
            query += f".{exact_expr}"
        query += ".type.coding.display"

        return query


@register_template
class Template049(Template):
    """Get vital measurement"""

    template_id: ClassVar[str] = "vital-measurement"
    description: ClassVar[str] = "Get a vital measurement of a patient"
    tags: ClassVar[list[str]] = ["vital", "measurement", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the [time_filter_exact1] measured {vital_name} of patient {patient_id} [time_filter_global1]?"
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
        query += ".valueQuantity.value"

        return query


@register_template
class Template050(Template):
    """Get lab measurement"""

    template_id: ClassVar[str] = "lab-measurement"
    description: ClassVar[str] = "Get a lab test measurement of a patient"
    tags: ClassVar[list[str]] = ["lab", "measurement", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the [time_filter_exact1] measured value of a {lab_name} lab test of patient {patient_id} [time_filter_global1]?"
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
        query += ".valueQuantity.value"

        return query


@register_template
class Template051(Template):
    """Get weight"""

    template_id: ClassVar[str] = "weight"
    description: ClassVar[str] = "Get the weight of a patient"
    tags: ClassVar[list[str]] = ["weight", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the [time_filter_exact1] measured weight of patient {patient_id} [time_filter_global1]?"
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
            # "code.coding.code='29463-7'",  # LOINC code for body weight -- not used for mimic
            "code.coding.display in {'Daily Weight', 'Admission Weight (lbs.)', 'Admission Weight (Kg)'}",
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += ".select(valueQuantity.value | valueQuantity.unit)"

        return query


@register_template
class Template052(Template):
    """Get drug dose"""

    template_id: ClassVar[str] = "drug-dose"
    description: ClassVar[str] = "Get the dose of a specific drug"
    tags: ClassVar[list[str]] = ["drug", "dose", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the dose of {drug_name} that patient {patient_id} was [time_filter_exact1] prescribed [time_filter_global1]?"
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
        query += ".dosageInstruction.doseAndRate.doseQuantity.value"

        return query


@register_template
class Template053(Template):
    """Get diagnosis name"""

    template_id: ClassVar[str] = "diagnosis-name"
    description: ClassVar[str] = "Get the name of a diagnosis"
    tags: ClassVar[list[str]] = ["diagnosis", "name", "Condition", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the name of the diagnosis that patient {patient_id} [time_filter_exact1] received [time_filter_global1]?"
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
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)

        partial_time_expr = TIME_PATHS[resource]

        if "first" in exact_expr:
            first_or_last = "first()"
        elif "last" in exact_expr:
            first_or_last = "last()"

        where_parts.append(
            f"{partial_time_expr} =%context.Bundle.entry.resource.where({where_parts[0]} and {time_expr}).{'.'.join(partial_time_expr.split('.')[:-1])}.select(toDateTime()).sort().{first_or_last}"
        )
        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        query += ".code.coding.display"

        return query


@register_template
class Template054(Template):
    """Get drug name"""

    template_id: ClassVar[str] = "drug-name"
    description: ClassVar[str] = "Get the name of a drug"
    tags: ClassVar[list[str]] = ["drug", "name", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the name of the drug that patient {patient_id} was [time_filter_exact1] prescribed [time_filter_global1]?"
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
        query += ".select(medicationReference.resolve().identifier.value | medicationCodeableConcept.coding.code)"

        return query


@register_template
class Template055(Template):
    """Get drug name by route"""

    template_id: ClassVar[str] = "drug-name-route"
    description: ClassVar[str] = (
        "Get the name of a drug prescribed via a specific route"
    )
    tags: ClassVar[list[str]] = ["drug", "name", "route", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the name of the drug that patient {patient_id} was [time_filter_exact1] prescribed via {drug_route} route [time_filter_global1]?"
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
        query += ".select(medicationReference.resolve().identifier.value | medicationCodeableConcept.coding.code)"

        return query


@register_template
class Template056(Template):
    """Get lab test name"""

    template_id: ClassVar[str] = "lab-name"
    description: ClassVar[str] = "Get the name of a lab test"
    tags: ClassVar[list[str]] = ["lab", "name", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the name of the lab test that patient {patient_id} [time_filter_exact1] received [time_filter_global1]?"
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
            "category.coding.code='laboratory'",
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += ".code.coding.display"

        return query


@register_template
class Template057(Template):
    """Get microbiology test name"""

    template_id: ClassVar[str] = "micro-test-name"
    description: ClassVar[str] = "Get the name of a microbiology test"
    tags: ClassVar[list[str]] = [
        "microbiology",
        "test",
        "name",
        "Observation",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "What was the name of the microbiology test that patient {patient_id} [time_filter_exact1] received [time_filter_global1]?"
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
            "code.coding.system = 'http://fhir.mimic.mit.edu/CodeSystem/microbiology-test'",
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += ".code.coding.display"

        return query


@register_template
class Template058(Template):
    """Get output name"""

    template_id: ClassVar[str] = "output-name"
    description: ClassVar[str] = "Get the name of an output"
    tags: ClassVar[list[str]] = ["output", "name", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the name of the output that patient {patient_id} [time_filter_exact1] had [time_filter_global1]?"
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
            "category.coding.code='Output'",
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += ".code.coding.display"

        return query


@register_template
class Template059(Template):
    """Get procedure name"""

    template_id: ClassVar[str] = "procedure-name"
    description: ClassVar[str] = "Get the name of a procedure"
    tags: ClassVar[list[str]] = ["procedure", "name", "Procedure", "ehrsql"]

    question_template: ClassVar[str] = (
        "What was the name of the procedure that patient {patient_id} [time_filter_exact1] received [time_filter_global1]?"
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
        query += ".code.coding.display"

        return query


@register_template
class Template060(Template):
    """Get specimen name"""

    template_id: ClassVar[str] = "specimen-name"
    description: ClassVar[str] = "Get the name of a specimen"
    tags: ClassVar[list[str]] = [
        "specimen",
        "name",
        "Specimen",
        "Observation",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "What was the name of the specimen that patient {patient_id} was [time_filter_exact1] tested [time_filter_global1]?"
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

        where_parts = [f"resourceType='{resource}'", "specimen.exists()"]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += ".specimen.resolve().type.coding.select(code | display)"

        return query


@register_template
class Template061(Template):
    """Get organism name"""

    template_id: ClassVar[str] = "organism-name"
    description: ClassVar[str] = "Get the organism name found in a microbiology test"
    tags: ClassVar[list[str]] = [
        "organism",
        "name",
        "microbiology",
        "Observation",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "What was the organism name found in the [time_filter_exact1] {spec_name} microbiology test of patient {patient_id} [time_filter_global1]?"
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
        params = {"resource_type": resource}

        spec_expr = self.simple_placeholders["spec_name"].get_fhirpath_expression(
            params
        )
        time_expr = t_filter.get_fhirpath_expression(params) if t_filter else ""
        exact_expr = t_exact.get_fhirpath_expression(params) if t_exact else ""

        where_parts = [
            f"resourceType='{resource}'",
            "category.coding.code='laboratory'",
            spec_expr,
            "hasMember.exists()",
        ]
        if time_expr:
            where_parts.append(time_expr)

        query = f"Bundle.entry.resource.where({' and '.join(where_parts)})"
        if exact_expr:
            query += f".{exact_expr}"
        query += ".hasMember.resolve().code.coding.display"

        return query
