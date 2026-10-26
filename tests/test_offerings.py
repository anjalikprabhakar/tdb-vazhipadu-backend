import pytest
from httpx import AsyncClient

from tests.conftest import OfferingFactory


async def test_offering_created_active_when_flag_omitted(
    client: AsyncClient, temple_id: int
) -> None:
    resp = await client.post(
        f"/temples/{temple_id}/offerings", json={"name": "Pushpanjali", "price": 30}
    )

    assert resp.status_code == 201
    assert resp.json() == {
        "id": resp.json()["id"],
        "temple_id": temple_id,
        "name": "Pushpanjali",
        "price": "30.00",
        "is_active": True,
        "daily_limit": None,
    }


@pytest.mark.parametrize("price", [0, -10, "30.555", "abc"])
async def test_offering_rejected_when_price_invalid(
    client: AsyncClient, temple_id: int, price: object
) -> None:
    resp = await client.post(
        f"/temples/{temple_id}/offerings", json={"name": "Archana", "price": price}
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["details"][0]["field"] == "price"


async def test_conflict_when_offering_name_exists_in_temple(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory
) -> None:
    await make_offering("Archana", "50")

    resp = await client.post(
        f"/temples/{temple_id}/offerings", json={"name": "Archana", "price": "60"}
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_conflict_when_offering_renamed_to_existing_name(
    client: AsyncClient, make_offering: OfferingFactory
) -> None:
    await make_offering("Archana", "50")
    pushpanjali = await make_offering("Pushpanjali", "30")

    resp = await client.patch(f"/offerings/{pushpanjali['id']}", json={"name": "Archana"})

    assert resp.status_code == 409
    assert resp.json()["error"] == {
        "code": "conflict",
        "message": "Offering 'Archana' already exists in this temple",
        "details": [],
    }
    assert (await client.get(f"/offerings/{pushpanjali['id']}")).json()["name"] == "Pushpanjali"


async def test_not_found_when_offering_temple_missing(client: AsyncClient) -> None:
    resp = await client.post("/temples/999/offerings", json={"name": "Archana", "price": "50"})

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_offering_inactive_when_patched_inactive(
    client: AsyncClient, make_offering: OfferingFactory
) -> None:
    offering = await make_offering("Archana", "50")

    resp = await client.patch(f"/offerings/{offering['id']}", json={"is_active": False})

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["price"] == "50.00"


async def test_patch_rejected_when_field_explicitly_null(
    client: AsyncClient, make_offering: OfferingFactory
) -> None:
    offering = await make_offering("Archana", "50")

    resp = await client.patch(f"/offerings/{offering['id']}", json={"price": None})

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_not_found_when_patching_missing_offering(client: AsyncClient) -> None:
    resp = await client.patch("/offerings/999", json={"is_active": False})

    assert resp.status_code == 404


async def test_only_active_listed_when_filtered_by_active(
    client: AsyncClient, temple_id: int, make_offering: OfferingFactory
) -> None:
    active = await make_offering("Pushpanjali", "30")
    await make_offering("Udayasthamana Pooja", "5000", is_active=False)

    resp = await client.get(f"/temples/{temple_id}/offerings", params={"active": "true"})

    assert resp.status_code == 200
    assert [offering["id"] for offering in resp.json()] == [active["id"]]
