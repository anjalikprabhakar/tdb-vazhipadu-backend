import pytest
from httpx import AsyncClient


async def test_standard_error_format_when_route_unknown(client: AsyncClient) -> None:
    resp = await client.get("/does-not-exist")

    assert resp.status_code == 404
    assert resp.json() == {"error": {"code": "not_found", "message": "Not Found", "details": []}}


async def test_standard_error_format_when_method_not_allowed(client: AsyncClient) -> None:
    resp = await client.delete("/temples")

    assert resp.status_code == 405
    assert resp.json()["error"]["code"] == "method_not_allowed"


async def test_field_details_listed_when_body_invalid(client: AsyncClient) -> None:
    resp = await client.post("/temples", json={"name": ""})

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert [detail["field"] for detail in error["details"]] == ["name"]


async def test_standard_error_format_when_body_not_json(client: AsyncClient) -> None:
    resp = await client.post(
        "/temples", content=b"not json", headers={"content-type": "application/json"}
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "path",
    [
        f"/temples/{2**63}",
        f"/temples/{2**63}/offerings",
        f"/offerings/{2**63}",
        f"/orders/{2**63}",
        "/orders/0",
    ],
)
async def test_validation_error_when_path_id_out_of_range(client: AsyncClient, path: str) -> None:
    resp = await client.get(path)

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"].endswith("_id")
