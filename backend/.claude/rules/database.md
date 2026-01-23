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

```bash
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
```
