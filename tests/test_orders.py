from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from assessment.clock import today_ist
from tests.conftest import OfferingFactory


def order_payload(
    booking_date: str, items: list[dict[str, int]], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "devotee_name": "Anjali K",
        "phone": "9876543210",
        "nakshatra": "ROHINI",
        "booking_date": booking_date,
        "items": items,
    }
    payload.update(overrides)
    return payload


async def test_total_is_110_when_two_pushpanjali_at_30_and_one_archana_at_50(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pushpanjali = await make_offering("Pushpanjali", "30")
    archana = await make_offering("Archana", "50")
    items = [
        {"offering_id": pushpanjali["id"], "quantity": 2},
        {"offering_id": archana["id"], "quantity": 1},
    ]

    created = await client.post(
        f"/temples/{temple_id}/orders", json=order_payload(booking_date, items)
    )
    fetched = await client.get(f"/orders/{created.json()['id']}")

    assert created.status_code == 201
    assert fetched.status_code == 200
    order = fetched.json()
    assert order["total_amount"] == "110.00"
    assert order["status"] == "CONFIRMED"
    assert order["booking_date"] == booking_date
    assert [(i["unit_price"], i["quantity"], i["line_total"]) for i in order["items"]] == [
        ("30.00", 2, "60.00"),
        ("50.00", 1, "50.00"),
    ]
    assert created.json() == order


async def test_order_rejected_when_offering_inactive(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    pushpanjali = await make_offering("Pushpanjali", "30")
    inactive = await make_offering("Udayasthamana Pooja", "5000", is_active=False)
    items = [
        {"offering_id": pushpanjali["id"], "quantity": 1},
        {"offering_id": inactive["id"], "quantity": 1},
    ]

    resp = await client.post(
        f"/temples/{temple_id}/orders", json=order_payload(booking_date, items)
    )

    assert resp.status_code == 422
    assert resp.json()["error"] == {
        "code": "offering_inactive",
        "message": "Some offerings are not currently available",
        "details": [{"offering_id": inactive["id"]}],
    }
    assert (await client.get("/orders/1")).status_code == 404


async def test_order_rejected_when_offering_deactivated_after_creation(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    await client.patch(f"/offerings/{archana['id']}", json={"is_active": False})

    resp = await client.post(
        f"/temples/{temple_id}/orders",
        json=order_payload(booking_date, [{"offering_id": archana["id"], "quantity": 1}]),
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "offering_inactive"


async def test_order_rejected_when_offering_unknown(
    client: AsyncClient, temple_id: int, booking_date: str
) -> None:
    resp = await client.post(
        f"/temples/{temple_id}/orders",
        json=order_payload(booking_date, [{"offering_id": 999, "quantity": 1}]),
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "offering_not_found"
    assert resp.json()["error"]["details"] == [{"offering_id": 999}]


async def test_order_rejected_when_offering_belongs_to_other_temple(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    other = await client.post("/temples", json={"name": "Attukal Temple"})
    foreign = await make_offering("Pongala", "100", temple=other.json()["id"])

    resp = await client.post(
        f"/temples/{temple_id}/orders",
        json=order_payload(booking_date, [{"offering_id": foreign["id"], "quantity": 1}]),
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "offering_not_found"


async def test_not_found_when_ordering_at_missing_temple(
    client: AsyncClient, booking_date: str
) -> None:
    resp = await client.post(
        "/temples/999/orders",
        json=order_payload(booking_date, [{"offering_id": 1, "quantity": 1}]),
    )

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"items": []}, "items"),
        ({"items": [{"offering_id": 1, "quantity": 0}]}, "items.0.quantity"),
        ({"items": [{"offering_id": 1, "quantity": -1}]}, "items.0.quantity"),
        ({"items": [{"offering_id": 1, "quantity": 101}]}, "items.0.quantity"),
        ({"phone": "12345"}, "phone"),
        ({"phone": "5123456789"}, "phone"),
        ({"phone": "9८७६५४३२१०"}, "phone"),
        ({"nakshatra": "Pluto"}, "nakshatra"),
        ({"devotee_name": "   "}, "devotee_name"),
        ({"booking_date": "not-a-date"}, "booking_date"),
    ],
)
async def test_order_rejected_when_field_invalid(
    client: AsyncClient,
    temple_id: int,
    booking_date: str,
    overrides: dict[str, Any],
    field: str,
) -> None:
    payload = order_payload(booking_date, [{"offering_id": 1, "quantity": 1}]) | overrides

    resp = await client.post(f"/temples/{temple_id}/orders", json=payload)

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert field in [detail["field"] for detail in error["details"]]


async def test_order_rejected_when_phone_missing(
    client: AsyncClient, temple_id: int, booking_date: str
) -> None:
    payload = order_payload(booking_date, [{"offering_id": 1, "quantity": 1}])
    del payload["phone"]

    resp = await client.post(f"/temples/{temple_id}/orders", json=payload)

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert [detail["field"] for detail in error["details"]] == ["phone"]


async def test_order_rejected_when_booking_date_in_past(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory
) -> None:
    archana = await make_offering("Archana", "50")
    yesterday = (today_ist() - timedelta(days=1)).isoformat()

    resp = await client.post(
        f"/temples/{temple_id}/orders",
        json=order_payload(yesterday, [{"offering_id": archana["id"], "quantity": 1}]),
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["details"][0]["field"] == "booking_date"


async def test_order_rejected_when_offering_repeated(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    items = [
        {"offering_id": archana["id"], "quantity": 1},
        {"offering_id": archana["id"], "quantity": 2},
    ]

    resp = await client.post(
        f"/temples/{temple_id}/orders", json=order_payload(booking_date, items)
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_phone_and_nakshatra_normalised_when_given_in_loose_format(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    payload = order_payload(
        booking_date,
        [{"offering_id": archana["id"], "quantity": 1}],
        phone="+91 98765-43210",
        nakshatra="purva phalguni",
    )

    resp = await client.post(f"/temples/{temple_id}/orders", json=payload)

    assert resp.status_code == 201
    assert resp.json()["phone"] == "9876543210"
    assert resp.json()["nakshatra"] == "PURVA_PHALGUNI"


async def test_order_keeps_booked_price_when_offering_price_changes(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    created = await client.post(
        f"/temples/{temple_id}/orders",
        json=order_payload(booking_date, [{"offering_id": archana["id"], "quantity": 3}]),
    )
    await client.patch(f"/offerings/{archana['id']}", json={"price": "75.50"})

    resp = await client.get(f"/orders/{created.json()['id']}")

    assert resp.json()["total_amount"] == "150.00"
    assert resp.json()["items"][0]["unit_price"] == "50.00"


async def test_paisa_exact_total_when_prices_have_paise(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    first = await make_offering("Neyvilakku", "10.10")
    second = await make_offering("Thulabharam", "0.20")
    items = [
        {"offering_id": first["id"], "quantity": 3},
        {"offering_id": second["id"], "quantity": 1},
    ]

    resp = await client.post(
        f"/temples/{temple_id}/orders", json=order_payload(booking_date, items)
    )

    assert resp.json()["total_amount"] == "30.50"


async def test_not_found_when_order_missing(client: AsyncClient) -> None:
    resp = await client.get("/orders/999")

    assert resp.status_code == 404
    assert resp.json()["error"] == {
        "code": "not_found",
        "message": "Order 999 not found",
        "details": [],
    }


async def test_validation_error_when_offering_id_out_of_range(
    client: AsyncClient, temple_id: int, booking_date: str
) -> None:
    payload = order_payload(booking_date, [{"offering_id": 2**63, "quantity": 1}])

    resp = await client.post(f"/temples/{temple_id}/orders", json=payload)

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert [detail["field"] for detail in error["details"]] == ["items.0.offering_id"]
