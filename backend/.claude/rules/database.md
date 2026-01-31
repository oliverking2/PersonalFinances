# Database Patterns

## Structure

```
src/postgres/<domain>/
├── __init__.py
├── models.py         # SQLAlchemy ORM models
└── operations/       # CRUD functions
    └── <entity>.py
```

## SQLAlchemy Models

- Use 2.0 style with `Mapped` type hints
- Indexes on columns used in queries
- JSONB for semi-structured data

```python
class Item(Base):
    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
```

## Operations

- Session as first parameter
- No commits in operations (caller manages transactions)
- Use `.flush()` to get auto-generated IDs
- Log with context: `logger.info(f"Created item: id={item.id}")`

```python
def create_item(session: Session, name: str) -> Item:
    item = Item(name=name)
    session.add(item)
    session.flush()
    return item
```

## Validation

- Pydantic for API boundary validation
- SQLAlchemy constraints for database integrity
- Validate at system boundaries, trust internal code

## Migrations

**ALWAYS use `--autogenerate`** - never write migrations manually:

```bash
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
```

Why autogenerate matters:

- Compares models to the actual database schema
- Generates correct revision IDs automatically
- Detects added/removed columns, index changes, constraint changes
- Avoids duplicate column errors and revision ID conflicts

After autogeneration, you may need to edit the migration for:

1. **Data migration**: Copy data before dropping columns
2. **NOT NULL columns**: Add as nullable first, populate data, then alter to NOT NULL
3. **Unique constraints**: Clean up duplicates before adding constraint

Example pattern for schema changes with data:

```python
def upgrade():
    # 1. Add new columns as NULLABLE
    op.add_column('table', sa.Column('new_col', sa.String(), nullable=True))

    # 2. Migrate data from old to new columns
    op.execute("UPDATE table SET new_col = old_col")

    # 3. Make columns NOT NULL
    op.alter_column('table', 'new_col', nullable=False)

    # 4. Clean up duplicates before unique constraint
    op.execute("DELETE FROM table WHERE id NOT IN (SELECT DISTINCT ON ...)")

    # 5. Drop old columns
    op.drop_column('table', 'old_col')
```
