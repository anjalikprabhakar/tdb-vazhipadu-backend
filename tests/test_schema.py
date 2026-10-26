import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Select
from sqlalchemy.dialects import sqlite

from assessment.enums import OrderStatus
from assessment.pagination import encode_cursor
from assessment.schemas.order import OrderSearch
from assessment.services.collections import build_collection_query
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


def query_plan(database: Path, query: Select[*tuple[Any, ...]]) -> list[str]:
    compiled = query.compile(dialect=sqlite.dialect())
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
    plan = query_plan(migrated_db, build_order_search(1, search))

    assert any(line.startswith("SEARCH orders USING INDEX ix_orders_temple_") for line in plan)
    if index is not None:
        assert any(f"USING INDEX {index} " in line for line in plan)
    assert not any(line.startswith("SCAN orders") for line in plan)
    assert not any("TEMP B-TREE" in line for line in plan)


def test_collection_report_uses_created_at_index_when_planned(migrated_db: Path) -> None:
    plan = query_plan(migrated_db, build_collection_query(1, date(2026, 10, 26)))

    assert any("SEARCH orders USING INDEX ix_orders_temple_created_at" in line for line in plan)
    assert not any(line.startswith("SCAN orders") for line in plan)


def test_daily_usage_backfilled_from_existing_orders_when_migrated(tmp_path: Path) -> None:
    database = tmp_path / "upgrade.db"
    config = alembic_config(database)
    command.upgrade(config, "0002")
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            INSERT INTO temples (id, name) VALUES (1, 'Guruvayur');
            INSERT INTO offerings (id, temple_id, name, price, is_active)
                VALUES (1, 1, 'Archana', 5000, 1), (2, 1, 'Pooja', 500000, 1);
            INSERT INTO orders (id, temple_id, devotee_name, phone, nakshatra, booking_date,
                                status, total_amount, created_at)
                VALUES (1, 1, 'A', '9876543210', 'ROHINI', '2030-01-01', 'CONFIRMED', 0,
                        '2026-10-26 00:00:00+00:00'),
                       (2, 1, 'B', '9876543210', 'ROHINI', '2030-01-01', 'CONFIRMED', 0,
                        '2026-10-26 00:00:00+00:00'),
                       (3, 1, 'C', '9876543210', 'ROHINI', '2030-01-02', 'CONFIRMED', 0,
                        '2026-10-26 00:00:00+00:00');
            INSERT INTO order_items (order_id, offering_id, quantity, unit_price)
                VALUES (1, 1, 2, 5000), (1, 2, 1, 500000), (2, 1, 3, 5000), (3, 1, 4, 5000);
            """
        )

    command.upgrade(config, "head")

    with sqlite3.connect(database) as connection:
        usage = connection.execute(
            "SELECT offering_id, booking_date, booked FROM offering_daily_usage ORDER BY 1, 2"
        ).fetchall()
        limits = connection.execute("SELECT daily_limit FROM offerings").fetchall()
    assert usage == [(1, "2030-01-01", 5), (1, "2030-01-02", 4), (2, "2030-01-01", 1)]
    assert limits == [(None,), (None,)]
