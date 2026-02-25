from enum import Enum


## Related to Time Expressions
class TimeFilterType(str, Enum):
    GLOBAL = "global"
    WITHIN = "within"
    EXACT = "exact"


class TimeExpressionType(str, Enum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    MIXED = "mixed"


class TimeUnit(str, Enum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    HOSPITAL_VISIT = "hospital_visit"
    ICU_VISIT = "icu_visit"
    EXACT = "exact"


class IntervalType(str, Enum):
    SINCE = "since"
    UNTIL = "until"
    IN = "in"
    AT = "at"


class Option(str, Enum):
    FIRST = "first"
    SECOND = "second"
    SECOND_TO_LAST = "second_to_last"
    LAST = "last"
    CURRENT = "current"
    THIS = "this"
    NA = "na"  # Not applicable, used when option is not relevant


class OperationType(str, Enum):
    AGGREGATION = "aggregation"  # min/max/avg/sum/count
    COMPARISON = "comparison"  # >, <, = …
    # N_RANK = "n_rank"                # Not in patient-queries
    N_TIMES = "n_times"  # >= N, = N
    # SORT_PICK = "sort_pick"          # Not in patient-queries
    UNIT_AVERAGE = "unit_average"  # average per unit
    UNIT_COUNT = "unit_count"  # counts per unit
    # AGE_GROUP = "age_group"              # Not in patient-queries
    # SURVIVAL_PERIOD = "survival_period" # Not in patient-queries


class ResourceType(str, Enum):
    PATIENT = "Patient"
    ENCOUNTER = "Encounter"
    OBSERVATION = "Observation"
    CONDITION = "Condition"
    PROCEDURE = "Procedure"
    MEDICATION = "Medication"
    MEDICATION_REQUEST = "MedicationRequest"
    MEDICATION_ADMINISTRATION = "MedicationAdministration"
    SPECIMEN = "Specimen"
    # Add other resource types as needed
