# Testing Standards

Rules for writing and organising tests.

## Framework

- Use `pytest` for all tests.
- Use `pytest-mock` for mocking (provides `mocker` fixture).
- Tests live under `testing/` and mirror `src/` structure.
- Aim for at least 80% test coverage.

## What to Test

### Test Selection Principles

- **Test behaviour and contracts, not implementation details**: Focus on what the function promises to do, not how it does it internally.
- **Test at the right level**: Unit tests for business logic, integration tests for boundaries.
- **Prioritise coverage of**:
  - Public API functions
  - Edge cases and boundary conditions
  - Error handling paths
  - Any code that has caused bugs before

### When Adding Tests

Before writing tests, identify:

1. The function's **public contract** (inputs, outputs, side effects)
2. The **expected behaviour** for normal cases
3. The **edge cases** (empty inputs, nulls, boundaries)
4. The **error conditions** and how they should be handled

## Test Design Principles

### One Test, One Reason to Fail

Each test should verify a single behaviour. If a test can fail for multiple unrelated reasons, split it:

```python
# Bad: Tests multiple things
def test_create_and_update_task(db_session: Session) -> None:
    task = create_task(db_session, "Test")
    assert task.name == "Test"
    update_task(db_session, task.id, name="Updated")
    assert task.name == "Updated"

# Good: Separate tests for each behaviour
def test_create_task_sets_name(db_session: Session) -> None:
    task = create_task(db_session, "Test")
    assert task.name == "Test"

def test_update_task_changes_name(db_session: Session) -> None:
    task = create_task(db_session, "Original")
    update_task(db_session, task.id, name="Updated")
    assert task.name == "Updated"
```

### Test Behaviour, Not Implementation

```python
# Bad: Tests internal implementation
def test_cache_uses_dict_internally() -> None:
    cache = Cache()
    cache.set("key", "value")
    assert "key" in cache._internal_dict  # Implementation detail!

# Good: Tests observable behaviour
def test_cache_retrieves_stored_value() -> None:
    cache = Cache()
    cache.set("key", "value")
    assert cache.get("key") == "value"
```

## Test Structure

Use the Arrange-Act-Assert pattern:

```python
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock client for testing."""
    return MagicMock()


def test_happy_path_returns_expected_result(mock_client: MagicMock) -> None:
    """Test description of what this verifies."""
    # Arrange
    expected = {"id": "123", "status": "created"}
    mock_client.create.return_value = expected

    # Act
    result = create_item(mock_client, "Test")

    # Assert
    assert result == expected
    mock_client.create.assert_called_once()
```

## Test Coverage

Every new behaviour must include tests covering:

1. **The happy path**: Normal successful operation
2. **At least one edge case**: Boundary conditions, empty inputs, etc.
3. **At least one failure mode**: Error handling, validation failures

## Mocking and Isolation

### Mock at the Boundaries, Not in the Middle

Mock external dependencies (HTTP, database, filesystem, external APIs), not internal functions:

```python
# Good: Mock the external boundary
@patch("src.client.requests.get")
def test_fetch_data_returns_parsed_response(mock_get: MagicMock) -> None:
    mock_get.return_value.json.return_value = {"data": "value"}
    result = fetch_data("https://api.example.com/data")
    assert result == {"data": "value"}

# Bad: Mock internal helper functions
@patch("src.client._parse_response")  # Internal implementation!
def test_fetch_data_parses_response(mock_parse: MagicMock) -> None:
    ...
```

### Use pytest-mock for Cleaner Mocking

```python
def test_upload_file_calls_s3(mocker: MockerFixture) -> None:
    """Use mocker fixture from pytest-mock."""
    mock_s3 = mocker.patch("src.aws.s3.boto3.client")
    mock_s3.return_value.put_object.return_value = {}

    upload_file("bucket", "key", b"data")

    mock_s3.return_value.put_object.assert_called_once()
```

### Decorator vs Context Manager

```python
# Decorator: When the mock applies to the entire test
@patch("src.client.requests.get")
def test_get_page_returns_page_data(mock_get: MagicMock) -> None:
    mock_get.return_value.json.return_value = {"id": "page-123"}
    mock_get.return_value.status_code = 200

    client = Client()
    result = client.get_page("page-123")

    assert result["id"] == "page-123"


# Context manager: When you need fine-grained control
def test_retry_on_failure() -> None:
    with patch("src.client.requests.get") as mock_get:
        mock_get.side_effect = [ConnectionError(), MagicMock(status_code=200)]
        result = fetch_with_retry("https://example.com")
        assert mock_get.call_count == 2
```

## Fixture Strategy

### Use Fixtures for Shared Setup

Put fixtures in `testing/conftest.py` for cross-module sharing:

```python
# testing/conftest.py
import pytest
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from unittest.mock import MagicMock


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create a test database session with in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Create a mock S3 client."""
    mock = MagicMock()
    mock.put_object.return_value = {}
    mock.get_object.return_value = {"Body": MagicMock(read=lambda: b"data")}
    return mock


@pytest.fixture
def mock_api_client() -> MagicMock:
    """Create a mock API client."""
    client = MagicMock()
    client.get.return_value = {"data": "test"}
    return client
```

### Builder Functions for Test Data

Use builder functions for complex test objects:

```python
def build_item_response(
    item_id: str = "item-123",
    status: str = "active",
    name: str = "Test Item",
) -> dict[str, Any]:
    """Build a mock item response with sensible defaults."""
    return {"id": item_id, "status": status, "name": name}


def test_process_item_updates_status(mock_client: MagicMock) -> None:
    mock_client.get.return_value = build_item_response(status="pending")
    result = process_item(mock_client, "item-123")
    assert result["status"] == "processed"
```

### Fixture Scope

Use appropriate scope to balance isolation and performance:

```python
@pytest.fixture(scope="function")  # Default: fresh for each test
def db_session() -> Generator[Session, None, None]:
    ...

@pytest.fixture(scope="module")  # Shared within a test file
def expensive_resource() -> SomeResource:
    ...

@pytest.fixture(scope="session")  # Shared across all tests
def docker_container() -> Container:
    ...
```

## Reliability and CI Discipline

### Keep Unit Tests Fast

- Unit tests should complete in milliseconds, not seconds.
- If a test is slow, it's probably testing too much or hitting real I/O.
- Use in-memory databases (SQLite) for database tests.

### Tests Must Be Deterministic

- No reliance on external services, network, or timing.
- No test order dependencies.
- Mock all sources of non-determinism (time, random, UUIDs).

```python
# Mock time for deterministic tests
@patch("src.module.datetime")
def test_record_created_with_current_time(mock_datetime: MagicMock) -> None:
    mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
    record = create_record()
    assert record.created_at == datetime(2025, 1, 1, 12, 0, 0)
```

### Avoid Network Calls

- Tests must be deterministic and isolated.
- Mock all external HTTP calls, database connections, and API clients.
- Use dependency injection to make mocking easier.

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run single test file
poetry run pytest testing/path/to/test_file.py

# Run single test function
poetry run pytest testing/path/to/test_file.py::test_function_name

# Run single test class
poetry run pytest testing/path/to/test_file.py::TestClassName

# Run tests matching a pattern
poetry run pytest -k "test_create"

# Run with verbose output
poetry run pytest -v

# Run and stop on first failure
poetry run pytest -x
```

## Test Naming

- Use descriptive names: `test_<action>_<condition>_<expected_result>`
- Examples:
  - `test_create_task_with_valid_data_returns_task_id`
  - `test_create_task_with_empty_name_raises_validation_error`
  - `test_query_tasks_with_no_results_returns_empty_list`

## Parametrised Tests

Use `@pytest.mark.parametrize` for testing multiple inputs:

```python
@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("valid", True),
        ("invalid", False),
        ("", False),
    ],
)
def test_validate_input(input_value: str, expected: bool) -> None:
    """Test input validation with multiple values."""
    assert validate(input_value) == expected
```

## Exception Testing

Use `pytest.raises` for testing exceptions:

```python
def test_invalid_input_raises_value_error() -> None:
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError, match="Invalid input"):
        process_input(None)
```

## Claude Code Operating Instructions

When Claude adds or modifies tests:

1. **Identify the public contract first**: Before writing tests, understand what the function promises to do.
2. **Write tests that would catch real bugs**: Ask "if someone broke this function, would this test fail?"
3. **Don't test framework behaviour**: Don't test that SQLAlchemy saves to the database or that pytest fixtures work.
4. **Match existing test style**: Look at nearby tests and follow the same patterns.
5. **Run tests after writing**: Always verify tests pass with `make test` before considering work complete.
