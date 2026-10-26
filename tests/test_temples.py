from httpx import AsyncClient


async def test_temple_retrievable_when_created(client: AsyncClient) -> None:
    created = await client.post("/temples", json={"name": "  Ambalappuzha Temple  "})

    resp = await client.get(f"/temples/{created.json()['id']}")

    assert created.status_code == 201
    assert resp.status_code == 200
    assert resp.json() == {"id": created.json()["id"], "name": "Ambalappuzha Temple"}


async def test_conflict_when_temple_name_exists(client: AsyncClient) -> None:
    await client.post("/temples", json={"name": "Guruvayur Temple"})

    resp = await client.post("/temples", json={"name": "Guruvayur Temple"})

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_not_found_when_temple_missing(client: AsyncClient) -> None:
    resp = await client.get("/temples/999")

    assert resp.status_code == 404
    assert resp.json()["error"] == {
        "code": "not_found",
        "message": "Temple 999 not found",
        "details": [],
    }
