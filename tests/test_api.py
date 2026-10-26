from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_create_and_get_item(client: AsyncClient) -> None:
    resp = await client.post("/items", json={"name": "widget"})
    assert resp.status_code == 201
    item = resp.json()

    resp = await client.get(f"/items/{item['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "widget"


async def test_missing_item_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/items/999")
    assert resp.status_code == 404
