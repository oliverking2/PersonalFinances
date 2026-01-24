# Python Standards

## Style

- Python 3.12+, Poetry for dependencies
- Type hints everywhere
- Ruff for linting/formatting, mypy for type checking
- Line length: 100 characters
- British English in comments and user-facing text

## Naming

- Constants: `UPPER_SNAKE_CASE`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Use `StrEnum` for string constants, never raw string literals

## Functions

- Small, composable (<50 lines, low branching)
- Sphinx-style docstrings for public functions:

  ```python
  def create_item(name: str) -> Item:
      """Create a new item.

      :param name: Item name.
      :returns: Created item.
      :raises ValueError: If name is empty.
      """
  ```

## Error Handling

- Never bare `except:`, always catch specific exceptions
- Chain exceptions with `from e`
- Use `logger.exception()` for unexpected errors
- Create domain-specific exceptions with context

## Logging

- Use `logging.getLogger(__name__)`
- Structured format: `logger.info(f"Created item: id={item.id}")`
- Never log secrets
- No print statements in production code

## Testing

- pytest with pytest-mock
- Tests in `testing/` mirroring `src/` structure
- 80% coverage minimum
- One assertion focus per test
- Mock at boundaries (HTTP, database), not internal functions
- Use fixtures for shared setup

## Imports

- Absolute imports within `src/`
- Group: stdlib, third-party, local
- Type-only imports (e.g., `mypy_boto3_*` stubs) go in `TYPE_CHECKING` block to avoid runtime dependencies. Use `from __future__ import annotations` to defer annotation evaluation:

  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from mypy_boto3_s3 import S3Client

  def get_client() -> S3Client:  # Works at runtime
      ...
  ```
