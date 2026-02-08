"""Tests for the semantic query builder (src/duckdb/semantic.py).

Pure Python tests — no DuckDB connection required.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from src.duckdb.manifest import DatasetFilters, Dimension, Measure, SemanticDataset
from src.duckdb.semantic import (
    InvalidQueryError,
    QueryFilter,
    QuerySpec,
    build_semantic_query,
    execute_semantic_query,
    validate_query_spec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DATASET_ID = UUID("12345678-1234-1234-1234-123456789abc")


@pytest.fixture
def sample_dataset() -> SemanticDataset:
    """Create a sample semantic dataset for testing."""
    return SemanticDataset(
        id=DATASET_ID,
        name="fct_monthly_trends",
        friendly_name="Monthly Trends",
        description="Monthly income and spending trends",
        group="aggregations",
        time_grain="month",
        schema_name="mart",
        filters=DatasetFilters(date_column="month_start"),
        measures=[
            Measure(name="total_income", expr="total_income", agg="sum", description=""),
            Measure(name="total_spending", expr="total_spending", agg="sum", description=""),
            Measure(name="savings_rate_pct", expr="savings_rate_pct", agg="avg", description=""),
            Measure(
                name="total_transactions", expr="total_transactions", agg="sum", description=""
            ),
            Measure(
                name="unique_merchants",
                expr="counterparty_name",
                agg="count_distinct",
                description="",
            ),
            Measure(name="record_count", expr="*", agg="count", description=""),
        ],
        dimensions=[
            Dimension(name="month_start", expr="month_start", type="time", description=""),
            Dimension(name="currency", expr="currency", type="categorical", description=""),
        ],
        sample_questions=["What is my income vs spending trend?"],
    )


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidateQuerySpec:
    """Tests for validate_query_spec."""

    def test_valid_spec_passes(self, sample_dataset: SemanticDataset) -> None:
        """Should not raise for a valid spec."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            dimensions=["month_start"],
        )
        validate_query_spec(spec, sample_dataset)

    def test_empty_measures_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when no measures are provided."""
        spec = QuerySpec(dataset="fct_monthly_trends", measures=[])
        with pytest.raises(InvalidQueryError, match="At least one measure"):
            validate_query_spec(spec, sample_dataset)

    def test_unknown_measure_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise for an unknown measure name."""
        spec = QuerySpec(dataset="fct_monthly_trends", measures=["nonexistent"])
        with pytest.raises(InvalidQueryError, match="Unknown measure 'nonexistent'"):
            validate_query_spec(spec, sample_dataset)

    def test_unknown_dimension_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise for an unknown dimension name."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            dimensions=["nonexistent"],
        )
        with pytest.raises(InvalidQueryError, match="Unknown dimension 'nonexistent'"):
            validate_query_spec(spec, sample_dataset)

    def test_invalid_operator_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise for an invalid filter operator."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="like", value="GBP")],
        )
        with pytest.raises(InvalidQueryError, match="Invalid operator 'like'"):
            validate_query_spec(spec, sample_dataset)

    def test_unknown_filter_dimension_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise for a filter on an unknown dimension."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="nonexistent", operator="eq", value="x")],
        )
        with pytest.raises(InvalidQueryError, match="Unknown filter dimension"):
            validate_query_spec(spec, sample_dataset)

    def test_invalid_time_granularity_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise for an invalid time granularity."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            dimensions=["month_start"],
            time_granularity="hourly",
        )
        with pytest.raises(InvalidQueryError, match="Invalid time granularity"):
            validate_query_spec(spec, sample_dataset)

    def test_time_granularity_without_time_dim_raises(
        self, sample_dataset: SemanticDataset
    ) -> None:
        """Should raise when time_granularity is set but no time dimension is queried."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            dimensions=["currency"],
            time_granularity="month",
        )
        with pytest.raises(InvalidQueryError, match="time_granularity requires"):
            validate_query_spec(spec, sample_dataset)

    def test_limit_too_low_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when limit is less than 1."""
        spec = QuerySpec(dataset="fct_monthly_trends", measures=["total_income"], limit=0)
        with pytest.raises(InvalidQueryError, match="Limit must be between"):
            validate_query_spec(spec, sample_dataset)

    def test_limit_too_high_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when limit exceeds MAX_LIMIT."""
        spec = QuerySpec(dataset="fct_monthly_trends", measures=["total_income"], limit=20_000)
        with pytest.raises(InvalidQueryError, match="Limit must be between"):
            validate_query_spec(spec, sample_dataset)

    def test_in_operator_requires_list(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when 'in' operator receives a non-list value."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="in", value="GBP")],
        )
        with pytest.raises(InvalidQueryError, match="requires a list value"):
            validate_query_spec(spec, sample_dataset)

    def test_not_in_operator_requires_list(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when 'not_in' operator receives a non-list value."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="not_in", value="GBP")],
        )
        with pytest.raises(InvalidQueryError, match="requires a list value"):
            validate_query_spec(spec, sample_dataset)

    def test_between_requires_two_values(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when 'between' operator doesn't have exactly 2 values."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="between", value=["a"])],
        )
        with pytest.raises(InvalidQueryError, match="exactly 2 values"):
            validate_query_spec(spec, sample_dataset)

    def test_between_requires_list(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when 'between' operator receives a non-list value."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="between", value="GBP")],
        )
        with pytest.raises(InvalidQueryError, match="exactly 2 values"):
            validate_query_spec(spec, sample_dataset)

    def test_order_by_must_be_queried_column(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when order_by is not a queried measure or dimension."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            order_by="total_spending",
        )
        with pytest.raises(InvalidQueryError, match="order_by"):
            validate_query_spec(spec, sample_dataset)

    def test_invalid_order_direction_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise for invalid order direction."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            order_by="total_income",
            order_direction="SIDEWAYS",
        )
        with pytest.raises(InvalidQueryError, match="order_direction"):
            validate_query_spec(spec, sample_dataset)


# ---------------------------------------------------------------------------
# Query building tests
# ---------------------------------------------------------------------------


class TestBuildSemanticQuery:
    """Tests for build_semantic_query."""

    def test_simple_measure_query(self, sample_dataset: SemanticDataset) -> None:
        """Should build a query with a single measure and no dimensions."""
        spec = QuerySpec(dataset="fct_monthly_trends", measures=["total_income"])
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        assert "SUM(total_income) AS total_income" in sql
        assert "FROM mart.fct_monthly_trends" in sql
        assert "WHERE user_id = $user_id" in sql
        assert "GROUP BY" not in sql
        assert params["user_id"] == str(user_id)

    def test_measure_with_dimension(self, sample_dataset: SemanticDataset) -> None:
        """Should build a query with GROUP BY when dimensions are specified."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            dimensions=["currency"],
        )
        user_id = uuid4()

        sql, _params = build_semantic_query(spec, sample_dataset, user_id)

        assert "currency AS currency" in sql
        assert "SUM(total_income) AS total_income" in sql
        assert "GROUP BY currency" in sql

    def test_time_granularity(self, sample_dataset: SemanticDataset) -> None:
        """Should apply DATE_TRUNC for time granularity."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            dimensions=["month_start"],
            time_granularity="quarter",
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "DATE_TRUNC('quarter', month_start) AS month_start" in sql
        assert "GROUP BY DATE_TRUNC('quarter', month_start)" in sql

    def test_filter_eq(self, sample_dataset: SemanticDataset) -> None:
        """Should build an equality filter."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="eq", value="GBP")],
        )
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        assert "currency = $filter_0" in sql
        assert params["filter_0"] == "GBP"

    def test_filter_neq(self, sample_dataset: SemanticDataset) -> None:
        """Should build a not-equal filter."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="neq", value="USD")],
        )
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        assert "currency != $filter_0" in sql
        assert params["filter_0"] == "USD"

    def test_filter_gt(self, sample_dataset: SemanticDataset) -> None:
        """Should build a greater-than filter."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="gt", value="A")],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)
        assert "currency > $filter_0" in sql

    def test_filter_gte(self, sample_dataset: SemanticDataset) -> None:
        """Should build a greater-than-or-equal filter."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="gte", value="A")],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)
        assert "currency >= $filter_0" in sql

    def test_filter_lt(self, sample_dataset: SemanticDataset) -> None:
        """Should build a less-than filter."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="lt", value="Z")],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)
        assert "currency < $filter_0" in sql

    def test_filter_lte(self, sample_dataset: SemanticDataset) -> None:
        """Should build a less-than-or-equal filter."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="lte", value="Z")],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)
        assert "currency <= $filter_0" in sql

    def test_filter_in(self, sample_dataset: SemanticDataset) -> None:
        """Should build an IN filter using UNNEST."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="in", value=["GBP", "EUR"])],
        )
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        assert "currency IN (SELECT UNNEST($filter_0))" in sql
        assert params["filter_0"] == ["GBP", "EUR"]

    def test_filter_not_in(self, sample_dataset: SemanticDataset) -> None:
        """Should build a NOT IN filter using UNNEST."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="not_in", value=["USD"])],
        )
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        assert "currency NOT IN (SELECT UNNEST($filter_0))" in sql
        assert params["filter_0"] == ["USD"]

    def test_filter_between(self, sample_dataset: SemanticDataset) -> None:
        """Should build a BETWEEN filter with lo/hi params."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="between", value=["A", "M"])],
        )
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        assert "currency BETWEEN $filter_0_lo AND $filter_0_hi" in sql
        assert params["filter_0_lo"] == "A"
        assert params["filter_0_hi"] == "M"

    def test_order_by(self, sample_dataset: SemanticDataset) -> None:
        """Should add ORDER BY clause."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            order_by="total_income",
            order_direction="DESC",
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "ORDER BY total_income DESC" in sql

    def test_limit_applied(self, sample_dataset: SemanticDataset) -> None:
        """Should apply the limit."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            limit=50,
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "LIMIT 50" in sql

    def test_limit_capped_at_max(self, sample_dataset: SemanticDataset) -> None:
        """Should cap the limit at MAX_LIMIT."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            limit=10_000,
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "LIMIT 10000" in sql

    def test_multiple_measures(self, sample_dataset: SemanticDataset) -> None:
        """Should include multiple measures in SELECT."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income", "total_spending", "savings_rate_pct"],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "SUM(total_income) AS total_income" in sql
        assert "SUM(total_spending) AS total_spending" in sql
        assert "AVG(savings_rate_pct) AS savings_rate_pct" in sql

    def test_multiple_dimensions(self, sample_dataset: SemanticDataset) -> None:
        """Should include multiple dimensions in SELECT and GROUP BY."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            dimensions=["month_start", "currency"],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "month_start AS month_start" in sql
        assert "currency AS currency" in sql
        assert "GROUP BY month_start, currency" in sql

    def test_no_dimensions_no_group_by(self, sample_dataset: SemanticDataset) -> None:
        """Should omit GROUP BY when there are no dimensions."""
        spec = QuerySpec(dataset="fct_monthly_trends", measures=["total_income"])
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "GROUP BY" not in sql

    def test_no_filters_only_user_id(self, sample_dataset: SemanticDataset) -> None:
        """Should only have user_id in WHERE when no filters are applied."""
        spec = QuerySpec(dataset="fct_monthly_trends", measures=["total_income"])
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        # WHERE clause should only contain user_id condition
        where_clause = (
            sql.split("WHERE")[1]
            .split("GROUP BY")[0]
            .split("ORDER BY")[0]
            .split("LIMIT")[0]
            .strip()
        )
        assert where_clause == "user_id = $user_id"
        assert len(params) == 1

    def test_count_distinct_aggregation(self, sample_dataset: SemanticDataset) -> None:
        """Should generate COUNT(DISTINCT ...) for count_distinct agg."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["unique_merchants"],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "COUNT(DISTINCT counterparty_name) AS unique_merchants" in sql

    def test_count_aggregation(self, sample_dataset: SemanticDataset) -> None:
        """Should generate COUNT(...) for count agg."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["record_count"],
        )
        user_id = uuid4()

        sql, _ = build_semantic_query(spec, sample_dataset, user_id)

        assert "COUNT(*) AS record_count" in sql

    def test_multiple_filters(self, sample_dataset: SemanticDataset) -> None:
        """Should chain multiple filters with AND."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[
                QueryFilter(dimension="currency", operator="eq", value="GBP"),
                QueryFilter(dimension="currency", operator="neq", value="USD"),
            ],
        )
        user_id = uuid4()

        sql, params = build_semantic_query(spec, sample_dataset, user_id)

        assert "currency = $filter_0" in sql
        assert "currency != $filter_1" in sql
        assert params["filter_0"] == "GBP"
        assert params["filter_1"] == "USD"


# ---------------------------------------------------------------------------
# Empty list validation tests
# ---------------------------------------------------------------------------


class TestEmptyListValidation:
    """Tests for empty list validation on in/not_in operators."""

    def test_empty_in_list_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when 'in' operator receives an empty list."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="in", value=[])],
        )
        with pytest.raises(InvalidQueryError, match="non-empty list"):
            validate_query_spec(spec, sample_dataset)

    def test_empty_not_in_list_raises(self, sample_dataset: SemanticDataset) -> None:
        """Should raise when 'not_in' operator receives an empty list."""
        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="not_in", value=[])],
        )
        with pytest.raises(InvalidQueryError, match="non-empty list"):
            validate_query_spec(spec, sample_dataset)


# ---------------------------------------------------------------------------
# execute_semantic_query tests
# ---------------------------------------------------------------------------


class TestExecuteSemanticQuery:
    """Tests for execute_semantic_query (mocked DuckDB)."""

    @patch("src.duckdb.semantic.execute_query")
    @patch("src.duckdb.semantic.get_semantic_dataset")
    def test_returns_result_with_provenance(
        self, mock_get_dataset: object, mock_execute: object, sample_dataset: SemanticDataset
    ) -> None:
        """Should return data and provenance from a valid query."""
        mock_get_dataset.return_value = sample_dataset  # type: ignore[union-attr]
        mock_execute.return_value = [  # type: ignore[union-attr]
            {"total_income": 5000.0},
        ]

        spec = QuerySpec(dataset="fct_monthly_trends", measures=["total_income"])
        user_id = uuid4()

        result = execute_semantic_query(spec, user_id)

        assert len(result.data) == 1
        assert result.data[0]["total_income"] == 5000.0
        assert result.provenance.dataset_name == "fct_monthly_trends"
        assert result.provenance.friendly_name == "Monthly Trends"
        assert result.provenance.measures_queried == ["total_income"]
        assert result.provenance.dimensions_queried == []
        assert result.provenance.row_count == 1
        assert result.provenance.query_duration_ms >= 0

    @patch("src.duckdb.semantic.get_semantic_dataset")
    def test_dataset_not_found_raises(self, mock_get_dataset: object) -> None:
        """Should raise InvalidQueryError when dataset is not found."""
        mock_get_dataset.return_value = None  # type: ignore[union-attr]

        spec = QuerySpec(dataset="nonexistent", measures=["total_income"])
        with pytest.raises(InvalidQueryError, match="Dataset not found"):
            execute_semantic_query(spec, uuid4())

    @patch("src.duckdb.semantic.get_semantic_dataset")
    def test_validation_failure_propagates(
        self, mock_get_dataset: object, sample_dataset: SemanticDataset
    ) -> None:
        """Should propagate validation errors from validate_query_spec."""
        mock_get_dataset.return_value = sample_dataset  # type: ignore[union-attr]

        spec = QuerySpec(dataset="fct_monthly_trends", measures=["nonexistent"])
        with pytest.raises(InvalidQueryError, match="Unknown measure"):
            execute_semantic_query(spec, uuid4())

    @patch("src.duckdb.semantic.execute_query")
    @patch("src.duckdb.semantic.get_semantic_dataset")
    def test_provenance_includes_filters(
        self, mock_get_dataset: object, mock_execute: object, sample_dataset: SemanticDataset
    ) -> None:
        """Should include filter descriptions in provenance."""
        mock_get_dataset.return_value = sample_dataset  # type: ignore[union-attr]
        mock_execute.return_value = []  # type: ignore[union-attr]

        spec = QuerySpec(
            dataset="fct_monthly_trends",
            measures=["total_income"],
            filters=[QueryFilter(dimension="currency", operator="eq", value="GBP")],
        )
        result = execute_semantic_query(spec, uuid4())

        assert result.provenance.filters_applied == ["currency eq GBP"]
        assert result.provenance.row_count == 0

    @patch("src.duckdb.semantic.execute_query")
    @patch("src.duckdb.semantic.get_semantic_dataset")
    def test_empty_result_set(
        self, mock_get_dataset: object, mock_execute: object, sample_dataset: SemanticDataset
    ) -> None:
        """Should handle empty result sets gracefully."""
        mock_get_dataset.return_value = sample_dataset  # type: ignore[union-attr]
        mock_execute.return_value = []  # type: ignore[union-attr]

        spec = QuerySpec(dataset="fct_monthly_trends", measures=["total_income"])
        result = execute_semantic_query(spec, uuid4())

        assert result.data == []
        assert result.provenance.row_count == 0
