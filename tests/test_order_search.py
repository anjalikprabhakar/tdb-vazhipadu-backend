import base64
from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from assessment.clock import today_ist
from assessment.ids import MAX_DB_ID
from assessment.pagination import encode_cursor
from tests.conftest import OfferingFactory

PHONE_A = "9876543210"
PHONE_B = "9123456780"


async def place(
    client: AsyncClient, temple_id: int, offering_id: int, phone: str, booking_date: str
) -> dict[str, Any]:
    resp = await client.post(
        f"/temples/{temple_id}/orders",
        json={
            "devotee_name": "Devotee",
            "phone": phone,
            "nakshatra": "ROHINI",
            "booking_date": booking_date,
            "items": [{"offering_id": offering_id, "quantity": 1}],
        },
    )
    assert resp.status_code == 201
    body: dict[str, Any] = resp.json()
    return body


def ids(page: dict[str, Any]) -> list[int]:
    return [order["id"] for order in page["items"]]


def days_ahead(days: int) -> str:
    return (today_ist() + timedelta(days=days)).isoformat()


async def test_only_that_devotees_orders_returned_when_searching_by_phone(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    first = await place(client, temple_id, archana["id"], PHONE_A, booking_date)
    await place(client, temple_id, archana["id"], PHONE_B, booking_date)
    second = await place(client, temple_id, archana["id"], PHONE_A, days_ahead(9))
    other_temple = (await client.post("/temples", json={"name": "Attukal Temple"})).json()["id"]
    pongala = await make_offering("Pongala", "100", temple=other_temple)
    await place(client, other_temple, pongala["id"], PHONE_A, booking_date)

    resp = await client.get(f"/temples/{temple_id}/orders", params={"phone": "+91 98765-43210"})

    assert resp.status_code == 200
    body = resp.json()
    assert ids(body) == [second["id"], first["id"]]
    assert {order["phone"] for order in body["items"]} == {PHONE_A}
    assert {order["temple_id"] for order in body["items"]} == {temple_id}
    assert body["next_cursor"] is None


async def test_page_two_continues_page_one_without_repeats_or_gaps_when_paginating(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    placed = [
        (await place(client, temple_id, archana["id"], PHONE_A, booking_date))["id"]
        for _ in range(5)
    ]
    url = f"/temples/{temple_id}/orders"

    page_one = (await client.get(url, params={"limit": 2})).json()
    page_two = (
        await client.get(url, params={"limit": 2, "cursor": page_one["next_cursor"]})
    ).json()
    page_three = (
        await client.get(url, params={"limit": 2, "cursor": page_two["next_cursor"]})
    ).json()

    newest_first = sorted(placed, reverse=True)
    assert ids(page_one) == newest_first[0:2]
    assert ids(page_two) == newest_first[2:4]
    assert ids(page_three) == newest_first[4:5]
    assert page_three["next_cursor"] is None
    assert ids(page_one) + ids(page_two) + ids(page_three) == newest_first


async def test_page_two_unchanged_when_new_order_placed_between_pages(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    placed = [
        (await place(client, temple_id, archana["id"], PHONE_A, booking_date))["id"]
        for _ in range(4)
    ]
    url = f"/temples/{temple_id}/orders"
    page_one = (await client.get(url, params={"limit": 2})).json()

    await place(client, temple_id, archana["id"], PHONE_A, booking_date)
    page_two = (
        await client.get(url, params={"limit": 2, "cursor": page_one["next_cursor"]})
    ).json()

    assert ids(page_two) == sorted(placed, reverse=True)[2:4]


async def test_only_matching_order_returned_when_date_status_and_phone_combined(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    match = await place(client, temple_id, archana["id"], PHONE_A, booking_date)
    await place(client, temple_id, archana["id"], PHONE_B, booking_date)
    await place(client, temple_id, archana["id"], PHONE_A, days_ahead(9))

    resp = await client.get(
        f"/temples/{temple_id}/orders",
        params={"booking_date": booking_date, "status": "CONFIRMED", "phone": PHONE_A},
    )

    assert resp.status_code == 200
    assert ids(resp.json()) == [match["id"]]


async def test_only_that_dates_orders_returned_when_filtered_by_booking_date(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    first = await place(client, temple_id, archana["id"], PHONE_A, booking_date)
    await place(client, temple_id, archana["id"], PHONE_A, days_ahead(9))
    second = await place(client, temple_id, archana["id"], PHONE_B, booking_date)

    resp = await client.get(f"/temples/{temple_id}/orders", params={"booking_date": booking_date})

    assert resp.status_code == 200
    assert ids(resp.json()) == [second["id"], first["id"]]
    assert {order["booking_date"] for order in resp.json()["items"]} == {booking_date}


async def test_twenty_orders_and_a_cursor_returned_when_limit_omitted(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    for _ in range(21):
        await place(client, temple_id, archana["id"], PHONE_A, booking_date)

    resp = await client.get(f"/temples/{temple_id}/orders")

    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 20
    assert resp.json()["next_cursor"] is not None


async def test_full_orders_listed_when_results_found(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory, booking_date: str
) -> None:
    archana = await make_offering("Archana", "50")
    placed = await place(client, temple_id, archana["id"], PHONE_A, booking_date)

    resp = await client.get(f"/temples/{temple_id}/orders")

    assert resp.status_code == 200
    assert resp.json() == {"items": [placed], "next_cursor": None}


async def test_empty_page_returned_when_no_orders_match(
    client: AsyncClient, temple_id: int
) -> None:
    resp = await client.get(f"/temples/{temple_id}/orders", params={"phone": PHONE_A})

    assert resp.status_code == 200
    assert resp.json() == {"items": [], "next_cursor": None}


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"limit": 0}, "limit"),
        ({"limit": -1}, "limit"),
        ({"limit": 101}, "limit"),
        ({"limit": "abc"}, "limit"),
        ({"cursor": "not-a-cursor"}, "cursor"),
        ({"cursor": encode_cursor(0)}, "cursor"),
        ({"cursor": "eyJpZCI6InRlbiJ9"}, "cursor"),
        ({"cursor": base64.urlsafe_b64encode(b"[" * 5000).decode()}, "cursor"),
        ({"cursor": encode_cursor(5) + "!!!"}, "cursor"),
        ({"cursor": encode_cursor(10) + "="}, "cursor"),
        ({"cursor": base64.urlsafe_b64encode(b"05").decode().rstrip("=")}, "cursor"),
        ({"cursor": encode_cursor(MAX_DB_ID + 1)}, "cursor"),
        ({"phone": "12345"}, "phone"),
        ({"status": "UNKNOWN"}, "status"),
        ({"booking_date": "26-10-2026"}, "booking_date"),
        ({"date": "2026-10-26"}, "date"),
    ],
)
async def test_validation_error_when_search_params_invalid(
    client: AsyncClient, temple_id: int, params: dict[str, Any], field: str
) -> None:
    resp = await client.get(f"/temples/{temple_id}/orders", params=params)

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"] == "Request is invalid"
    assert [detail["field"] for detail in error["details"]] == [field]


async def test_not_found_when_searching_orders_of_missing_temple(client: AsyncClient) -> None:
    resp = await client.get("/temples/999/orders")

    assert resp.status_code == 404
    assert resp.json()["error"] == {
        "code": "not_found",
        "message": "Temple 999 not found",
        "details": [],
    }
