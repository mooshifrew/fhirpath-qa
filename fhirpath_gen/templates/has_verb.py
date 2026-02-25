from typing import ClassVar, Dict, List

from fhirpath_gen.base import (
    register_template,
    Template,
)

from fhirpath_gen.enums import ResourceType


@register_template
class Template009(Template):

    template_id: ClassVar[str] = "has-hospital-admission"
    description: ClassVar[str] = (
        "Check if the patient has been admitted in the given time frame"
    )
    tags: ClassVar[list[str]] = [
        "has_verb",
        "admission",
        "Encounter",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} been admitted to the hospital [time_filter_global1]?"
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
        time_expr = t_filter.get_fhirpath_expression(params)
        where_parts = [
            f"resourceType='{resource}'",
            "partOf.empty()",  # only pulls the root encounters, which correspond to an admission
        ]
        if time_expr:  # only add if not empty
            where_parts.append(time_expr)

        return (
            "Bundle.entry.resource.where("
            + " and ".join(where_parts)
            + ").exists()"  # just check existence for boolean question
        )


@register_template
class Template010(Template):
    template_id: ClassVar[str] = "has-diagnosis"
    description: ClassVar[str] = "Check if the patient has a specific diagnosis"
    tags: ClassVar[list[str]] = ["has_verb", "diagnosis", "Condition", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} been diagnosed with {diagnosis_name} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "diagnosis_name": ["diagnosis_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.CONDITION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        diag_expr = self.simple_placeholders["diagnosis_name"].get_fhirpath_expression(
            params
        )
        where_parts = [f"resourceType='{resource}'", diag_expr]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template011(Template):
    template_id: ClassVar[str] = "has-drug-prescribed"
    description: ClassVar[str] = (
        "Check if the patient has been prescribed a specific drug"
    )
    tags: ClassVar[list[str]] = ["has_verb", "drug", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} been prescribed {drug_name} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "drug_name": ["drug_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
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
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template012(Template):
    template_id: ClassVar[str] = "has-multiple-drugs-or"
    description: ClassVar[str] = (
        "Check if the patient has been prescribed any of multiple drugs"
    )
    tags: ClassVar[list[str]] = ["has_verb", "drug", "MedicationRequest", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} been prescribed {drug_name1}, {drug_name2}, or {drug_name3} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "drug_name1": ["drug_name"],
        "drug_name2": ["drug_name"],
        "drug_name3": ["drug_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.MEDICATION_REQUEST.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        exprs = [
            self.simple_placeholders["drug_name1"].get_fhirpath_expression(params),
            self.simple_placeholders["drug_name2"].get_fhirpath_expression(params),
            self.simple_placeholders["drug_name3"].get_fhirpath_expression(params),
        ]
        where_parts = [f"resourceType='{resource}'", "(" + " or ".join(exprs) + ")"]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template013(Template):
    template_id: ClassVar[str] = "has-any-medication"
    description: ClassVar[str] = (
        "Check if the patient has been prescribed any medication"
    )
    tags: ClassVar[list[str]] = [
        "has_verb",
        "medication",
        "MedicationRequest",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} been prescribed any medication [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.MEDICATION_REQUEST.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template014(Template):
    template_id: ClassVar[str] = "has-emergency-room-visit"
    description: ClassVar[str] = "Check if the patient has had an emergency room visit"
    tags: ClassVar[list[str]] = ["has_verb", "er", "Encounter", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} been to an emergency room [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.ENCOUNTER.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        where_parts = [f"resourceType='{resource}'", "class.code='EMER'"]
        if time_expr:
            where_parts.append(time_expr)
        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template015(Template):
    template_id: ClassVar[str] = "has-input-intake"
    description: ClassVar[str] = (
        "Check if the patient had any specific input intake events"
    )
    tags: ClassVar[list[str]] = [
        "has_verb",
        "inputs",
        "MedicationAdministration",
        "ehrsql",
    ]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} had any {input_name} intake [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "input_name": ["input_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
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

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template016(Template):
    template_id: ClassVar[str] = "has-output-events"
    description: ClassVar[str] = "Check if the patient had any specific output events"
    tags: ClassVar[list[str]] = ["has_verb", "outputs", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} had any {output_name} output [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "output_name": ["output_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
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

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template017(Template):
    template_id: ClassVar[str] = "has-micro-test-specific"
    description: ClassVar[str] = (
        "Check if the patient had any microbiology result for a specific specimen/test"
    )
    tags: ClassVar[list[str]] = ["has_verb", "microbiology", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} had any {spec_name} microbiology test result [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "spec_name": ["spec_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        # spec_name relates to the specimen in ObservationMicroTest. Results are in ObservationMicroOrg which
        # link back to the ObservationMicroTest
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        spec_expr = self.simple_placeholders["spec_name"].get_fhirpath_expression(
            params
        )
        where_parts = [
            f"resourceType='{resource}'",
            "code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism'",
            f"derivedFrom.resolve().{spec_expr}",
        ]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template018(Template):
    template_id: ClassVar[str] = "has-micro-test-any"
    description: ClassVar[str] = "Check if the patient had any microbiology test result"
    tags: ClassVar[list[str]] = ["has_verb", "microbiology", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} had any microbiology test result [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)

        where_parts = [
            f"resourceType='{resource}'",
            "code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism'",
        ]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template019(Template):
    template_id: ClassVar[str] = "has-lab-test"
    description: ClassVar[str] = "Check if the patient received a specific lab test"
    tags: ClassVar[list[str]] = ["has_verb", "labs", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} received a {lab_name} lab test [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "lab_name": ["lab_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        # Mirrors Template006 (count-lab-test-events) but returns exists()
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)
        lab_expr = self.simple_placeholders["lab_name"].get_fhirpath_expression(params)

        where_parts = [f"resourceType='{resource}'", lab_expr]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template020(Template):
    template_id: ClassVar[str] = "has-procedure"
    description: ClassVar[str] = "Check if the patient received a specific procedure"
    tags: ClassVar[list[str]] = ["has_verb", "Procedure", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} received a {procedure_name} procedure [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "procedure_name": ["procedure_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        # Mirrors Template007 (count-procedure-events) but returns exists()
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

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template021(Template):
    template_id: ClassVar[str] = "has-any-diagnosis"
    description: ClassVar[str] = "Check if the patient received any diagnosis"
    tags: ClassVar[list[str]] = ["has_verb", "diagnosis", "Condition", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} received any diagnosis [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.CONDITION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)

        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template022(Template):
    template_id: ClassVar[str] = "has-any-lab-test"
    description: ClassVar[str] = "Check if the patient received any lab test"
    tags: ClassVar[list[str]] = ["has_verb", "labs", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} received any lab test [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)

        where_parts = [
            f"resourceType='{resource}'",
            "category.coding.code = 'laboratory'",
        ]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template023(Template):
    template_id: ClassVar[str] = "has-any-procedure"
    description: ClassVar[str] = "Check if the patient received any procedure"
    tags: ClassVar[list[str]] = ["has_verb", "Procedure", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb patient {patient_id} received any procedure [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {"patient_id": ["patient_id"]}
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")
        resource = ResourceType.PROCEDURE.value
        params = {"resource_type": resource}
        time_expr = t_filter.get_fhirpath_expression(params)

        where_parts = [f"resourceType='{resource}'"]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template024(Template):
    template_id: ClassVar[str] = "has-vital-comparison"
    description: ClassVar[str] = (
        "Check if a vital sign has ever compared against a threshold"
    )
    tags: ClassVar[list[str]] = ["has_verb", "vitals", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb the {vital_name} of patient {patient_id} been ever [comparison] than {vital_value} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "vital_name": ["vital_name"],
        "vital_value": ["vital_value"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    # Expect an operation placeholder that resolves to a comparison operator or predicate
    op_allowed: ClassVar[Dict[str, List[str]]] = {"comparison": ["comparison"]}

    def compile_query(self) -> str:
        t_filter = self.time_placeholders.get("time_filter_global1")

        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}

        time_expr = t_filter.get_fhirpath_expression(params)
        vital_expr = self.simple_placeholders["vital_name"].get_fhirpath_expression(
            params
        )
        value_expr = self.simple_placeholders["vital_value"].get_fhirpath_expression(
            params
        )
        vital_value = self.simple_placeholders["vital_value"].value
        comp_op = self.operation_placeholders["comparison"].get_fhirpath_expression(
            params
        )

        comparison_expr = f"({value_expr} {comp_op} {vital_value})"

        where_parts = [f"resourceType='{resource}'", vital_expr, comparison_expr]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template025(Template):
    # Note that there are sometimes interpretations in the record such as
    # https://mimic.mit.edu/fhir/ValueSet-mimic-lab-interpretation.html
    # However, here I will manually check if the value is in the reference range
    template_id: ClassVar[str] = "has-normal-vital"
    description: ClassVar[str] = (
        "Check if a vital sign has ever been within its normal reference range"
    )
    tags: ClassVar[list[str]] = ["has_verb", "vitals", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb the {vital_name} of patient {patient_id} been normal [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "vital_name": ["vital_name"],
    }
    t_allowed: ClassVar[Dict[str, List[str]]] = Template009.t_allowed
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        # "Normal" → valueQuantity inside referenceRange bounds when present
        t_filter = self.time_placeholders.get("time_filter_global1")

        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}

        time_expr = t_filter.get_fhirpath_expression(params)
        vital_expr = self.simple_placeholders["vital_name"].get_fhirpath_expression(
            params
        )

        normal_predicate = (  # TODO: retest this once patched https://github.com/octofhir/fhirpath-rs/issues/35
            "("
            "valueQuantity.value.convertsToQuantity() and "
            "(referenceRange.low.value.exists() implies valueQuantity.value >= referenceRange.low.value) and "
            "(referenceRange.high.value.exists() implies valueQuantity.value <= referenceRange.high.value)"
            ")"
        )

        where_parts = [f"resourceType='{resource}'", vital_expr, normal_predicate]
        if time_expr:
            where_parts.append(time_expr)

        return "Bundle.entry.resource.where(" + " and ".join(where_parts) + ").exists()"


@register_template
class Template026(Template):
    template_id: ClassVar[str] = "has-organism-found"
    description: ClassVar[str] = (
        "Check if any organism was found in the specified (exact-timed) microbiology test, within the global time window"
    )
    tags: ClassVar[list[str]] = ["has_verb", "microbiology", "Observation", "ehrsql"]

    question_template: ClassVar[str] = (
        "Has_verb there been any organism found in the [time_filter_exact1] {spec_name} microbiology test of patient {patient_id} [time_filter_global1]?"
    )

    sp_allowed: ClassVar[Dict[str, List[str]]] = {
        "patient_id": ["patient_id"],
        "spec_name": ["spec_name"],
    }
    # Needs BOTH an exact-time filter and the global filter
    t_allowed: ClassVar[Dict[str, List[str]]] = {
        "time_filter_global1": Template009.t_allowed["time_filter_global1"],
        "time_filter_exact1": ["exact-first", "exact-last"],
    }
    op_allowed: ClassVar[Dict[str, List[str]]] = {}

    def compile_query(self) -> str:
        # Strategy:
        # 1.  Filter by Observation, ObsMicroTest, global time filter
        # 2.  Make selection with exact time filter
        # 3.  Check existence of an organism
        # - exact-time filter (time_filter_exact1) to pin the specimen/test occurrence
        # - global time filter (time_filter_global1)
        # - spec_name narrowing to the desired microbiology test/specimen
        # - organism presence (keep predicate general; refine in placeholder if desired)
        t_global = self.time_placeholders.get("time_filter_global1")
        t_exact = self.time_placeholders.get("time_filter_exact1")

        resource = ResourceType.OBSERVATION.value
        params = {"resource_type": resource}

        time_expr_global = t_global.get_fhirpath_expression(params) if t_global else ""
        time_expr_exact = t_exact.get_fhirpath_expression(params) if t_exact else ""
        spec_expr = self.simple_placeholders["spec_name"].get_fhirpath_expression(
            params
        )

        # Generic organism-present signal; adjust to your data conventions if needed
        org_exists_expr = "where(hasMember.exists() and hasMember.resolve().code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism').exists()"

        where_parts = [f"resourceType='{resource}'", spec_expr]
        if time_expr_global:
            where_parts.append(time_expr_global)

        return (
            "Bundle.entry.resource.where("
            + " and ".join(where_parts)
            + f").{time_expr_exact}.{org_exists_expr}"
        )
