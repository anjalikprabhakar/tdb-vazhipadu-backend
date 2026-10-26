from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import timedelta
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from assessment.clock import today_ist
from assessment.db import Base, enable_sqlite_immediate, get_session
from assessment.main import app

OfferingFactory = Callable[..., Awaitable[dict[str, Any]]]


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
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


@pytest.fixture
async def temple_id(client: AsyncClient) -> int:
    resp = await client.post("/temples", json={"name": "Sree Padmanabhaswamy Temple"})
    assert resp.status_code == 201
    return int(resp.json()["id"])


@pytest.fixture
def make_offering(client: AsyncClient, temple_id: int) -> OfferingFactory:
    async def make(
        name: str,
        price: str,
        *,
        is_active: bool = True,
        temple: int | None = None,
        daily_limit: int | None = None,
    ) -> dict[str, Any]:
        resp = await client.post(
            f"/temples/{temple or temple_id}/offerings",
            json={"name": name, "price": price, "is_active": is_active, "daily_limit": daily_limit},
        )
        assert resp.status_code == 201
        body: dict[str, Any] = resp.json()
        return body

    return make


@pytest.fixture
def booking_date() -> str:
    return (today_ist() + timedelta(days=7)).isoformat()
