import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from assessment.clock import today_ist
from assessment.db import Base, enable_sqlite_immediate, get_session
from assessment.main import app
from tests.conftest import OfferingFactory


def order_body(booking_date: str, *items: tuple[int, int]) -> dict[str, Any]:
    return {
        "devotee_name": "Devotee",
        "phone": "9876543210",
        "nakshatra": "ROHINI",
        "booking_date": booking_date,
        "items": [{"offering_id": offering, "quantity": quantity} for offering, quantity in items],
    }


async def place(
    client: AsyncClient, temple_id: int, booking_date: str, *items: tuple[int, int]
) -> Response:
    return await client.post(f"/temples/{temple_id}/orders", json=order_body(booking_date, *items))


async def order_count(client: AsyncClient, temple_id: int) -> int:
    resp = await client.get(f"/temples/{temple_id}/orders", params={"limit": 100})
    return len(resp.json()["items"])


@pytest.fixture
async def file_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'app.db').as_posix()}")
    enable_sqlite_immediate(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_order_for_2_rejected_and_for_1_accepted_when_limit_5_has_4_booked(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pooja = await make_offering("Udayasthamana Pooja", "5000", daily_limit=5)
    assert (await place(client, temple_id, booking_date, (pooja["id"], 4))).status_code == 201

    rejected = await place(client, temple_id, booking_date, (pooja["id"], 2))
    accepted = await place(client, temple_id, booking_date, (pooja["id"], 1))

    assert rejected.status_code == 409
    assert rejected.json()["error"] == {
        "code": "daily_limit_exceeded",
        "message": "Some offerings do not have enough capacity on this date",
        "details": [
            {
                "offering_id": pooja["id"],
                "booking_date": booking_date,
                "requested": 2,
                "remaining": 1,
            }
        ],
    }
    assert accepted.status_code == 201
    assert await order_count(client, temple_id) == 2


async def test_exactly_5_of_20_simultaneous_orders_succeed_when_limit_is_5(
    file_client: AsyncClient,
) -> None:
    temple_id = (await file_client.post("/temples", json={"name": "Guruvayur"})).json()["id"]
    pooja = (
        await file_client.post(
            f"/temples/{temple_id}/offerings",
            json={"name": "Udayasthamana Pooja", "price": "5000", "daily_limit": 5},
        )
    ).json()
    booking_date = (today_ist() + timedelta(days=7)).isoformat()

    responses = await asyncio.gather(
        *(place(file_client, temple_id, booking_date, (pooja["id"], 1)) for _ in range(20))
    )

    statuses = sorted(resp.status_code for resp in responses)
    assert statuses == [201] * 5 + [409] * 15
    rejected = [resp.json()["error"] for resp in responses if resp.status_code == 409]
    assert {error["code"] for error in rejected} == {"daily_limit_exceeded"}
    assert all(error["details"][0]["remaining"] == 0 for error in rejected)
    assert await order_count(file_client, temple_id) == 5


async def test_nothing_booked_when_one_item_of_multi_item_order_exceeds_limit(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50", daily_limit=5)
    pooja = await make_offering("Udayasthamana Pooja", "5000", daily_limit=1)
    assert (await place(client, temple_id, booking_date, (pooja["id"], 1))).status_code == 201

    rejected = await place(client, temple_id, booking_date, (archana["id"], 2), (pooja["id"], 1))
    full_archana = await place(client, temple_id, booking_date, (archana["id"], 5))

    assert rejected.status_code == 409
    assert [detail["offering_id"] for detail in rejected.json()["error"]["details"]] == [
        pooja["id"]
    ]
    assert full_archana.status_code == 201
    assert await order_count(client, temple_id) == 2


async def test_unlimited_offering_accepts_any_quantity_when_no_limit_set(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")

    statuses = [
        (await place(client, temple_id, booking_date, (archana["id"], 100))).status_code
        for _ in range(3)
    ]

    assert archana["daily_limit"] is None
    assert statuses == [201, 201, 201]


async def test_other_booking_date_unaffected_when_one_date_is_full(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pooja = await make_offering("Udayasthamana Pooja", "5000", daily_limit=1)
    next_day = (today_ist() + timedelta(days=8)).isoformat()
    assert (await place(client, temple_id, booking_date, (pooja["id"], 1))).status_code == 201

    same_day = await place(client, temple_id, booking_date, (pooja["id"], 1))
    other_day = await place(client, temple_id, next_day, (pooja["id"], 1))

    assert same_day.status_code == 409
    assert other_day.status_code == 201


async def test_new_orders_blocked_when_limit_lowered_below_bookings(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pooja = await make_offering("Udayasthamana Pooja", "5000", daily_limit=5)
    assert (await place(client, temple_id, booking_date, (pooja["id"], 4))).status_code == 201

    patched = await client.patch(f"/offerings/{pooja['id']}", json={"daily_limit": 2})
    rejected = await place(client, temple_id, booking_date, (pooja["id"], 1))

    assert patched.status_code == 200
    assert patched.json()["daily_limit"] == 2
    assert rejected.status_code == 409
    assert rejected.json()["error"]["details"][0]["remaining"] == 0
    assert await order_count(client, temple_id) == 1


async def test_limit_removed_when_patched_to_null(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pooja = await make_offering("Udayasthamana Pooja", "5000", daily_limit=1)
    assert (await place(client, temple_id, booking_date, (pooja["id"], 1))).status_code == 201

    patched = await client.patch(f"/offerings/{pooja['id']}", json={"daily_limit": None})
    accepted = await place(client, temple_id, booking_date, (pooja["id"], 1))

    assert patched.status_code == 200
    assert patched.json()["daily_limit"] is None
    assert accepted.status_code == 201


async def test_limit_counts_bookings_made_before_limit_was_set(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pooja = await make_offering("Udayasthamana Pooja", "5000")
    assert (await place(client, temple_id, booking_date, (pooja["id"], 3))).status_code == 201

    await client.patch(f"/offerings/{pooja['id']}", json={"daily_limit": 4})
    rejected = await place(client, temple_id, booking_date, (pooja["id"], 2))

    assert rejected.status_code == 409
    assert rejected.json()["error"]["details"][0]["remaining"] == 1


@pytest.mark.parametrize("daily_limit", [0, -1, 10_001, "abc", 1.5, True, False, "5", 5.0])
async def test_validation_error_when_daily_limit_invalid(
    client: AsyncClient, temple_id: int, daily_limit: Any
) -> None:
    created = await client.post(
        f"/temples/{temple_id}/offerings",
        json={"name": "Pooja", "price": "100", "daily_limit": daily_limit},
    )

    assert created.status_code == 422
    error = created.json()["error"]
    assert error["code"] == "validation_error"
    assert [detail["field"] for detail in error["details"]] == ["daily_limit"]


async def test_offering_and_temple_writes_succeed_when_orders_placed_simultaneously(
    file_client: AsyncClient,
) -> None:
    temple_id = (await file_client.post("/temples", json={"name": "Guruvayur"})).json()["id"]
    pooja = (
        await file_client.post(
            f"/temples/{temple_id}/offerings",
            json={"name": "Udayasthamana Pooja", "price": "5000", "daily_limit": 5},
        )
    ).json()
    booking_date = (today_ist() + timedelta(days=7)).isoformat()

    orders = [place(file_client, temple_id, booking_date, (pooja["id"], 1)) for _ in range(20)]
    creates = [
        file_client.post(
            f"/temples/{temple_id}/offerings", json={"name": f"Archana {n}", "price": "50"}
        )
        for n in range(10)
    ]
    patches = [
        file_client.patch(f"/offerings/{pooja['id']}", json={"daily_limit": 5}) for _ in range(10)
    ]
    temples = [file_client.post("/temples", json={"name": f"Temple {n}"}) for n in range(5)]
    responses = await asyncio.gather(*orders, *creates, *patches, *temples)

    order_statuses = sorted(resp.status_code for resp in responses[:20])
    assert order_statuses == [201] * 5 + [409] * 15
    assert [resp.status_code for resp in responses[20:30]] == [201] * 10
    assert [resp.status_code for resp in responses[30:40]] == [200] * 10
    assert [resp.status_code for resp in responses[40:]] == [201] * 5
