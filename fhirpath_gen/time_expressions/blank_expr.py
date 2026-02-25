from pydantic import Field
from typing import ClassVar
from datetime import datetime

from ..base import TimeExpression, register_time_expression
from ..enums import TimeFilterType, TimeExpressionType, TimeUnit, IntervalType, Option
from ..generator import GenerationContext


@register_time_expression
class BlankTimeExpr(TimeExpression):
    """A placeholder for a blank time expression, to avoid using None."""

    time_exp_id: ClassVar[str] = "blank"

    filter_type: ClassVar[TimeFilterType] = TimeFilterType.GLOBAL
    exp_type: ClassVar[TimeExpressionType] = TimeExpressionType.ABSOLUTE
    option: ClassVar[Option] = Option.NA
    unit: ClassVar[TimeUnit] = TimeUnit.YEAR
    interval_type: ClassVar[IntervalType] = IntervalType.SINCE

    def get_fhirpath_expression(self, params):
        return ""

    def get_nl_expr(self) -> str:
        return ""

    @classmethod
    def random_instance(cls, ctx: GenerationContext):
        return cls()
