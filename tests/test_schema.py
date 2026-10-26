import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.dialects import sqlite

from assessment.enums import OrderStatus
from assessment.pagination import encode_cursor
from assessment.schemas.order import OrderSearch
from assessment.services.orders import build_order_search

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def alembic_config(database: Path) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["database_url"] = f"sqlite+aiosqlite:///{database.as_posix()}"
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture
def migrated_db(tmp_path: Path) -> Iterator[Path]:
    database = tmp_path / "migrated.db"
    command.upgrade(alembic_config(database), "head")
    yield database


def query_plan(database: Path, search: OrderSearch) -> list[str]:
    compiled = build_order_search(1, search).compile(dialect=sqlite.dialect())
    params = [compiled.params[name] for name in compiled.positiontup or []]
    with sqlite3.connect(database) as connection:
        rows = connection.execute(f"EXPLAIN QUERY PLAN {compiled}", params).fetchall()
    return [str(row[3]) for row in rows]


def test_schema_matches_models_when_migrated_from_empty(tmp_path: Path) -> None:
    config = alembic_config(tmp_path / "fresh.db")

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    command.check(config)


@pytest.mark.parametrize(
    ("search", "index"),
    [
        (OrderSearch(), "ix_orders_temple_id_id"),
        (OrderSearch(booking_date=date(2030, 1, 1)), "ix_orders_temple_booking_date_id"),
        (OrderSearch(status=OrderStatus.CONFIRMED), "ix_orders_temple_status_id"),
        (OrderSearch(phone="9876543210"), "ix_orders_temple_phone_id"),
        (OrderSearch(phone="9876543210", cursor=encode_cursor(50)), "ix_orders_temple_phone_id"),
        (
            OrderSearch(
                booking_date=date(2030, 1, 1),
                status=OrderStatus.CONFIRMED,
                phone="9876543210",
            ),
            None,
        ),
    ],
)
def test_order_search_uses_index_without_sorting_when_planned(
    migrated_db: Path, search: OrderSearch, index: str | None
) -> None:
    plan = query_plan(migrated_db, search)

    assert any(line.startswith("SEARCH orders USING INDEX ix_orders_temple_") for line in plan)
    if index is not None:
        assert any(f"USING INDEX {index} " in line for line in plan)
    assert not any(line.startswith("SCAN orders") for line in plan)
    assert not any("TEMP B-TREE" in line for line in plan)
