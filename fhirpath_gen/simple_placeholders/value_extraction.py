"""
Functions to extract all values for each placeholder type from patient bundles.
"""

from typing import Dict, List, Optional
from ..enums import ResourceType


def get_value_extraction_query(
    placeholder_name: str, resource_type: Optional[str] = None
) -> str:
    """
    Generate a FHIRPath query to extract all values for a given placeholder type.

    Args:
        placeholder_name: The name of the placeholder class (e.g., 'drug_name', 'procedure_name')
        resource_type: Optional resource type to filter by. If None, returns queries for all applicable resource types.

    Returns:
        FHIRPath query string to extract all values for the placeholder
    """

    # Map placeholder names to their value extraction queries
    queries = {
        "blank": "",
        "patient_id": "",  # Patient ID is already filtered in the bundle
        "drug_name": {
            ResourceType.MEDICATION.value: "Bundle.entry.resource.where(resourceType='Medication').identifier.value",
            ResourceType.MEDICATION_REQUEST.value: "Bundle.entry.resource.where(resourceType='MedicationRequest').select(medicationReference.resolve().identifier.value | medicationCodeableConcept.coding.code)",
        },
        "procedure_name": {
            ResourceType.PROCEDURE.value: "Bundle.entry.resource.where(resourceType='Procedure').code.coding.display"
        },
        "admission_route": {
            ResourceType.ENCOUNTER.value: "Bundle.entry.resource.where(resourceType='Encounter').hospitalization.admitSource.coding.code"
        },
        "careunit": {
            ResourceType.ENCOUNTER.value: "Bundle.entry.resource.where(resourceType='Encounter').location.location.resolve().name"
        },
        "diagnosis_name": {
            ResourceType.CONDITION.value: "Bundle.entry.resource.where(resourceType='Condition').code.coding.display"
        },
        "drug_route": {
            ResourceType.MEDICATION_REQUEST.value: "Bundle.entry.resource.where(resourceType='MedicationRequest').dosageInstruction.route.coding.code"
        },
        "gender": {
            ResourceType.PATIENT.value: "Bundle.entry.resource.where(resourceType='Patient').gender"
        },
        "input_name": {
            ResourceType.MEDICATION_ADMINISTRATION.value: "Bundle.entry.resource.where(resourceType='MedicationAdministration').where(context.resolve().identifier.system='http://fhir.mimic.mit.edu/identifier/encounter-icu').medicationCodeableConcept.coding.display"
        },
        "lab_name": {
            ResourceType.OBSERVATION.value: "Bundle.entry.resource.where(resourceType='Observation').where(category.coding.code='laboratory').code.coding.display"
        },
        "output_name": {
            ResourceType.OBSERVATION.value: "Bundle.entry.resource.where(resourceType='Observation' and category.coding.code='Output').code.coding.display"
        },
        "spec_name": {
            ResourceType.SPECIMEN.value: "Bundle.entry.resource.where(resourceType='Specimen').type.coding.select(code | display)",
        },
        "vital_name": {
            ResourceType.OBSERVATION.value: "Bundle.entry.resource.where(resourceType='Observation').code.coding.display"
        },
        "vital_value": {
            ResourceType.OBSERVATION.value: "Bundle.entry.resource.where(resourceType='Observation').valueQuantity.value"
        },
        "lab_value": {
            ResourceType.OBSERVATION.value: "Bundle.entry.resource.where(resourceType='Observation').where(category.coding.code='laboratory').valueQuantity.value"
        },
    }

    if placeholder_name not in queries:
        raise ValueError(f"Unknown placeholder name: {placeholder_name}")

    query = queries[placeholder_name]

    # Handle special cases
    if placeholder_name == "blank":
        return ""

    if placeholder_name == "patient_id":
        return ""  # Patient ID is already filtered in the bundle

    # If resource_type is specified, return the query for that specific resource type
    if resource_type and isinstance(query, dict):
        if resource_type in query:
            return query[resource_type]
        else:
            raise ValueError(
                f"Resource type {resource_type} not supported for placeholder {placeholder_name}"
            )

    # If no resource_type specified, return all applicable queries
    if isinstance(query, dict):
        return query
    else:
        return query


def get_all_value_queries_for_placeholder(placeholder_name: str) -> Dict[str, str]:
    """
    Get all possible value extraction queries for a placeholder across all resource types.

    Args:
        placeholder_name: The name of the placeholder class

    Returns:
        Dictionary mapping resource types to their corresponding FHIRPath queries
    """
    query = get_value_extraction_query(placeholder_name)

    if isinstance(query, dict):
        return query
    elif isinstance(query, str):
        return {"default": query}
    else:
        return {}


def get_placeholder_value_queries() -> Dict[str, Dict[str, str]]:
    """
    Get all value extraction queries for all placeholder types.

    Returns:
        Dictionary mapping placeholder names to their resource type queries
    """
    placeholder_names = [
        "blank",
        "patient_id",
        "drug_name",
        "procedure_name",
        "admission_route",
        "careunit",
        "diagnosis_name",
        "drug_route",
        "gender",
        "input_name",
        "lab_name",
        "output_name",
        "spec_name",
        "vital_name",
        "vital_value",
        "lab_value",
    ]

    result = {}
    for name in placeholder_names:
        result[name] = get_all_value_queries_for_placeholder(name)

    return result


# Convenience functions for specific placeholder types
def get_drug_name_values(resource_type: str = None) -> str:
    """Get FHIRPath query to extract all drug names from a patient bundle."""
    return get_value_extraction_query("drug_name", resource_type)


def get_procedure_name_values() -> str:
    """Get FHIRPath query to extract all procedure names from a patient bundle."""
    return get_value_extraction_query("procedure_name", ResourceType.PROCEDURE.value)


def get_diagnosis_name_values() -> str:
    """Get FHIRPath query to extract all diagnosis names from a patient bundle."""
    return get_value_extraction_query("diagnosis_name", ResourceType.CONDITION.value)


def get_lab_name_values() -> str:
    """Get FHIRPath query to extract all lab names from a patient bundle."""
    return get_value_extraction_query("lab_name", ResourceType.OBSERVATION.value)


def get_vital_name_values() -> str:
    """Get FHIRPath query to extract all vital names from a patient bundle."""
    return get_value_extraction_query("vital_name", ResourceType.OBSERVATION.value)


def get_care_unit_values() -> str:
    """Get FHIRPath query to extract all care unit names from a patient bundle."""
    return get_value_extraction_query("careunit", ResourceType.ENCOUNTER.value)


def get_admission_route_values() -> str:
    """Get FHIRPath query to extract all admission routes from a patient bundle."""
    return get_value_extraction_query("admission_route", ResourceType.ENCOUNTER.value)


def get_drug_route_values() -> str:
    """Get FHIRPath query to extract all drug routes from a patient bundle."""
    return get_value_extraction_query(
        "drug_route", ResourceType.MEDICATION_REQUEST.value
    )


def get_input_name_values() -> str:
    """Get FHIRPath query to extract all input names from a patient bundle."""
    return get_value_extraction_query(
        "input_name", ResourceType.MEDICATION_ADMINISTRATION.value
    )


def get_output_name_values() -> str:
    """Get FHIRPath query to extract all output names from a patient bundle."""
    return get_value_extraction_query("output_name", ResourceType.OBSERVATION.value)


def get_spec_name_values(resource_type: str = None) -> str:
    """Get FHIRPath query to extract all specimen names from a patient bundle."""
    return get_value_extraction_query("spec_name", resource_type)


def get_gender_values() -> str:
    """Get FHIRPath query to extract gender from a patient bundle."""
    return get_value_extraction_query("gender", ResourceType.PATIENT.value)


def get_vital_value_values() -> str:
    """Get FHIRPath query to extract all vital values from a patient bundle."""
    return get_value_extraction_query("vital_value", ResourceType.OBSERVATION.value)


def get_lab_value_values() -> str:
    """Get FHIRPath query to extract all lab values from a patient bundle."""
    return get_value_extraction_query("lab_value", ResourceType.OBSERVATION.value)
