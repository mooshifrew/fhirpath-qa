from typing import Dict, Optional
from pydantic import field_validator, model_validator
from ..base import SimplePlaceholder, register_simple_placeholder
from ..generator import GenerationContext
from typing import ClassVar
from ..valuesets import (
    ABBREVIATION_VALUESET,
    ADMISSION_ROUTE_VALUESET,
    CAREUNIT_VALUESET,
    DIAGNOSIS_NAME_VALUESET,
    DRUG_NAME_VALUESET,
    DRUG_ROUTE_VALUESET,
    GENDER_VALUESET,
    INPUT_NAME_VALUESET,
    LAB_NAME_VALUESET,
    OUTPUT_NAME_VALUESET,
    PATIENT_ID_VALUESET,
    PROCEDURE_NAME_VALUESET,
    SPEC_NAME_VALUESET,
    VITAL_NAME_VALUESET,
    ehr_sql_values,
)
from ..enums import ResourceType


@register_simple_placeholder
class BlankPlaceholder(SimplePlaceholder):
    """A placeholder for a blank value, to avoid using None."""

    name: ClassVar[str] = "blank"
    value: str = ""

    def get_fhirpath_expression(self, params: Dict):
        return ""

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "BlankPlaceholder":
        return cls()


@register_simple_placeholder
class PatientId(SimplePlaceholder):
    name: ClassVar[str] = "patient_id"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "patient_ids"):
            valueset = self.context.patient_ids
        else:
            valueset = PATIENT_ID_VALUESET

        if self.value not in valueset:
            print(  # not raising an error so that questions and answers can still be generated
                f"{self.value!r} is not a recognized patient_id."
                r"Add it to fhirpath_gen\valuesets\patient_id.json or select a different patient_id. "
            )

        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        # depending on the resource type, this would have different paths. Regardless, for
        # these queries we assume the bundle is already filtered to the patient so nothing must be done
        return f""

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "PatientId":
        patient_id = ctx.patient_id
        return cls(value=patient_id, context=ctx)


@register_simple_placeholder
class DrugName(SimplePlaceholder):
    name: ClassVar[str] = "drug_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "drug_names"):
            valueset = self.context.drug_names
        else:
            valueset = DRUG_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid drug name. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")
        # this pattern is used because identifier is a list, so this iterates through the collection
        # also to catch mixtures that include a drug --> this is different than ehrsql
        # strict pattern would be:
        # identifier.value = '{self.value}'

        if resource == ResourceType.MEDICATION.value:
            return f"identifier.where(value='{self.value}')"
        if resource == ResourceType.MEDICATION_REQUEST.value:
            return f"(medicationReference.resolve().identifier.where(value='{self.value}').exists() or medicationCodeableConcept.coding.code='{self.value}')"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "DrugName":
        drug = ctx.rng.choice(ctx.drug_names)
        return cls(value=drug, context=ctx)


@register_simple_placeholder
class ProcedureName(SimplePlaceholder):
    name: ClassVar[str] = "procedure_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "procedure_names"):
            valueset = self.context.procedure_names
        else:
            valueset = PROCEDURE_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid procedure Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")
        if resource == ResourceType.PROCEDURE.value:
            return f"code.coding.display = '{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    # code.where(coding.display.contains({self.value})) # this works for partial matches

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "ProcedureName":
        procedure = ctx.rng.choice(ctx.procedure_names)
        return cls(value=procedure, context=ctx)


@register_simple_placeholder
class AdmissionRoute(SimplePlaceholder):
    """Corresonds to AdmitSource (Encounter.hospitalization.admitSource)
    http://mimic.mit.edu/fhir/mimic/ValueSet/mimic-admit-source
    """

    name: ClassVar[str] = "admission_route"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "admission_routes"):
            valueset = self.context.admission_routes
        else:
            valueset = ADMISSION_ROUTE_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid admission route. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")
        if resource == ResourceType.ENCOUNTER.value:
            return f"hospitalization.admitSource.coding.code = '{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "AdmissionRoute":
        route = ctx.rng.choice(ctx.admission_routes)
        return cls(value=route, context=ctx)


@register_simple_placeholder
class CareUnit(SimplePlaceholder):
    """Corresponds to Location.name in MIMIC-IV on FHIR"""

    name: ClassVar[str] = "careunit"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "care_units"):
            valueset = self.context.care_units
        else:
            valueset = CAREUNIT_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid care unit. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")
        if resource == ResourceType.ENCOUNTER.value:
            return f"location.where(location.resolve().name = '{self.value}')"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "CareUnit":
        care_unit = ctx.rng.choice(ctx.care_units)
        return cls(value=care_unit, context=ctx)


@register_simple_placeholder
class DiagnosisName(SimplePlaceholder):
    """Corresponds to Condition.code.coding.display in MIMIC-IV on FHIR"""

    name: ClassVar[str] = "diagnosis_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "diagnosis_names"):
            valueset = self.context.diagnosis_names
        else:
            valueset = DIAGNOSIS_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid diagnosis name/code. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")
        if resource == ResourceType.CONDITION.value:
            return f"code.coding.display = '{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "DiagnosisName":
        diagnosis = ctx.rng.choice(ctx.diagnosis_names)
        return cls(value=diagnosis, context=ctx)


@register_simple_placeholder
class DrugRoute(SimplePlaceholder):
    """Corresponds to MedicationRequest.dosageInstruction.route in MIMIC-IV on FHIR"""

    name: ClassVar[str] = "drug_route"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "drug_routes"):
            valueset = self.context.drug_routes
        else:
            valueset = DRUG_ROUTE_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid drug route. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:

        resource = params.get("resource_type")
        if resource == ResourceType.MEDICATION_REQUEST.value:
            return f"dosageInstruction.route.coding.code = '{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "DrugRoute":
        route = ctx.rng.choice(ctx.drug_routes)
        return cls(value=route, context=ctx)


@register_simple_placeholder
class Gender(SimplePlaceholder):
    name: ClassVar[str] = "gender"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "genders"):
            valueset = self.context.genders
        else:
            valueset = GENDER_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid gender. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        # TODO: add FHIRPath for 'gender'
        return f""

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "Gender":
        gender = ctx.rng.choice(ctx.genders)
        return cls(value=gender, context=ctx)


@register_simple_placeholder
class InputName(SimplePlaceholder):
    # should be MedicationAdministration.medicationCodeableConcept -- but specifically ICU medications
    name: ClassVar[str] = "input_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "input_names"):
            valueset = self.context.input_names
        else:
            valueset = INPUT_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid input name. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")

        if resource == ResourceType.MEDICATION_ADMINISTRATION.value:
            return f"context.resolve().identifier.system='http://fhir.mimic.mit.edu/identifier/encounter-icu' and medicationCodeableConcept.coding.display = '{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "InputName":
        input_name = ctx.rng.choice(ctx.input_names)
        return cls(value=input_name, context=ctx)


@register_simple_placeholder
class LabName(SimplePlaceholder):
    name: ClassVar[str] = "lab_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "lab_names"):
            valueset = self.context.lab_names
        else:
            valueset = LAB_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid lab name. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:

        resource = params.get("resource_type")
        if resource == ResourceType.OBSERVATION.value:
            return f"category.coding.code = 'laboratory' and code.coding.display = '{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "LabName":
        lab_name = ctx.rng.choice(ctx.lab_names)
        ctx.filled[cls.name] = lab_name
        return cls(value=lab_name, context=ctx)


@register_simple_placeholder
class OutputName(SimplePlaceholder):
    name: ClassVar[str] = "output_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "output_names"):
            valueset = self.context.output_names
        else:
            valueset = OUTPUT_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid output name. Must be one of {valueset}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:

        resource = params.get("resource_type")

        if resource == ResourceType.OBSERVATION.value:
            return f"code.coding.display = '{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for OutputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "OutputName":
        output_name = ctx.rng.choice(ctx.output_names)
        return cls(value=output_name, context=ctx)


@register_simple_placeholder
class SpecName(SimplePlaceholder):
    name: ClassVar[str] = "spec_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "spec_names"):
            valueset = self.context.spec_names
        else:
            valueset = SPEC_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid specimen name. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")
        # NOTE: For mimic on fhir, specimens use two code systems:
        #   http://fhir.mimic.mit.edu/CodeSystem/spec-type-desc -- NL is at type.coding.code
        #   http://fhir.mimic.mit.edu/CodeSystem/lab-fluid -- NL is at type.coding.display
        if resource == ResourceType.OBSERVATION.value:
            return f"specimen.resolve().type.coding.where((code = '{self.value}') or (display = '{self.value}')).exists()"
        if resource == ResourceType.SPECIMEN.value:
            return (
                f"type.coding.code='{self.value}' or type.coding.display='{self.value}'"
            )
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for InputName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "SpecName":
        spec = ctx.rng.choice(ctx.spec_names)
        return cls(value=spec, context=ctx)


@register_simple_placeholder
class VitalName(SimplePlaceholder):
    name: ClassVar[str] = "vital_name"
    value: str

    @model_validator(mode="after")
    def check_allowed(self):
        # Use context valueset if available, otherwise fall back to static valueset
        if self.context and hasattr(self.context, "vital_names"):
            valueset = self.context.vital_names
        else:
            valueset = VITAL_NAME_VALUESET

        if self.value not in valueset:
            raise ValueError(
                f"{self.value!r} is not a valid vital name. Must be one of {sorted(valueset)}"
            )
        return self

    def get_fhirpath_expression(self, params: Dict) -> str:
        resource = params.get("resource_type")

        if resource == ResourceType.OBSERVATION.value:
            return f"code.coding.display='{self.value}'"
        else:
            raise NotImplementedError(
                f"resource {resource} not implemented for VitalName"
            )

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "VitalName":
        vital_name = ctx.rng.choice(ctx.vital_names)
        ctx.filled[cls.name] = vital_name
        return cls(value=vital_name, context=ctx)


@register_simple_placeholder
class VitalValue(SimplePlaceholder):
    name: ClassVar[str] = "vital_value"
    value: float  # not validated so select properly

    def get_fhirpath_expression(self, params):
        resource = params.get("resource_type", None)

        if resource == ResourceType.OBSERVATION.value:
            return f"valueQuantity.value"
        if not resource:
            return f"{self.value:.1f}"

    def get_nl_expr(self):
        return f"{self.value:.1f}"

    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "VitalValue":
        vital_name = ctx.filled.get("vital_name", None)
        if vital_name:
            # TODO: choose based on vital reference ranges or something
            # for now, just select from values used in ehrsql
            value_options = ehr_sql_values["vital_value_mapping"].get(vital_name, None)
            if value_options:
                value = ctx.rng.choice(value_options)
            else:
                value = "50.0"

            return cls(value=float(value), context=ctx)

        else:
            raise ("Vital Name is not known while trying to generate the vital value!")


@register_simple_placeholder
class LabValue(SimplePlaceholder):
    name: ClassVar[str] = "lab_value"
    value: float  # not validated so select properly

    def get_fhirpath_expression(self, params):
        resource = params.get("resource_type", None)

        if resource == ResourceType.OBSERVATION.value:
            return f"valueQuantity.value"
        if not resource:
            return f"{self.value:.1f}"

    def get_nl_expr(self):
        return f"{self.value:.1f}"

    @classmethod
    def random_instance(cls, ctx):
        lab_name = ctx.filled.get("lab_name", None)
        if lab_name:
            # TODO: choose based on lab reference ranges or something
            # for now, just select from values used in ehrsql
            value_options = ehr_sql_values["lab_value_mapping"].get(lab_name, None)
            if value_options:
                value = ctx.rng.choice(value_options)
            else:
                value = "50.0"

            return cls(value=float(value), context=ctx)

        else:
            raise ("Lab Name is not known when trying to generate Lab Value")
