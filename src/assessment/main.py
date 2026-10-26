from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from assessment import models  # noqa: F401  (registers tables on Base.metadata)
from assessment.api import collections, offerings, orders, temples
from assessment.config import settings
from assessment.db import engine
from assessment.errors import register_error_handlers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
register_error_handlers(app)
app.include_router(temples.router)
app.include_router(offerings.router)
app.include_router(orders.router)
app.include_router(collections.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
