"""Semantic query builder for the analytics layer.

Translates structured query specs into safe, parameterised DuckDB SQL.
All queries are constrained to known measures, dimensions, and operators
defined in dbt schema metadata — no arbitrary SQL generation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.duckdb.client import execute_query
from src.duckdb.manifest import SemanticDataset, get_semantic_dataset

logger = logging.getLogger(__name__)

# Allowed aggregation functions
VALID_AGGS = frozenset({"sum", "avg", "count", "count_distinct", "min", "max"})

# Allowed filter operators
VALID_OPERATORS = frozenset({"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "between"})

# Allowed time granularities for DATE_TRUNC
VALID_GRANULARITIES = frozenset({"day", "week", "month", "quarter", "year"})

# Maximum rows to return from a semantic query
MAX_LIMIT = 10_000
DEFAULT_LIMIT = 1_000


class InvalidQueryError(Exception):
    """Raised when a query spec is invalid against the dataset schema."""


@dataclass
class QueryFilter:
    """A filter to apply to a semantic query."""

    dimension: str
    operator: str  # eq, neq, gt, gte, lt, lte, in, not_in, between
    value: Any


@dataclass
class QuerySpec:
    """Specification for a semantic query."""

    dataset: str  # Dataset name or UUID
    measures: list[str]
    dimensions: list[str] = field(default_factory=list)
    filters: list[QueryFilter] = field(default_factory=list)
    time_granularity: str | None = None
    order_by: str | None = None
    order_direction: str = "ASC"
    limit: int = DEFAULT_LIMIT


@dataclass
class QueryProvenance:
    """Metadata about how a query result was produced."""

    dataset_name: str
    friendly_name: str
    measures_queried: list[str]
    dimensions_queried: list[str]
    filters_applied: list[str]
    row_count: int
    query_duration_ms: float


@dataclass
class QueryResult:
    """Result of a semantic query with provenance."""

    data: list[dict[str, Any]]
    provenance: QueryProvenance


def _apply_time_granularity(expr: str, granularity: str) -> str:
    """Wrap a column expression with DATE_TRUNC for time granularity.

    :param expr: Column expression.
    :param granularity: Time granularity (day, week, month, quarter, year).
    :returns: DATE_TRUNC expression.
    """
    return f"DATE_TRUNC('{granularity}', {expr})"


_OPERATOR_TEMPLATES: dict[str, str] = {
    "eq": "{col} = ${p}",
    "neq": "{col} != ${p}",
    "gt": "{col} > ${p}",
    "gte": "{col} >= ${p}",
    "lt": "{col} < ${p}",
    "lte": "{col} <= ${p}",
    "in": "{col} IN (SELECT UNNEST(${p}))",
    "not_in": "{col} NOT IN (SELECT UNNEST(${p}))",
    "between": "{col} BETWEEN ${p}_lo AND ${p}_hi",
}


def _operator_to_sql(operator: str, column: str, param_name: str) -> str:
    """Convert a filter operator to a SQL clause.

    :param operator: Filter operator name.
    :param column: Column expression.
    :param param_name: Parameter placeholder name.
    :returns: SQL clause fragment.
    """
    template = _OPERATOR_TEMPLATES.get(operator)
    if template is None:
        raise InvalidQueryError(f"Unknown operator: {operator}")
    return template.format(col=column, p=param_name)


BETWEEN_VALUE_COUNT = 2


def _validate_filter(f: QueryFilter, known_dims: set[str]) -> None:
    """Validate a single query filter.

    :param f: Filter to validate.
    :param known_dims: Set of valid dimension names.
    :raises InvalidQueryError: If the filter is invalid.
    """
    if f.dimension not in known_dims:
        raise InvalidQueryError(
            f"Unknown filter dimension '{f.dimension}'. Available: {sorted(known_dims)}"
        )
    if f.operator not in VALID_OPERATORS:
        raise InvalidQueryError(
            f"Invalid operator '{f.operator}'. Available: {sorted(VALID_OPERATORS)}"
        )
    if f.operator in ("in", "not_in"):
        if not isinstance(f.value, list):
            raise InvalidQueryError(
                f"Operator '{f.operator}' requires a list value, got {type(f.value).__name__}"
            )
        if not f.value:
            raise InvalidQueryError(f"Operator '{f.operator}' requires a non-empty list")
    if f.operator == "between" and (
        not isinstance(f.value, list) or len(f.value) != BETWEEN_VALUE_COUNT
    ):
        raise InvalidQueryError("Operator 'between' requires a list of exactly 2 values")


def _validate_time_granularity(spec: QuerySpec, dataset: SemanticDataset) -> None:
    """Validate time granularity against dataset dimensions.

    :param spec: Query specification.
    :param dataset: Semantic dataset to validate against.
    :raises InvalidQueryError: If the time granularity is invalid.
    """
    if not spec.time_granularity:
        return

    if spec.time_granularity not in VALID_GRANULARITIES:
        raise InvalidQueryError(
            f"Invalid time granularity '{spec.time_granularity}'. "
            f"Available: {sorted(VALID_GRANULARITIES)}"
        )
    time_dims = {d.name for d in dataset.dimensions if d.type == "time"}
    if not time_dims.intersection(spec.dimensions):
        raise InvalidQueryError(
            "time_granularity requires at least one time dimension in the query. "
            f"Available time dimensions: {sorted(time_dims)}"
        )


def validate_query_spec(spec: QuerySpec, dataset: SemanticDataset) -> None:
    """Validate a query spec against a dataset's semantic schema.

    :param spec: Query specification.
    :param dataset: Semantic dataset to validate against.
    :raises InvalidQueryError: If the spec is invalid.
    """
    if not spec.measures:
        raise InvalidQueryError("At least one measure is required")

    # Validate measures
    known_measures = {m.name for m in dataset.measures}
    for measure_name in spec.measures:
        if measure_name not in known_measures:
            raise InvalidQueryError(
                f"Unknown measure '{measure_name}'. Available: {sorted(known_measures)}"
            )

    # Validate dimensions
    known_dims = {d.name for d in dataset.dimensions}
    for dim_name in spec.dimensions:
        if dim_name not in known_dims:
            raise InvalidQueryError(
                f"Unknown dimension '{dim_name}'. Available: {sorted(known_dims)}"
            )

    # Validate filters
    for f in spec.filters:
        _validate_filter(f, known_dims)

    _validate_time_granularity(spec, dataset)

    # Validate limit
    if spec.limit < 1 or spec.limit > MAX_LIMIT:
        raise InvalidQueryError(f"Limit must be between 1 and {MAX_LIMIT}, got {spec.limit}")

    # Validate order_by
    if spec.order_by:
        valid_order_cols = set(spec.measures) | set(spec.dimensions)
        if spec.order_by not in valid_order_cols:
            raise InvalidQueryError(
                f"order_by '{spec.order_by}' must be a queried measure or dimension"
            )

    # Validate order_direction
    if spec.order_direction.upper() not in ("ASC", "DESC"):
        raise InvalidQueryError(
            f"order_direction must be 'ASC' or 'DESC', got '{spec.order_direction}'"
        )


def build_semantic_query(
    spec: QuerySpec, dataset: SemanticDataset, user_id: UUID
) -> tuple[str, dict[str, Any]]:
    """Build a parameterised SQL query from a semantic query spec.

    :param spec: Validated query specification.
    :param dataset: Semantic dataset.
    :param user_id: User ID for data isolation.
    :returns: Tuple of (SQL string, parameters dict).
    """
    measures_by_name = {m.name: m for m in dataset.measures}
    dims_by_name = {d.name: d for d in dataset.dimensions}
    params: dict[str, Any] = {"user_id": str(user_id)}

    # Build SELECT clause
    select_parts: list[str] = []
    group_by_parts: list[str] = []

    # Add dimensions to SELECT and GROUP BY
    for dim_name in spec.dimensions:
        dim = dims_by_name[dim_name]
        expr = dim.expr

        # Apply time granularity to time dimensions
        if dim.type == "time" and spec.time_granularity:
            expr = _apply_time_granularity(expr, spec.time_granularity)

        select_parts.append(f"{expr} AS {dim_name}")
        group_by_parts.append(expr)

    # Add measures to SELECT
    for measure_name in spec.measures:
        measure = measures_by_name[measure_name]
        agg = measure.agg.upper()

        if agg == "COUNT_DISTINCT":
            select_parts.append(f"COUNT(DISTINCT {measure.expr}) AS {measure_name}")
        elif agg == "COUNT":
            select_parts.append(f"COUNT({measure.expr}) AS {measure_name}")
        else:
            select_parts.append(f"{agg}({measure.expr}) AS {measure_name}")

    select_clause = ", ".join(select_parts)

    # Build WHERE clause (user_id is always required)
    where_parts = ["user_id = $user_id"]

    # Apply filters
    for idx, f in enumerate(spec.filters):
        dim = dims_by_name[f.dimension]
        param_name = f"filter_{idx}"

        clause = _operator_to_sql(f.operator, dim.expr, param_name)
        where_parts.append(clause)

        if f.operator == "between":
            params[f"{param_name}_lo"] = f.value[0]
            params[f"{param_name}_hi"] = f.value[1]
        else:
            params[param_name] = f.value

    where_clause = " AND ".join(where_parts)

    # Build full query
    table_ref = f"{dataset.schema_name}.{dataset.name}"
    query = f"SELECT {select_clause} FROM {table_ref} WHERE {where_clause}"

    # GROUP BY (only if there are dimensions)
    if group_by_parts:
        query += f" GROUP BY {', '.join(group_by_parts)}"

    # ORDER BY
    if spec.order_by:
        direction = spec.order_direction.upper()
        query += f" ORDER BY {spec.order_by} {direction}"

    # LIMIT (capped at MAX_LIMIT)
    limit = min(spec.limit, MAX_LIMIT)
    query += f" LIMIT {limit}"

    return query, params


def execute_semantic_query(spec: QuerySpec, user_id: UUID) -> QueryResult:
    """Validate, build, and execute a semantic query.

    :param spec: Query specification.
    :param user_id: User ID for data isolation.
    :returns: QueryResult with data and provenance.
    :raises InvalidQueryError: If the spec is invalid or dataset is not found.
    """
    # Resolve dataset
    dataset = get_semantic_dataset(spec.dataset)
    if dataset is None:
        raise InvalidQueryError(f"Dataset not found: {spec.dataset}")

    # Validate
    validate_query_spec(spec, dataset)

    # Build query
    query, params = build_semantic_query(spec, dataset, user_id)

    logger.info(
        f"Executing semantic query: dataset={dataset.name}, "
        f"measures={spec.measures}, dimensions={spec.dimensions}"
    )

    # Execute
    start = time.monotonic()
    data = execute_query(query, params, max_rows=min(spec.limit, MAX_LIMIT))
    duration_ms = (time.monotonic() - start) * 1000

    # Build provenance
    provenance = QueryProvenance(
        dataset_name=dataset.name,
        friendly_name=dataset.friendly_name,
        measures_queried=spec.measures,
        dimensions_queried=spec.dimensions,
        filters_applied=[f"{f.dimension} {f.operator} {f.value}" for f in spec.filters],
        row_count=len(data),
        query_duration_ms=round(duration_ms, 2),
    )

    return QueryResult(data=data, provenance=provenance)
