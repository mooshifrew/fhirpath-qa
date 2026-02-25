from pydantic import Field, field_validator
from typing import Literal, Dict, ClassVar, Optional
from datetime import datetime

from ..base import TimeExpression, register_time_expression
from ..enums import TimeFilterType, TimeExpressionType, TimeUnit, IntervalType, Option
from ..utils import TIME_PATHS
from ..generator import GenerationContext
from .helpers import build_fhirpath_time_filter, make_delta


def _pluralize(word: str, n: int) -> str:
    return word if abs(n) == 1 else f"{word}s"


def _last_phrase(unit: TimeUnit) -> str:
    # "yesterday" for last day
    return "yesterday" if unit is TimeUnit.DAY else f"last {unit.value}"


def _this_phrase(unit: TimeUnit) -> str:
    # special case to match the table: "today" for this day
    return "today" if unit is TimeUnit.DAY else f"this {unit.value}"


class RelativeDateTime(TimeExpression):
    """Filter since/until/at/in relative to 'now'"""

    # class-level identity for registry
    time_exp_id: ClassVar[str] = "relative_datetime"

    filter_type: ClassVar[TimeFilterType] = TimeFilterType.GLOBAL
    exp_type: ClassVar[TimeExpressionType] = TimeExpressionType.RELATIVE
    option: ClassVar[Literal[Option.LAST, Option.THIS, Option.NA]]
    unit: ClassVar[Literal[TimeUnit.YEAR, TimeUnit.MONTH, TimeUnit.DAY]]
    interval_type: ClassVar[
        Literal[IntervalType.SINCE, IntervalType.UNTIL, IntervalType.IN]
    ]

    now: datetime = Field(
        ..., description="The current time used in relative comparisons"
    )
    quantity: Optional[int] = Field(
        None, description="The number of days/months/years to look forward/back"
    )

    @field_validator("quantity")
    def ensure_quantity(cls, v) -> Optional[int]:
        """quantity is required when Option.NA"""

        if cls.option == Option.NA:
            if not isinstance(v, int):
                raise ValueError("quantity must be specified when option NA")

        return v

    def get_fhirpath_expression(self, params: Dict) -> str:
        """Get the FHIRPath expression for this time expression"""
        resource_type = params.get("resource_type", None)
        if resource_type is None:
            raise ValueError("Resource type must be provided in params")
        if resource_type not in TIME_PATHS.keys():
            raise ValueError(f"Resource type {resource_type} time path is not defined.")

        time_path = TIME_PATHS[resource_type]

        # determine how far to look back
        if self.option == Option.LAST:
            q = 1
        elif self.option == Option.THIS:
            q = 0
        elif self.option == Option.NA:
            q = self.quantity

        delta = make_delta(q, self.unit)
        date = self.now - delta

        return build_fhirpath_time_filter(
            date=date,
            time_path=time_path,
            interval_type=self.interval_type,
            unit=self.unit,
        )

    def get_nl_expr(self) -> str:
        if self.interval_type is IntervalType.IN:
            if self.option is Option.LAST:
                return _last_phrase(self.unit)  # e.g., "last year", "yesterday"
            if self.option is Option.THIS:
                return _this_phrase(self.unit)  # e.g., "this month", "today"
            raise ValueError("IN requires option=LAST or THIS for RelativeDateTime.")

        prefix = "since" if self.interval_type is IntervalType.SINCE else "until"

        if self.option is Option.LAST:
            # e.g., "since last month", "until yesterday"
            return f"{prefix} {_last_phrase(self.unit)}"

        if self.option is Option.NA:
            # quantity is required; use proper pluralization
            if not isinstance(self.quantity, int) or self.quantity < 1:
                raise ValueError("quantity must be a positive integer when option=NA.")
            unit_word = _pluralize(self.unit.value, self.quantity)
            return f"{prefix} {self.quantity} {unit_word} ago"

        raise ValueError("SINCE/UNTIL with option=THIS is not supported for NL output.")

    @classmethod
    def random_instance(cls, ctx: GenerationContext):
        now = ctx.now
        option = cls.option

        if option == Option.NA:
            unit = cls.unit
            if unit == TimeUnit.YEAR:
                quantity = ctx.rng.randint(1, 10)
            if unit == TimeUnit.MONTH:
                quantity = ctx.rng.randint(1, 36)
            if unit == TimeUnit.DAY:
                quantity = ctx.rng.randint(1, 800)
        else:
            quantity = None

        instance = cls(now=now, quantity=quantity)
        return instance


# -------- YEAR --------


@register_time_expression
class RelYearInLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-year-in-last"
    unit: ClassVar[TimeUnit] = TimeUnit.YEAR
    interval_type: ClassVar[IntervalType] = IntervalType.IN
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelYearUntilLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-year-until-last"
    unit: ClassVar[TimeUnit] = TimeUnit.YEAR
    interval_type: ClassVar[IntervalType] = IntervalType.UNTIL
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelYearSinceLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-year-since-last"
    unit: ClassVar[TimeUnit] = TimeUnit.YEAR
    interval_type: ClassVar[IntervalType] = IntervalType.SINCE
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelYearInThis(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-year-in-this"
    unit: ClassVar[TimeUnit] = TimeUnit.YEAR
    interval_type: ClassVar[IntervalType] = IntervalType.IN
    option: ClassVar[Option] = Option.THIS


@register_time_expression
class RelYearUntilNA(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-year-until"
    unit: ClassVar[TimeUnit] = TimeUnit.YEAR
    interval_type: ClassVar[IntervalType] = IntervalType.UNTIL
    option: ClassVar[Option] = Option.NA


@register_time_expression
class RelYearSinceNA(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-year-since"
    unit: ClassVar[TimeUnit] = TimeUnit.YEAR
    interval_type: ClassVar[IntervalType] = IntervalType.SINCE
    option: ClassVar[Option] = Option.NA


# -------- MONTH --------


@register_time_expression
class RelMonthInLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-month-in-last"
    unit: ClassVar[TimeUnit] = TimeUnit.MONTH
    interval_type: ClassVar[IntervalType] = IntervalType.IN
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelMonthUntilLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-month-until-last"
    unit: ClassVar[TimeUnit] = TimeUnit.MONTH
    interval_type: ClassVar[IntervalType] = IntervalType.UNTIL
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelMonthSinceLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-month-since-last"
    unit: ClassVar[TimeUnit] = TimeUnit.MONTH
    interval_type: ClassVar[IntervalType] = IntervalType.SINCE
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelMonthInThis(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-month-in-this"
    unit: ClassVar[TimeUnit] = TimeUnit.MONTH
    interval_type: ClassVar[IntervalType] = IntervalType.IN
    option: ClassVar[Option] = Option.THIS


@register_time_expression
class RelMonthUntilNA(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-month-until"
    unit: ClassVar[TimeUnit] = TimeUnit.MONTH
    interval_type: ClassVar[IntervalType] = IntervalType.UNTIL
    option: ClassVar[Option] = Option.NA


@register_time_expression
class RelMonthSinceNA(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-month-since"
    unit: ClassVar[TimeUnit] = TimeUnit.MONTH
    interval_type: ClassVar[IntervalType] = IntervalType.SINCE
    option: ClassVar[Option] = Option.NA


# -------- DAY --------


@register_time_expression
class RelDayInLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-day-in-last"
    unit: ClassVar[TimeUnit] = TimeUnit.DAY
    interval_type: ClassVar[IntervalType] = IntervalType.IN
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelDayUntilLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-day-until-last"
    unit: ClassVar[TimeUnit] = TimeUnit.DAY
    interval_type: ClassVar[IntervalType] = IntervalType.UNTIL
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelDaySinceLast(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-day-since-last"
    unit: ClassVar[TimeUnit] = TimeUnit.DAY
    interval_type: ClassVar[IntervalType] = IntervalType.SINCE
    option: ClassVar[Option] = Option.LAST


@register_time_expression
class RelDayInThis(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-day-in-this"
    unit: ClassVar[TimeUnit] = TimeUnit.DAY
    interval_type: ClassVar[IntervalType] = IntervalType.IN
    option: ClassVar[Option] = Option.THIS


@register_time_expression
class RelDayUntilNA(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-day-until"
    unit: ClassVar[TimeUnit] = TimeUnit.DAY
    interval_type: ClassVar[IntervalType] = IntervalType.UNTIL
    option: ClassVar[Option] = Option.NA


@register_time_expression
class RelDaySinceNA(RelativeDateTime):
    time_exp_id: ClassVar[str] = "rel-day-since"
    unit: ClassVar[TimeUnit] = TimeUnit.DAY
    interval_type: ClassVar[IntervalType] = IntervalType.SINCE
    option: ClassVar[Option] = Option.NA
