from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import Connection, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from assessment.config import settings

SQLITE_IMMEDIATE = "sqlite_immediate"


def enable_sqlite_immediate(engine: AsyncEngine) -> None:
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine.sync_engine, "connect")
    def disable_driver_transactions(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine.sync_engine, "begin")
    def begin(connection: Connection) -> None:
        immediate = connection.get_execution_options().get(SQLITE_IMMEDIATE, False)
        connection.exec_driver_sql("BEGIN IMMEDIATE" if immediate else "BEGIN")


engine = create_async_engine(settings.database_url, echo=settings.debug)
enable_sqlite_immediate(engine)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def begin_write(session: AsyncSession) -> None:
    await session.connection(execution_options={SQLITE_IMMEDIATE: True})
