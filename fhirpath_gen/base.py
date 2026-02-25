from pydantic import BaseModel, Field, model_validator, field_validator, PrivateAttr
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Any, Optional, Type, ClassVar
from datetime import datetime

from .generator import GenerationContext
from .enums import (
    TimeFilterType,
    TimeExpressionType,
    TimeUnit,
    IntervalType,
    Option,
    OperationType,
)
from .utils import fill_slots, tidy_punctuation


# ======================================================================
# Base types
# ======================================================================


class SimplePlaceholder(ABC, BaseModel):
    """
    Base class for *simple placeholders* that inject concrete values (e.g., a drug
    or diagnosis string) into both the natural-language (NL) question and the
    FHIRPath query.

    Key design:
    - `name` is a **class-level identifier** (`ClassVar[str]`) used by the registry.
      This allows us to register classes *without instantiation*.
    - `value` is an **instance field** that must be provided when constructing.
    - `context` is an **optional instance field** that provides access to dynamic valuesets.
    - Subclasses should implement `get_fhirpath_expression()` and may override
      `random_instance()` to provide an auto-generation policy.
    """

    # Registry identity (class-level; not validated by Pydantic)
    name: ClassVar[str]

    # Per-instance data
    value: Any = Field(
        ...,
        description="Concrete placeholder value to substitute into NL and FHIRPath.",
    )

    # Optional generation context for dynamic validation
    context: Optional[GenerationContext] = Field(
        default=None,
        description="Generation context for dynamic valueset validation.",
        exclude=True,  # Exclude from serialization
    )

    def model_dump(self, **kwargs):
        """Override model_dump to exclude context field from serialization."""
        return super().model_dump(exclude={"context"}, **kwargs)

    @abstractmethod
    def get_fhirpath_expression(self, params: Dict) -> str:
        """
        Return the FHIRPath expression fragment corresponding to this placeholder.

        Parameters
        ----------
        params : Dict
            Arbitrary parameters that may be required for expression construction,
            such as resource_type or additional context.
        """
        ...

    def get_nl_expr(self) -> str:
        """
        Return the natural-language representation of the placeholder.
        Defaults to `self.value`.
        """
        return self.value

    # ---- Optional factory hooks for auto-generation ----
    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "SimplePlaceholder":
        """
        Return a plausible instance for auto-generation. Subclasses must override.
        """
        raise ValueError(
            f"{cls.__name__} does not define random_instance(ctx); please implement."
        )


class TimeExpression(ABC, BaseModel):
    """
    Base class for time expressions (absolute/relative filters).

    - `time_exp_id` is a class-level identifier used by the registry.
    - The semantics (`filter_type`, `exp_type`, `unit`, `interval_type`, `option`)
      are class-level constants in subclasses. Instances carry only per-instance
      data (e.g., `date` for absolute filters, nl text).
    """

    # Registry identity (class-level)
    time_exp_id: ClassVar[str]

    # Semantics (class-level, constant for a given subclass/preset)
    filter_type: ClassVar[TimeFilterType]
    exp_type: ClassVar[TimeExpressionType]
    unit: ClassVar[TimeUnit]
    interval_type: ClassVar[IntervalType]
    option: ClassVar[Option]

    def model_dump(self, **kwargs):
        """Override model_dump to include class-level metadata for proper serialization."""
        data = super().model_dump(**kwargs)
        # Add class-level metadata that's needed to reconstruct the filter
        data.update(
            {
                "time_exp_id": self.time_exp_id,
                "filter_type": (
                    self.filter_type.value
                    if hasattr(self.filter_type, "value")
                    else self.filter_type
                ),
                "exp_type": (
                    self.exp_type.value
                    if hasattr(self.exp_type, "value")
                    else self.exp_type
                ),
                "unit": self.unit.value if hasattr(self.unit, "value") else self.unit,
                "interval_type": (
                    self.interval_type.value
                    if hasattr(self.interval_type, "value")
                    else self.interval_type
                ),
                "option": (
                    self.option.value if hasattr(self.option, "value") else self.option
                ),
            }
        )
        return data

    @abstractmethod
    def get_fhirpath_expression(self, params: Dict) -> str:
        """
        Return the FHIRPath expression fragment for this time expression.
        Must not include surrounding 'where'/'and' unless that is your chosen convention.
        """
        ...

    @abstractmethod
    def get_nl_expr(self) -> str:
        """Return the NL string for this time expression."""
        ...

    # ---- Optional factory hooks for auto-generation ----
    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "TimeExpression":
        """
        Return a plausible instance if the subclass defines sensible defaults.
        Default implementation raises; time expressions typically require parameters.
        """
        raise ValueError(
            f"{cls.__name__} does not define random_instance(ctx); please implement."
        )


class Operation(ABC, BaseModel):
    """
    Base class for operations (e.g., count, comparison, max).

    Key design:
    - `op_type` is a **class-level identity** (`ClassVar[OperationType]`) used by the registry.
    - Subclasses implement `get_fhirpath_expression()` and `get_nl_expr()`.
    """

    # Registry identity (class-level)
    op_type: ClassVar[OperationType]
    op_expr_allowed: ClassVar[List[str]]

    op_expr: str = Field(..., description="the actual operation of this instance")

    @field_validator("op_expr")
    def check_expr(cls, v):
        if v not in cls.op_expr_allowed:
            raise ValueError(
                f"{v!r} is not an allowed operation for {cls.op_type}. Must be one of {cls.op_expr_allowed}"
            )
        return v

    @abstractmethod
    def get_fhirpath_expression(self, params: Dict) -> str:
        """
        Return a FHIRPath expression fragment implementing this operation.
        """
        ...

    @abstractmethod
    def get_nl_expr(self) -> str:
        """Return the NL expression of this operation (e.g., 'count of')."""
        ...

    # ---- Optional factory hooks for auto-generation ----
    @classmethod
    def random_instance(cls, ctx: GenerationContext) -> "Operation":
        """
        Return a plausible instance if fields have defaults.
        Default attempts no-arg construction.
        """
        chosen_expr = ctx.rng.choice(cls.op_expr_allowed)
        return cls(op_expr=chosen_expr)


class Template(ABC, BaseModel):
    """
    Base class for all question templates.

    - *Class-level metadata* (`template_id`, `description`, `tags`, `question_template`) is used by the registry
      without requiring instantiation.
    - *Allowed-placeholder maps* (`sp_allowed`, `op_allowed`, `t_allowed`) are **identifier lists** that specify,
      for each slot name, which placeholder types are legal. To represent an “absent” value uniformly, include the
      **'blank'** identifier in the allowed list and provide a registered sentinel class (e.g., `BlankPlaceholder`,
      `BlankTimeExpr`). No `None` is used for placeholders.
    - *Instance state* holds the **actual placeholder objects** resolved via the registries.

    **Supplying placeholders**

    You may instantiate a template:
      - With **no parameters** — missing slots are auto-generated from the allowed lists, preferring 'blank' when present.
      - With **instances**, e.g., `{'drug': DrugName(value='Heparin')}`.
      - With **dicts** that contain a `type` identifier and constructor kwargs, e.g.:
        `{'t_window': {'type': 'abs-year-in', 'date': '2024-01-01', ...}}`.

    Identifiers:
      - Simple placeholders: `placeholder_class.name` (e.g., `"drug_name"`, `"blank"`)
      - Operations: `str(op_type)` (e.g., `"count"`) — add `"blank"` if you define a BlankOperation
      - Time expressions: `time_exp_id` (e.g., `"abs-year-in"`, `"blank"`)
    """

    # ------------------ Class-level metadata ------------------
    template_id: ClassVar[str]
    description: ClassVar[str]
    tags: ClassVar[List[str]] = Field(
        default_factory=list, description="Tags for template categorization."
    )

    question_template: ClassVar[str] = Field(
        ...,
        description=(
            "NL question template with placeholders: "
            "use `{name}` for simple placeholders and `[name]` for operation/time placeholders."
        ),
    )

    # Allowed identifiers per slot (strings only; use 'blank' to mean sentinel/no-op) -----
    sp_allowed: ClassVar[Dict[str, List[str]]] = Field(
        default_factory=dict,
        description=(
            "Allowed **simple placeholder identifiers** per slot name. "
            "Identifiers come from registered SimplePlaceholder classes' `name` (e.g., 'drug_name', 'blank')."
        ),
    )
    op_allowed: ClassVar[Dict[str, List[str]]] = Field(
        default_factory=dict,
        description=(
            "Allowed **operation identifiers** per slot name. "
            "Identifiers are `str(op_type)` for registered Operation classes (e.g., 'count'). "
            "Add 'blank' if you define a BlankOperation."
        ),
    )
    t_allowed: ClassVar[Dict[str, List[str]]] = Field(
        default_factory=dict,
        description=(
            "Allowed **time expression identifiers** per slot name. "
            "Identifiers come from registered TimeExpression classes' `time_exp_id` (e.g., 'abs-year-in', 'blank')."
        ),
    )

    # ------------------ Instance placeholder state ------------------
    simple_placeholders: Dict[str, "SimplePlaceholder"] = Field(
        default_factory=dict,
        description="Resolved simple placeholders by slot name.",
    )
    operation_placeholders: Dict[str, "Operation"] = Field(
        default_factory=dict,
        description="Resolved operation placeholders by slot name.",
    )
    time_placeholders: Dict[str, "TimeExpression"] = Field(
        default_factory=dict,
        description="Resolved time placeholders by slot name.",
    )

    gen_ctx: GenerationContext = Field(
        default_factory=GenerationContext,
        description="Context for placeholder value generation; always present with defaults.",
    )

    _selected_paraphrase: Optional[str] = PrivateAttr(default=None)

    class Config:
        use_enum_values = True

    # -----------------------------
    # Lifecycle: validate & auto-generate
    # -----------------------------
    @model_validator(mode="after")
    def _validate_and_autofill(self):
        """
        Validate provided placeholders against the class-level `*_allowed` maps,
        coerce dicts/instances using registries, and auto-generate any missing slots.
        """
        self._check_unknown_keys()

        # Coerce/construct provided placeholders
        self.simple_placeholders = self._coerce_placeholders(
            provided=self.simple_placeholders,
            allowed=self.sp_allowed,
            kind="simple",
        )
        self.operation_placeholders = self._coerce_placeholders(
            provided=self.operation_placeholders,
            allowed=self.op_allowed,
            kind="operation",
        )
        self.time_placeholders = self._coerce_placeholders(
            provided=self.time_placeholders,
            allowed=self.t_allowed,
            kind="time",
        )

        # Auto-generate any missing slots
        self._autofill_missing()
        return self

    def _check_unknown_keys(self):
        """Raise if any provided slot name is not declared in the allowed maps."""
        allowed_keys = set(self.sp_allowed) | set(self.op_allowed) | set(self.t_allowed)
        provided_keys = (
            set(self.simple_placeholders)
            | set(self.operation_placeholders)
            | set(self.time_placeholders)
        )
        unknown = provided_keys - allowed_keys
        if unknown:
            raise ValueError(
                f"Unknown placeholder slots provided: {sorted(unknown)}. "
                f"Allowed: {sorted(allowed_keys)}"
            )

    def _identifier_for_instance(self, kind: str, inst: BaseModel) -> str:
        """
        Compute the registry identifier for a provided instance, used to validate
        against the `*_allowed` lists.
        """
        cls = inst.__class__
        if kind == "simple":
            return getattr(cls, "name", cls.__name__)
        if kind == "operation":
            op_type = getattr(cls, "op_type", None)
            return str(op_type.value if hasattr(op_type, "value") else op_type)
        if kind == "time":
            return getattr(cls, "time_exp_id", cls.__name__)
        raise ValueError(f"Unknown kind: {kind}")

    def _class_for_identifier(self, kind: str, ident: str):
        """
        Resolve a registry identifier to the registered class for the given kind.
        Returns `None` if the ident is unknown.
        """
        from .base import (
            simple_placeholder_registry,
            operation_registry,
            time_expression_registry,
        )  # local to avoid cycles

        if kind == "simple":
            return simple_placeholder_registry._placeholders.get(ident)
        if kind == "operation":
            return operation_registry._operations.get(str(ident))
        if kind == "time":
            return time_expression_registry._time_expressions.get(ident)
        return None

    def _coerce_placeholders(
        self, provided: Dict[str, Any], allowed: Dict[str, List[str]], kind: str
    ):
        """
        Coerce the `provided` mapping for a given `kind` into a mapping of instances.
        Validates identifiers against `allowed`.
        """
        out: Dict[str, BaseModel] = {}
        for slot, obj in provided.items():
            if slot not in allowed:
                raise ValueError(
                    f"Slot '{slot}' is not allowed for {self.__class__.__name__} in {kind}_placeholders"
                )
            allowed_idents = allowed[slot]

            if obj is None:
                raise TypeError(
                    f"Slot '{slot}' received None. Use a registered 'blank' type and include 'blank' in the allowed list."
                )

            # Already an instance?
            if isinstance(obj, BaseModel):
                ident = self._identifier_for_instance(kind, obj)
                if ident not in allowed_idents:
                    raise TypeError(
                        f"Provided instance for slot '{slot}' identifies as '{ident}', "
                        f"which is not allowed {allowed_idents}"
                    )
                out[slot] = obj
                continue

            # # Dict-based provisioning
            # if isinstance(obj, dict):
            #     type_name = obj.pop("type", None)
            #     kwargs = obj

            #     if not type_name:
            #         # If a type isn't specified, default to 'blank' if allowed, else the first allowed identifier.
            #         chosen_ident = (
            #             "blank" if "blank" in allowed_idents else allowed_idents[0]
            #         )
            #         chosen_cls = self._class_for_identifier(kind, chosen_ident)
            #     else:
            #         if type_name not in allowed_idents:
            #             raise TypeError(
            #                 f"Type identifier '{type_name}' not allowed for slot '{slot}'. Allowed: {allowed_idents}"
            #             )
            #         chosen_cls = self._class_for_identifier(kind, type_name)
            #         if chosen_cls is None:
            #             raise ValueError(
            #                 f"Unknown {kind} type '{type_name}' for slot '{slot}'"
            #             )

            #     try:
            #         out[slot] = chosen_cls(**kwargs)
            #     except TypeError:
            #         # Try class-provided factory hooks
            #         out[slot] = self._instantiate_with_hooks(chosen_cls, kwargs)
            #     continue

            raise TypeError(
                f"Unsupported value for slot '{slot}' in {kind}_placeholders: {type(obj)}"
            )

        return out

    def _instantiate_with_hooks(self, cls: Type, kwargs: Dict[str, Any]):
        """
        Attempt to build an instance using common class factory hooks before failing.
        Recognized hook names: 'from_params', 'from_kwargs', 'build', 'create'.
        """
        for hook in ("from_params", "from_kwargs", "build", "create"):
            if hasattr(cls, hook):
                inst = getattr(cls, hook)(**kwargs)
                if isinstance(inst, cls):
                    return inst

        # Last attempt: direct kwargs construction
        return cls(**kwargs)

    def _autofill_missing(self):
        """
        For any slot not provided, generate a valid instance using one of the class-level
        `*_allowed` identifiers and `random_instance()`.
        """
        # Simple placeholders
        for slot, idents in self.sp_allowed.items():
            if slot not in self.simple_placeholders:
                chosen_ident = self.gen_ctx.rng.choice(idents)
                chosen_cls = self._class_for_identifier("simple", chosen_ident)
                try:
                    self.simple_placeholders[slot] = self._auto_instance(chosen_cls)
                except Exception as e:
                    raise ValueError(
                        f"Failed to auto-generate simple placeholder for slot '{slot}': {e}"
                    )

        # Operations
        for slot, idents in self.op_allowed.items():
            if slot not in self.operation_placeholders:
                chosen_ident = self.gen_ctx.rng.choice(idents)
                chosen_cls = self._class_for_identifier("operation", chosen_ident)
                self.operation_placeholders[slot] = self._auto_instance(chosen_cls)

        # Time expressions
        for slot, idents in self.t_allowed.items():
            if slot not in self.time_placeholders:
                chosen_ident = self.gen_ctx.rng.choice(idents)
                chosen_cls = self._class_for_identifier("time", chosen_ident)
                try:
                    self.time_placeholders[slot] = self._auto_instance(chosen_cls)
                except Exception as e:
                    raise ValueError(
                        f"Failed to auto-generate time placeholder for slot '{slot}': {e}. "
                        f"Supply parameters for '{slot}' or implement random_instance()."
                    )

    def _auto_instance(self, cls: Type):
        """
        Construct an instance (of some placeholder/filter/op).
        """
        ctx = self.gen_ctx

        if hasattr(cls, "random_instance") and callable(
            getattr(cls, "random_instance")
        ):
            inst = cls.random_instance(ctx)
            if isinstance(inst, cls):
                # Ensure the context is set on the instance
                if hasattr(inst, "context"):
                    inst.context = ctx
                return inst
            # if isinstance(inst, dict):
            #     return cls(**inst)

        raise ValueError(
            f"{cls} cannot be auto-instantiated; define random_instance(ctx) or pass parameters explicitly."
        )

    # -----------------------------
    # Core API
    # -----------------------------
    @abstractmethod
    def compile_query(self) -> str:
        """
        Compile the currently filled placeholders into a FHIRPath query string.
        """
        ...

    def _select_paraphrase(self):
        """
        Select a paraphrase template deterministically using the generation context RNG.
        Falls back to the default question_template if paraphrasing is disabled or
        no paraphrases are available for this template.
        """
        # Reset selected paraphrase
        self._selected_paraphrase = None

        # Check if paraphrasing is enabled
        if not self.gen_ctx.use_paraphrases:
            return

        # Load paraphrases (cached, so this is efficient)
        paraphrases_dict = self.gen_ctx.load_paraphrases()

        # Check if this template has paraphrases
        if self.template_id not in paraphrases_dict:
            return

        paraphrases = paraphrases_dict[self.template_id]

        # Ensure we have valid paraphrases
        if (
            not paraphrases
            or not isinstance(paraphrases, list)
            or len(paraphrases) == 0
        ):
            return

        # Select a paraphrase deterministically using the seeded RNG
        selected = self.gen_ctx.rng.choice(paraphrases)
        self._selected_paraphrase = selected

    def generate_question(self) -> str:
        """
        Render the question string by substituting NL for placeholders.
        - Simple placeholders use `{slot}` (Python's `str.format`).
        - Operation and time placeholders use `[slot]` and are substituted via `fill_slots`.
        Uses selected paraphrase if available, otherwise falls back to class-level question_template.
        """
        # Use selected paraphrase if available, otherwise use class template
        template_str = (
            self._selected_paraphrase
            if self._selected_paraphrase is not None
            else self.question_template
        )

        # Simple placeholders -> python format `{}`
        question = template_str.format(
            **{k: v.get_nl_expr() for k, v in self.simple_placeholders.items()}
        )
        # Operation + time placeholders -> square-bracket slots via fill_slots()
        question = fill_slots(
            question,
            {k: v.get_nl_expr() for k, v in self.operation_placeholders.items()},
        )
        question = fill_slots(
            question, {k: v.get_nl_expr() for k, v in self.time_placeholders.items()}
        )
        return tidy_punctuation(question)

    def generate_qa_pair(
        self, placeholders: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete question-query pair.

        Parameters
        ----------
        placeholders : Optional[Dict[str, Any]]
            A dict with optional `simple` / `operation` / `time` keys, each mapping
            slot names to instances or dicts (with `type` + kwargs). If provided,
            the placeholders are merged into the instance, validated, and any missing
            slots are auto-filled according to `*_allowed`.
        """
        if placeholders:
            # Merge user-supplied into the current instance and re-validate
            self.simple_placeholders.update(placeholders.get("simple", {}))
            self.operation_placeholders.update(placeholders.get("operation", {}))
            self.time_placeholders.update(placeholders.get("time", {}))
            # Trigger validation + autofill again
            self._validate_and_autofill()

        # Use selected paraphrase if available, otherwise use default template
        template_str = (
            self._selected_paraphrase
            if self._selected_paraphrase is not None
            else self.question_template
        )

        return {
            "question": self.generate_question(),
            "query": self.compile_query(),
            "template_id": self.template_id,
            "template": template_str,
            "placeholders": {
                "simple": {
                    k: v.model_dump() for k, v in self.simple_placeholders.items()
                },
                "operation": {
                    k: v.model_dump() for k, v in self.operation_placeholders.items()
                },
                "time": {k: v.model_dump() for k, v in self.time_placeholders.items()},
            },
        }

    def regenerate_qa_pair(self) -> Dict[str, Any]:
        """
        Use the same template but randomly reselect all placeholders.
        Also selects a paraphrase if paraphrasing is enabled.
        """
        # Select paraphrase BEFORE regenerating placeholders to ensure deterministic selection
        self._select_paraphrase()

        self.simple_placeholders = {}
        self.time_placeholders = {}
        self.operation_placeholders = {}
        self._validate_and_autofill()

        return self.generate_qa_pair()


# ======================================================================
# Registries (store classes, resolve by identifiers)
# ======================================================================


class SimplePlaceholderRegistry:
    """
    Central registry for all `SimplePlaceholder` classes.

    - Keys are class identifiers (`SimplePlaceholder.name`).
    - Values are the classes themselves (not instances).
    """

    def __init__(self):
        self._placeholders: Dict[str, Type[SimplePlaceholder]] = {}

    def register(self, placeholder_class: Type[SimplePlaceholder]):
        """
        Register a `SimplePlaceholder` **class** (no instantiation here).
        The class must define a class attribute `name`.
        """
        key = getattr(placeholder_class, "name", None)
        if not key:
            raise ValueError(
                f"{placeholder_class.__name__} must define class attribute `name`."
            )
        self._placeholders[key] = placeholder_class
        return placeholder_class  # For use as decorator

    def get_placeholder(self, name: str, **kwargs) -> SimplePlaceholder:
        """
        Construct a placeholder by identifier with required kwargs (e.g., `value="..."`).

        Raises
        ------
        ValueError if the identifier is unknown.
        """
        if name not in self._placeholders:
            raise ValueError(f"Placeholder {name} not found")
        return self._placeholders[name](**kwargs)

    def gen_placeholder(self, name: str, ctx: GenerationContext) -> SimplePlaceholder:
        """
        Generate a placeholder by identifier with a generation context object.

        """
        if name not in self._placeholders:
            raise ValueError(f"Placeholder {name} not found")
        return self._placeholders[name].random_instance(ctx)

    def list_placeholders(self) -> List[str]:
        """Return all registered placeholder identifiers."""
        return list(self._placeholders.keys())


class OperationRegistry:
    """
    Central registry for `Operation` classes.

    - Keys are stringified `OperationType` identifiers (e.g., `"count"`).
    - Values are classes.
    """

    def __init__(self):
        self._operations: Dict[str, Type[Operation]] = {}

    def register(self, operation_class: Type[Operation]):
        """
        Register an `Operation` class.
        The class must define class attribute `op_type`.
        """
        op_type = getattr(operation_class, "op_type", None)
        if op_type is None:
            raise ValueError(
                f"{operation_class.__name__} must define class attribute `op_type`."
            )
        key = str(op_type.value if hasattr(op_type, "value") else op_type)
        self._operations[key] = operation_class
        return operation_class

    def get_operation(self, op_type: Union[str, OperationType], **kwargs) -> Operation:
        """
        Construct an `Operation` by identifier or enum value.
        """
        key = str(op_type.value if hasattr(op_type, "value") else op_type)
        if key not in self._operations:
            raise ValueError(f"Operation {key} not found")
        return self._operations[key](**kwargs)

    def gen_operation(
        self, op_type: Union[str, OperationType], ctx: GenerationContext
    ) -> Operation:
        """
        Randomly generate an `Operation` by identifier or enum value.

        """
        key = str(op_type.value if hasattr(op_type, "value") else op_type)
        if key not in self._operations:
            raise ValueError(f"Operation {key} not found")
        return self._operations[key].random_instance(ctx)

    def list_operations(self) -> List[str]:
        """Return all registered operation identifiers."""
        return list(self._operations.keys())


class TimeExpressionRegistry:
    """
    Central registry for `TimeExpression` classes.

    - Keys are class identifiers (`time_exp_id`).
    - Values are classes.
    """

    def __init__(self):
        self._time_expressions: Dict[str, Type[TimeExpression]] = {}

    def register(self, time_exp_class: Type[TimeExpression]):
        """
        Register a `TimeExpression` **class**.
        The class must define class attribute `time_exp_id`.
        """
        key = getattr(time_exp_class, "time_exp_id", None)
        if not key:
            raise ValueError(
                f"{time_exp_class.__name__} must define class attribute `time_exp_id`."
            )
        self._time_expressions[key] = time_exp_class
        return time_exp_class

    def get_time_expression(self, time_exp_id: str, **kwargs) -> TimeExpression:
        """
        Construct a `TimeExpression` by identifier with the provided kwargs.
        """
        if time_exp_id not in self._time_expressions:
            raise ValueError(f"TimeExpression {time_exp_id} not found")
        return self._time_expressions[time_exp_id](**kwargs)

    def gen_time_expression(
        self, time_exp_id: str, ctx: GenerationContext
    ) -> TimeExpression:
        """
        Generate a `TimeExpression` by identifier with the Generation Context.
        """
        if time_exp_id not in self._time_expressions:
            raise ValueError(f"TimeExpression {time_exp_id} not found")
        return self._time_expressions[time_exp_id].random_instance(ctx)

    def list_time_expressions(self) -> List[str]:
        """Return all registered time expression identifiers."""
        return list(self._time_expressions.keys())


class TemplateRegistry:
    """
    Central registry for `Template` classes.

    - Keys are `template_id` values.
    - Values are classes.
    - Tags are also indexed for discovery.
    """

    def __init__(self):
        self._templates: Dict[str, Type[Template]] = {}
        self._categories: Dict[str, List[str]] = {}  # tag -> list of template_ids

    def register(self, template_class: Type[Template]):
        """
        Register a `Template` class using class-level metadata.
        The class must define `template_id` (and may define `tags`).
        """
        template_id = getattr(template_class, "template_id", None)
        if not template_id:
            raise ValueError(
                f"{template_class.__name__} must define class attribute `template_id`."
            )
        tags = list(getattr(template_class, "tags", []))

        self._templates[template_id] = template_class
        for tag in tags:
            self._categories.setdefault(tag, []).append(template_id)
        return template_class

    def get_template_class(self, template_id: str) -> Type[Template]:
        """Return the registered `Template` class by id."""
        if template_id not in self._templates:
            raise ValueError(f"Template {template_id} not found")
        return self._templates[template_id]

    def new_template(self, template_id: str, **kwargs) -> Template:
        """Construct a new `Template` instance by id with provided kwargs."""
        return self.get_template_class(template_id)(**kwargs)

    def get_templates_by_tag(self, tag: str) -> List[Type[Template]]:
        """Return all template classes that carry the given tag."""
        if tag not in self._categories:
            return []
        return [self._templates[tid] for tid in self._categories[tag]]

    def list_templates(self) -> List[str]:
        """List all registered `template_id` values."""
        return list(self._templates.keys())

    def list_tags(self) -> List[str]:
        """List all registered tags (categories)."""
        return list(self._categories.keys())


# ======================================================================
# Global registries & decorators
# ======================================================================

simple_placeholder_registry = SimplePlaceholderRegistry()
operation_registry = OperationRegistry()
time_expression_registry = TimeExpressionRegistry()
template_registry = TemplateRegistry()


def register_template(template_class: Type[Template]):
    """Decorator to register a `Template` class."""
    return template_registry.register(template_class)


def register_simple_placeholder(placeholder_class: Type[SimplePlaceholder]):
    """Decorator to register a `SimplePlaceholder` class."""
    return simple_placeholder_registry.register(placeholder_class)


def register_operation(operation_class: Type[Operation]):
    """Decorator to register an `Operation` class."""
    return operation_registry.register(operation_class)


def register_time_expression(time_exp_class: Type[TimeExpression]):
    """Decorator to register a `TimeExpression` class."""
    return time_expression_registry.register(time_exp_class)
