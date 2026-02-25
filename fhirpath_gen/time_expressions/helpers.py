from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Literal
from ..utils import format_date
from fhirpath_gen.enums import IntervalType, TimeUnit


# Assuming you already have these enums somewhere:
# from .enums import IntervalType, TimeUnit
# and you already have format_date(date, granularity, end_of_period, fmt="iso")

Granularity = Literal["year", "month", "day"]


def build_fhirpath_time_filter(
    *,
    date: datetime,
    time_path: str,
    interval_type: IntervalType,
    unit: TimeUnit,
) -> str:
    """
    Build a FHIRPath time filter string based on interval type and unit.

    Parameters
    ----------
    date : datetime
        Anchor date.
    time_path : str
        FHIRPath to the time field (e.g., 'effectiveDateTime').
    interval_type : IntervalType
        One of AT, IN, SINCE, UNTIL.
    unit : TimeUnit
        One of YEAR, MONTH, DAY.

    Returns
    -------
    str
        FHIRPath predicate string.
    """
    # Map enum to the granularity string your formatter expects
    if unit not in [TimeUnit.DAY, TimeUnit.MONTH, TimeUnit.YEAR]:
        raise ValueError("Unsupported time unit. Unit must be 'day', 'month' or 'year'")

    granularity = unit.value

    if interval_type == IntervalType.AT:
        date_iso = format_date(date, granularity, end_of_period=False, fmt="iso")
        return f"{time_path} = @{date_iso}"

    if interval_type == IntervalType.IN:
        if unit in (TimeUnit.YEAR, TimeUnit.MONTH):
            low = format_date(date, granularity, end_of_period=False, fmt="iso")
            high = format_date(date, granularity, end_of_period=True, fmt="iso")
            return f"{time_path} >= @{low} and {time_path} <= @{high}.highBoundary()"
        else:  # DAY
            date_iso = format_date(date, granularity, end_of_period=False, fmt="iso")
            return f"{time_path} = @{date_iso}"

    if interval_type == IntervalType.SINCE:
        date_iso = format_date(date, granularity, end_of_period=False, fmt="iso")
        return f"{time_path} >= @{date_iso}"

    if interval_type == IntervalType.UNTIL:
        date_iso = format_date(date, granularity, end_of_period=True, fmt="iso")
        return f"{time_path} <= @{date_iso}"

    raise ValueError(f"Unsupported IntervalType: {interval_type}")


def make_delta(value: int, unit: TimeUnit):
    if unit == TimeUnit.DAY:
        return relativedelta(days=value)
    elif unit == TimeUnit.MONTH:
        return relativedelta(months=value)
    elif unit == TimeUnit.YEAR:
        return relativedelta(years=value)
    else:
        raise ValueError(f"Unsupported unit: {unit}")
