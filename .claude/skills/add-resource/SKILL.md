---
name: add-resource
description: Scaffold a new CRUD domain resource (SQLAlchemy model, Pydantic schemas, FastAPI router, tests) wired into the app the same way as Item. Use when adding a new entity/endpoint group, or when a ticket introduces a new resource.
argument-hint: "<ResourceName> [field:type ...]"
---

# Add resource

Input: $ARGUMENTS — e.g. `Order customer_id:int total:decimal status:str`. Ask for fields and which operations (list/get/create/update/delete) are needed if unclear.

Use the `Item` files as the template for style. Names: model `Order`, table `orders`, module `order.py`, router prefix `/orders`, tag `orders`.

## Checklist

1. **Model** `src/assessment/models/<name>.py`
   - `Mapped[...]` + `mapped_column(...)`; give strings a `String(n)` length; nullable columns are `Mapped[X | None]`.
   - `created_at` with `server_default=func.now()` if the ticket wants timestamps; use `DateTime(timezone=True)`, since days are counted in IST.
   - Money: `Numeric(10, 2)` ↔ `Decimal` (or integer paise), never `Float`. Reports must match to the paisa.
   - Add indexes for the columns the ticket searches/filters on (`index=True` or `Index(...)` in `__table_args__`).
   - Foreign keys: `ForeignKey("<table>.id")`; relationships need `lazy="selectin"` (or explicit `selectinload`) — lazy loading fails in async.
2. **Register** — add the import and `__all__` entry in `src/assessment/models/__init__.py`.
3. **Schemas** `src/assessment/schemas/<name>.py`
   - `<Name>Create`: client-writable fields, `Field(...)` constraints matching the columns.
   - `<Name>Update` (if PATCH/PUT): every field optional.
   - `<Name>Read(<Name>Create)`: `model_config = ConfigDict(from_attributes=True)` + `id` and server fields.
4. **Router** `src/assessment/api/<plural>.py`
   - `APIRouter(prefix="/<plural>", tags=["<plural>"])`, `SessionDep` for the session.
   - POST → 201, GET list ordered by id, GET one → 404 if missing, PATCH → `model_dump(exclude_unset=True)` + `setattr`, DELETE → 204.
   - Unique constraints: catch `sqlalchemy.exc.IntegrityError`, `await session.rollback()`, raise 409.
   - Errors must go through the app's shared JSON error format (no ad-hoc error bodies).
5. **Register** — `app.include_router(<plural>.router)` in `src/assessment/main.py`.
6. **Tests** `tests/test_<plural>.py` using the `client` fixture: create, get, list, 404, 422 on invalid payload, and update/delete/409 where applicable.
7. Run the `quality-check` skill.
8. Schema: if Alembic is set up (from P2 on), generate a migration (`uv run alembic revision --autogenerate -m "add <plural> table"`), review it, and run `uv run alembic upgrade head`. Before that, tell the user to delete `app.db` if an existing table changed.
