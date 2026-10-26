from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from assessment.db import begin_write
from assessment.errors import ConflictError, NotFoundError
from assessment.models import Temple
from assessment.schemas.temple import TempleCreate


async def create_temple(session: AsyncSession, data: TempleCreate) -> Temple:
    await begin_write(session)
    temple = Temple(name=data.name)
    session.add(temple)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(f"Temple '{data.name}' already exists") from exc
    return temple


async def get_temple(session: AsyncSession, temple_id: int) -> Temple:
    temple = await session.get(Temple, temple_id)
    if temple is None:
        raise NotFoundError("Temple", temple_id)
    return temple
