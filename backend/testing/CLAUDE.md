# Testing CLAUDE.md

Testing patterns and conventions. See also `backend/.claude/rules/python.md`.

## Structure

```
testing/
├── conftest.py         # Shared fixtures (db_session, client, auth helpers)
├── api/                # API endpoint tests (mirrors src/api/)
│   ├── conftest.py     # API-specific fixtures (if needed)
│   ├── accounts/
│   ├── recurring/
│   └── ...
├── postgres/           # Database operation tests (mirrors src/postgres/)
│   ├── common/
│   │   └── operations/
│   └── gocardless/
├── orchestration/      # Dagster asset tests
├── providers/          # External API client tests
└── utils/              # Utility function tests
```

## Key Fixtures (from conftest.py)

### Database Sessions

```python
# For unit tests (operations, utilities)
@pytest.fixture
def db_session() -> Generator[Session]:
    """In-memory SQLite session for unit tests."""

# For API tests (need TestClient to share session)
@pytest.fixture
def api_db_session() -> Generator[Session]:
    """In-memory SQLite with StaticPool for API tests."""
```

### API Testing

```python
@pytest.fixture
def client(api_db_session: Session) -> TestClient:
    """FastAPI TestClient with database dependency override."""

@pytest.fixture
def test_user_in_db(api_db_session: Session) -> User:
    """Create user in database. Password: 'testpassword123'"""

@pytest.fixture
def api_auth_headers(test_user_in_db: User) -> dict[str, str]:
    """Authorization header with valid JWT for test_user_in_db."""
```

### Entity Fixtures

```python
# These build on each other (chain of dependencies)
test_institution → test_connection → test_account → test_transaction
test_user → test_refresh_token
```

### Mock Builders

```python
build_gocardless_requisition_response()
build_gocardless_account_response()
build_gocardless_transactions_response()
build_gocardless_balances_response()
```

## Test Patterns

### API Endpoint Tests

```python
class TestListItems:
    """Tests for GET /api/items endpoint."""

    def test_returns_empty_list_when_no_items(
        self,
        client: TestClient,
        api_db_session: Session,
        test_user_in_db: User,
        api_auth_headers: dict[str, str],
    ) -> None:
        """Should return empty list when user has no items."""
        response = client.get("/api/items", headers=api_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_requires_authentication(self, client: TestClient) -> None:
        """Should require authentication."""
        response = client.get("/api/items")
        assert response.status_code == 401
```

### Operation Tests

```python
def test_create_item(db_session: Session, test_user: User) -> None:
    """Should create item with correct fields."""
    item = create_item(db_session, test_user.id, name="Test")
    db_session.commit()

    assert item.id is not None
    assert item.name == "Test"
    assert item.user_id == test_user.id
```

### Mock External APIs

```python
def test_fetch_transactions(
    db_session: Session,
    test_account: Account,
    mocker: MockerFixture,
) -> None:
    """Should fetch and store transactions."""
    # Mock the external API
    mock_client = mocker.patch("src.providers.gocardless.api.client")
    mock_client.get_transactions.return_value = build_gocardless_transactions_response()

    result = sync_transactions(db_session, test_account)

    assert len(result) == 1
    mock_client.get_transactions.assert_called_once()
```

## Conventions

### Naming

- Test files: `test_{module}.py`
- Test classes: `TestFeatureName` (group related tests)
- Test methods: `test_{expected_behavior}` or `test_{scenario}_when_{condition}`

### Docstrings

Every test method should have a one-line docstring:

```python
def test_returns_404_for_not_found(self, ...) -> None:
    """Should return 404 for non-existent pattern."""
```

### Assertions

- One primary assertion focus per test
- Use specific assertions: `assert x == y` not `assert x`
- Check status codes first, then response body

### Coverage

- **80% minimum** coverage threshold (enforced by `make check`)
- Focus on business logic paths, not trivial getters
- Mock at boundaries (external APIs, time), not internal functions

## Commands

```bash
cd backend

# Run all tests with coverage
make coverage

# Run specific test file
poetry run pytest testing/api/recurring/test_endpoints.py -v

# Run specific test class
poetry run pytest testing/api/recurring/test_endpoints.py::TestListPatterns -v

# Run specific test method
poetry run pytest testing/api/recurring/test_endpoints.py::TestListPatterns::test_returns_empty_list -v

# Run tests matching pattern
poetry run pytest -k "test_create" -v

# Run with print statements visible
poetry run pytest -s testing/path/to/test.py
```

## Troubleshooting

### "No such table" errors

Fixtures create tables in order. Make sure you're using the right session fixture:

- `db_session` for unit tests
- `api_db_session` for API tests (with `client` fixture)

### Test isolation issues

Each test gets a fresh database. If tests affect each other:

- Check for module-level state
- Ensure fixtures don't share mutable objects

### Slow tests

- Use `pytest-xdist` (`-n auto`) for parallel execution
- Mock slow external calls
- Use `@pytest.mark.slow` to skip in quick runs
