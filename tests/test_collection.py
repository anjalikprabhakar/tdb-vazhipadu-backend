from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient, Response

from assessment.services import orders
from tests.conftest import OfferingFactory

REPORT_DATE = "2026-10-26"


def order_body(booking_date: str, *items: tuple[int, int]) -> dict[str, Any]:
    return {
        "devotee_name": "Devotee",
        "phone": "9876543210",
        "nakshatra": "ROHINI",
        "booking_date": booking_date,
        "items": [{"offering_id": offering, "quantity": quantity} for offering, quantity in items],
    }


async def place_at(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    placed_at: datetime,
    temple_id: int,
    booking_date: str,
    *items: tuple[int, int],
) -> Response:
    monkeypatch.setattr(orders, "now_utc", lambda: placed_at)
    resp = await client.post(f"/temples/{temple_id}/orders", json=order_body(booking_date, *items))
    assert resp.status_code == 201
    return resp


async def collection(client: AsyncClient, temple_id: int, day: str) -> Response:
    return await client.get(f"/temples/{temple_id}/daily-collection", params={"date": day})


async def test_order_at_0015_ist_counted_on_that_date_when_placed_at_1845_utc_day_before(
    client: AsyncClient,
    temple_id: int,
    make_offering: OfferingFactory,
    booking_date: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archana = await make_offering("Archana", "50")
    await place_at(
        client,
        monkeypatch,
        datetime(2026, 10, 25, 18, 45, tzinfo=UTC),
        temple_id,
        booking_date,
        (archana["id"], 1),
    )
    await place_at(
        client,
        monkeypatch,
        datetime(2026, 10, 25, 18, 29, 59, tzinfo=UTC),
        temple_id,
        booking_date,
        (archana["id"], 2),
    )

    on_date = await collection(client, temple_id, REPORT_DATE)
    day_before = await collection(client, temple_id, "2026-10-25")

    assert on_date.status_code == 200
    assert on_date.json()["offerings"] == [
        {"offering_id": archana["id"], "offering_name": "Archana", "count": 1, "amount": "50.00"}
    ]
    assert on_date.json()["total_amount"] == "50.00"
    assert day_before.json()["offerings"][0]["count"] == 2
    assert day_before.json()["total_amount"] == "100.00"


async def test_cancelled_order_not_counted_when_collection_reported(
    client: AsyncClient,
    temple_id: int,
    make_offering: OfferingFactory,
    booking_date: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archana = await make_offering("Archana", "50")
    pooja = await make_offering("Udayasthamana Pooja", "5000")
    placed_at = datetime(2026, 10, 26, 6, 0, tzinfo=UTC)
    await place_at(client, monkeypatch, placed_at, temple_id, booking_date, (archana["id"], 2))
    cancelled = await place_at(
        client,
        monkeypatch,
        placed_at,
        temple_id,
        booking_date,
        (archana["id"], 1),
        (pooja["id"], 1),
    )
    assert (await client.post(f"/orders/{cancelled.json()['id']}/cancel")).status_code == 200

    resp = await collection(client, temple_id, REPORT_DATE)

    assert resp.status_code == 200
    assert resp.json() == {
        "temple_id": temple_id,
        "date": REPORT_DATE,
        "offerings": [
            {
                "offering_id": archana["id"],
                "offering_name": "Archana",
                "count": 2,
                "amount": "100.00",
            }
        ],
        "total_amount": "100.00",
    }


async def test_total_equals_sum_of_offering_amounts_to_the_paisa_when_reported(
    client: AsyncClient,
    temple_id: int,
    make_offering: OfferingFactory,
    booking_date: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archana = await make_offering("Archana", "0.10")
    pushpanjali = await make_offering("Pushpanjali", "0.20")
    ganapathi = await make_offering("Ganapathi Homam", "333.33")
    placed_at = datetime(2026, 10, 26, 6, 0, tzinfo=UTC)
    for _ in range(3):
        await place_at(
            client,
            monkeypatch,
            placed_at,
            temple_id,
            booking_date,
            (archana["id"], 1),
            (pushpanjali["id"], 1),
            (ganapathi["id"], 1),
        )

    body = (await collection(client, temple_id, REPORT_DATE)).json()

    assert [
        (line["offering_name"], line["count"], line["amount"]) for line in body["offerings"]
    ] == [
        ("Archana", 3, "0.30"),
        ("Ganapathi Homam", 3, "999.99"),
        ("Pushpanjali", 3, "0.60"),
    ]
    assert body["total_amount"] == "1000.89"
    assert sum(Decimal(line["amount"]) for line in body["offerings"]) == Decimal(
        body["total_amount"]
    )


async def test_booked_price_reported_when_offering_price_changed_later(
    client: AsyncClient,
    temple_id: int,
    make_offering: OfferingFactory,
    booking_date: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archana = await make_offering("Archana", "50")
    placed_at = datetime(2026, 10, 26, 6, 0, tzinfo=UTC)
    await place_at(client, monkeypatch, placed_at, temple_id, booking_date, (archana["id"], 2))
    assert (
        await client.patch(f"/offerings/{archana['id']}", json={"price": "80"})
    ).status_code == 200

    body = (await collection(client, temple_id, REPORT_DATE)).json()

    assert body["offerings"][0]["amount"] == "100.00"
    assert body["total_amount"] == "100.00"


async def test_other_temples_orders_excluded_when_reported(
    client: AsyncClient,
    temple_id: int,
    make_offering: OfferingFactory,
    booking_date: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other = (await client.post("/temples", json={"name": "Guruvayur"})).json()["id"]
    archana = await make_offering("Archana", "50", temple=other)
    placed_at = datetime(2026, 10, 26, 6, 0, tzinfo=UTC)
    await place_at(client, monkeypatch, placed_at, other, booking_date, (archana["id"], 1))

    resp = await collection(client, temple_id, REPORT_DATE)

    assert resp.status_code == 200
    assert resp.json()["offerings"] == []
    assert resp.json()["total_amount"] == "0.00"


async def test_not_found_when_reporting_collection_of_missing_temple(client: AsyncClient) -> None:
    resp = await collection(client, 999, REPORT_DATE)

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("params", [{}, {"date": "26-10-2026"}, {"date": REPORT_DATE, "x": "1"}])
async def test_validation_error_when_collection_params_invalid(
    client: AsyncClient, temple_id: int, params: dict[str, str]
) -> None:
    resp = await client.get(f"/temples/{temple_id}/daily-collection", params=params)

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"
