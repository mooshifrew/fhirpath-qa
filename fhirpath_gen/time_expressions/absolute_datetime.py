from pydantic import Field, field_validator
from typing import Literal, Dict, ClassVar
from datetime import datetime, timedelta

from ..base import TimeExpression, register_time_expression
from ..enums import TimeFilterType, TimeExpressionType, TimeUnit, IntervalType, Option
from ..utils import TIME_PATHS
from ..generator import GenerationContext
from .helpers import build_fhirpath_time_filter


class AbsoluteDateTime(TimeExpression):
    """Filter since/until/at/in a specific absolute date"""

    # class-level identity for registry
    time_exp_id: ClassVar[str] = "absolute_datetime"

    filter_type: ClassVar[TimeFilterType] = TimeFilterType.GLOBAL
    exp_type: ClassVar[TimeExpressionType] = TimeExpressionType.ABSOLUTE
    option: ClassVar[Option] = (
        Option.NA
    )  # Not applicable, since specific date will be given
    unit: ClassVar[Literal[TimeUnit.YEAR, TimeUnit.MONTH, TimeUnit.DAY]]
    interval_type: ClassVar[
        Literal[
            IntervalType.SINCE, IntervalType.UNTIL, IntervalType.IN, IntervalType.AT
        ]
    ]

    date: datetime = Field(
        ..., description="The specific date for the absolute time expression"
    )

    @field_validator("date", mode="before")
    def parse_date(cls, v: datetime) -> datetime:
        """Handle passing of dates as strings"""
        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            # Year only (YYYY)
            if v.isdigit() and len(v) == 4:
                return datetime(int(v), 1, 1)  # default to Jan 1

            # Year + month (YYYY-MM)
            if len(v) == 7 and v[4] == "-":
                year, month = v.split("-")
                return datetime(int(year), int(month), 1)  # default to 1st

            # Full ISO date
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")

        raise TypeError(f"Unsupported type for date: {type(v)}")

    def get_fhirpath_expression(self, params: Dict) -> str:
        """Get the FHIRPath expression for this time expression"""
        resource_type = params.get("resource_type", None)
        if resource_type is None:
            raise ValueError("Resource type must be provided in params")
        if resource_type not in TIME_PATHS.keys():
            raise ValueError(f"Resource type {resource_type} time path is not defined.")

        time_path = TIME_PATHS[resource_type]

        return build_fhirpath_time_filter(
            date=self.date,
            time_path=time_path,
            interval_type=self.interval_type,
            unit=self.unit,
        )

    def get_nl_expr(self) -> str:
        """Get the natural language expression for this time expression"""
        if self.unit == TimeUnit.YEAR:
            date_nl = self.date.strftime("%Y")
        elif self.unit == TimeUnit.MONTH:
            date_nl = self.date.strftime("%m/%Y")
        elif self.unit == TimeUnit.DAY:
            date_nl = self.date.strftime("%d/%m/%Y")
        else:
            date_nl = self.date.isoformat()

        if self.interval_type == IntervalType.AT:
            date_nl = self.date.strftime("%Y-%m-%d %H:%M:%S")

        if self.interval_type == IntervalType.IN and self.unit == TimeUnit.DAY:
            return f"on {date_nl}"

        return f"{self.interval_type.value} {date_nl}"

    @classmethod
    def random_instance(cls, ctx: GenerationContext):
        start, end = ctx.date_range
        delta = int((end - start).total_seconds())
        offset = ctx.rng.randint(0, delta)
        date = start + timedelta(seconds=offset)
        return cls(date=date)


## Actual time expressions


@register_time_expression
class AbsYearIn(AbsoluteDateTime):
    """Absolute filter: IN a given YEAR."""

    time_exp_id: ClassVar[str] = "abs-year-in"
    unit: Literal[TimeUnit.YEAR] = TimeUnit.YEAR
    interval_type: Literal[IntervalType.IN] = IntervalType.IN


@register_time_expression
class AbsYearUntil(AbsoluteDateTime):
    """Absolute filter: UNTIL a given YEAR."""

    time_exp_id: ClassVar[str] = "abs-year-until"
    unit: Literal[TimeUnit.YEAR] = TimeUnit.YEAR
    interval_type: Literal[IntervalType.UNTIL] = IntervalType.UNTIL


@register_time_expression
class AbsYearSince(AbsoluteDateTime):
    """Absolute filter: SINCE a given YEAR."""

    time_exp_id: ClassVar[str] = "abs-year-since"
    unit: Literal[TimeUnit.YEAR] = TimeUnit.YEAR
    interval_type: Literal[IntervalType.SINCE] = IntervalType.SINCE


@register_time_expression
class AbsMonthIn(AbsoluteDateTime):
    """Absolute filter: IN a given MONTH."""

    time_exp_id: ClassVar[str] = "abs-month-in"
    unit: Literal[TimeUnit.MONTH] = TimeUnit.MONTH
    interval_type: Literal[IntervalType.IN] = IntervalType.IN


@register_time_expression
class AbsMonthUntil(AbsoluteDateTime):
    """Absolute filter: UNTIL a given MONTH."""

    time_exp_id: ClassVar[str] = "abs-month-until"
    unit: Literal[TimeUnit.MONTH] = TimeUnit.MONTH
    interval_type: Literal[IntervalType.UNTIL] = IntervalType.UNTIL


@register_time_expression
class AbsMonthSince(AbsoluteDateTime):
    """Absolute filter: SINCE a given MONTH."""

    time_exp_id: ClassVar[str] = "abs-month-since"
    unit: Literal[TimeUnit.MONTH] = TimeUnit.MONTH
    interval_type: Literal[IntervalType.SINCE] = IntervalType.SINCE


@register_time_expression
class AbsDayIn(AbsoluteDateTime):
    """Absolute filter: IN a given DAY."""

    time_exp_id: ClassVar[str] = "abs-day-in"
    unit: Literal[TimeUnit.DAY] = TimeUnit.DAY
    interval_type: Literal[IntervalType.IN] = IntervalType.IN


@register_time_expression
class AbsDayUntil(AbsoluteDateTime):
    """Absolute filter: UNTIL a given DAY."""

    time_exp_id: ClassVar[str] = "abs-day-until"
    unit: Literal[TimeUnit.DAY] = TimeUnit.DAY
    interval_type: Literal[IntervalType.UNTIL] = IntervalType.UNTIL


@register_time_expression
class AbsDaySince(AbsoluteDateTime):
    """Absolute filter: SINCE a given DAY."""

    time_exp_id: ClassVar[str] = "abs-day-since"
    unit: Literal[TimeUnit.DAY] = TimeUnit.DAY
    interval_type: Literal[IntervalType.SINCE] = IntervalType.SINCE


@register_time_expression
class AbsExactIn(AbsoluteDateTime):
    """Absolute filter: AT an exact date and time."""

    time_exp_id: ClassVar[str] = "abs-exact-in"
    unit: Literal[TimeUnit.DAY] = TimeUnit.DAY
    interval_type: Literal[IntervalType.AT] = IntervalType.AT
