from typing import ClassVar, Dict, List

from fhirpath_gen.base import (
    register_template,
    Template,
)

from fhirpath_gen.enums import ResourceType


@register_template
class Template001(Template):

    template_id: ClassVar[str] = "count-drugs-prescribed"
    description: ClassVar[str] = (
        "Count the number of unique drugs prescribed to a patient in a given time frame"
    )
    tags: ClassVar[list[str]] = [
        "drugs",
        "count",
        "MedicationRequest",
        "Medication",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "Count the number of drugs patient {patient_id} were prescribed [time_filter_global1]."
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
        resource = ResourceType.MEDICATION_REQUEST.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        where_parts = [f"resourceType='{resource}'"]
        if time_expr:  # only add if not empty
            where_parts.append(time_expr)

        return (
            "Bundle.entry.resource.where("
            + " and ".join(where_parts)
            + ").select(medicationReference.resolve() | medicationCodeableConcept)"
            ".distinct().count()"
        )


@register_template
class Template002(Template):
    """Hospital visits are the base encounters, so only count encounters without a 'partOf' reference"""

    template_id: ClassVar[str] = "count-hospital-visits"
    description: ClassVar[str] = (
        "Count the number of hospital visits of a patient in a given time frame"
    )
    tags: ClassVar[list[str]] = ["visits", "count", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "Count the number of hospital visits of patient {patient_id} [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template001.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.ENCOUNTER.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        where_parts = [f"resourceType='{resource}'", "partOf.empty()"]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").count()"


@register_template
class Template003(Template):
    template_id: ClassVar[str] = "count-icu-visits"
    description: ClassVar[str] = (
        "Count the number of ICU visits of a patient in a given time frame"
    )
    tags: ClassVar[list[str]] = ["icu", "visits", "count", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "Count the number of ICU visits of patient {patient_id} [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template001.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.ENCOUNTER.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        where_parts = [
            f"resourceType='{resource}'",
            "identifier.system = 'http://fhir.mimic.mit.edu/identifier/encounter-icu'",
        ]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").count()"


@register_template
class Template004(Template):
    template_id: ClassVar[str] = "count-input-intake-events"
    description: ClassVar[str] = (
        "Count the number of intake events for a specific input in a given time frame"
    )
    tags: ClassVar[list[str]] = [
        "inputs",
        "count",
        "MedicationAdministration",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "Count the number of times that patient {patient_id} had a {input_name} intake [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "input_name": ["input_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template001.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.MEDICATION_ADMINISTRATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        input_expr = self.simple_placeholders["input_name"].get_fhirpath_expression(
            params
        )
        where_parts = [f"resourceType='{resource}'", input_expr]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").count()"


@register_template
class Template005(Template):
    template_id: ClassVar[str] = "count-output-events"
    description: ClassVar[str] = (
        "Count the number of output events for a specific output in a given time frame"
    )
    tags: ClassVar[list[str]] = ["outputs", "count", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Count the number of times that patient {patient_id} had a {output_name} output [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "output_name": ["output_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template001.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        output_expr = self.simple_placeholders["output_name"].get_fhirpath_expression(
            params
        )
        where_parts = [f"resourceType='{resource}'", output_expr]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").count()"


@register_template
class Template006(Template):
    template_id: ClassVar[str] = "count-lab-test-events"
    description: ClassVar[str] = (
        "Count the number of times a specific lab test was performed for a patient"
    )
    tags: ClassVar[list[str]] = ["labs", "tests", "count", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Count the number of times that patient {patient_id} received a {lab_name} lab test [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "lab_name": ["lab_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template001.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        lab_expr = self.simple_placeholders["lab_name"].get_fhirpath_expression(params)
        where_parts = [f"resourceType='{resource}'", lab_expr]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").count()"


@register_template
class Template007(Template):
    template_id: ClassVar[str] = "count-procedure-events"
    description: ClassVar[str] = (
        "Count the number of times a patient received a procedure in a given time frame"
    )
    tags: ClassVar[list[str]] = ["count", "Procedure", "ehrsql"]

    question_template: ClassVar[str] = (
        "Count the number of times that patient {patient_id} received a {procedure_name} procedure [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "procedure_name": ["procedure_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template001.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.PROCEDURE.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        proc_expr = self.simple_placeholders["procedure_name"].get_fhirpath_expression(
            params
        )
        where_parts = [f"resourceType='{resource}'", proc_expr]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").count()"


@register_template
class Template008(Template):
    template_id: ClassVar[str] = "count-specific-drug-prescriptions"
    description: ClassVar[str] = (
        "Count the number of times a patient was prescribed a specific drug"
    )
    tags: ClassVar[list[str]] = ["drugs", "count", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "Count the number of times that patient {patient_id} were prescribed {drug_name} [time_filter_global1]."
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "drug_name": ["drug_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template001.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.MEDICATION_REQUEST.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        drug_expr = self.simple_placeholders["drug_name"].get_fhirpath_expression(
            params
        )
        where_parts = [f"resourceType='{resource}'", drug_expr]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").count()"
