from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient, Response

from assessment.clock import today_ist
from assessment.services import orders
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


async def test_order_cancelled_and_kept_when_cancel_requested(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    placed = (await place(client, temple_id, booking_date, (archana["id"], 2))).json()

    cancelled = await client.post(f"/orders/{placed['id']}/cancel")
    fetched = await client.get(f"/orders/{placed['id']}")
    searched = await client.get(f"/temples/{temple_id}/orders", params={"status": "CANCELLED"})

    assert cancelled.status_code == 200
    assert cancelled.json() == {**placed, "status": "CANCELLED"}
    assert fetched.json() == cancelled.json()
    assert [order["id"] for order in searched.json()["items"]] == [placed["id"]]


async def test_daily_limit_available_again_when_order_cancelled(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pooja = await make_offering("Udayasthamana Pooja", "5000", daily_limit=5)
    archana = await make_offering("Archana", "50", daily_limit=2)
    first = await place(client, temple_id, booking_date, (pooja["id"], 3), (archana["id"], 2))
    assert (await place(client, temple_id, booking_date, (pooja["id"], 2))).status_code == 201
    assert (await place(client, temple_id, booking_date, (pooja["id"], 3))).status_code == 409

    cancel = await client.post(f"/orders/{first.json()['id']}/cancel")
    rebooked = await place(client, temple_id, booking_date, (pooja["id"], 3), (archana["id"], 2))
    overbooked = await place(client, temple_id, booking_date, (pooja["id"], 1))

    assert cancel.status_code == 200
    assert rebooked.status_code == 201
    assert overbooked.status_code == 409
    assert overbooked.json()["error"]["details"][0]["remaining"] == 0


async def test_not_found_when_cancelling_unknown_order(client: AsyncClient) -> None:
    resp = await client.post("/orders/999/cancel")

    assert resp.status_code == 404
    assert resp.json() == {
        "error": {"code": "not_found", "message": "Order 999 not found", "details": []}
    }


async def test_conflict_and_limit_released_once_when_order_cancelled_twice(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pooja = await make_offering("Udayasthamana Pooja", "5000", daily_limit=2)
    first = (await place(client, temple_id, booking_date, (pooja["id"], 2))).json()
    await client.post(f"/orders/{first['id']}/cancel")
    assert (await place(client, temple_id, booking_date, (pooja["id"], 2))).status_code == 201

    repeat = await client.post(f"/orders/{first['id']}/cancel")
    overbooked = await place(client, temple_id, booking_date, (pooja["id"], 1))

    assert repeat.status_code == 409
    assert repeat.json() == {
        "error": {
            "code": "order_already_cancelled",
            "message": f"Order {first['id']} is already cancelled",
            "details": [],
        }
    }
    assert overbooked.status_code == 409


async def test_conflict_when_cancelling_order_whose_booking_date_has_passed(
    client: AsyncClient,
    temple_id: int,
    make_offering: OfferingFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archana = await make_offering("Archana", "50")
    today = today_ist()
    placed = (await place(client, temple_id, today.isoformat(), (archana["id"], 1))).json()
    monkeypatch.setattr(orders, "today_ist", lambda: today + timedelta(days=1))

    resp = await client.post(f"/orders/{placed['id']}/cancel")
    fetched = await client.get(f"/orders/{placed['id']}")

    assert resp.status_code == 409
    assert resp.json()["error"] == {
        "code": "order_not_cancellable",
        "message": f"Order {placed['id']} was for {today.isoformat()}, which has passed (IST)",
        "details": [],
    }
    assert fetched.json()["status"] == "CONFIRMED"


async def test_order_cancellable_when_booking_date_is_today_in_ist(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory
) -> None:
    archana = await make_offering("Archana", "50")
    placed = await place(client, temple_id, today_ist().isoformat(), (archana["id"], 1))

    resp = await client.post(f"/orders/{placed.json()['id']}/cancel")

    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
