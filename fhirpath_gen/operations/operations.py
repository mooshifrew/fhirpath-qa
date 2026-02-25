from fhirpath_gen.base import Operation, register_operation
from fhirpath_gen.enums import OperationType
from typing import ClassVar, List, Dict


@register_operation
class Comparison(Operation):
    op_type: ClassVar[OperationType] = (
        OperationType.COMPARISON
    )  # still referenced as "comparison"
    op_expr_allowed: ClassVar[List[str]] = ["greater", "less"]

    op_expr: str

    def get_fhirpath_expression(self, params: Dict) -> str:
        if self.op_expr == "greater":
            return ">"
        else:
            return "<"

    def get_nl_expr(self) -> str:
        return self.op_expr
    
    
