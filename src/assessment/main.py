from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from assessment import models  # noqa: F401  (registers tables on Base.metadata)
from assessment.api import items
from assessment.config import settings
from assessment.db import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(items.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
