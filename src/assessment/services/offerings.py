from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from assessment.db import begin_write
from assessment.errors import ConflictError, NotFoundError
from assessment.models import Offering
from assessment.schemas.offering import OfferingCreate, OfferingUpdate
from assessment.services.temples import get_temple


async def _commit_offering(session: AsyncSession, offering: Offering) -> Offering:
    name = offering.name
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(f"Offering '{name}' already exists in this temple") from exc
    return offering


async def create_offering(session: AsyncSession, temple_id: int, data: OfferingCreate) -> Offering:
    await begin_write(session)
    await get_temple(session, temple_id)
    offering = Offering(temple_id=temple_id, **data.model_dump())
    session.add(offering)
    return await _commit_offering(session, offering)


async def list_offerings(
    session: AsyncSession, temple_id: int, active: bool | None
) -> list[Offering]:
    await get_temple(session, temple_id)
    query = select(Offering).where(Offering.temple_id == temple_id)
    if active is not None:
        query = query.where(Offering.is_active == active)
    return list(await session.scalars(query.order_by(Offering.id)))


async def get_offering(session: AsyncSession, offering_id: int) -> Offering:
    offering = await session.get(Offering, offering_id)
    if offering is None:
        raise NotFoundError("Offering", offering_id)
    return offering


async def update_offering(
    session: AsyncSession, offering_id: int, data: OfferingUpdate
) -> Offering:
    await begin_write(session)
    offering = await get_offering(session, offering_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(offering, field, value)
    return await _commit_offering(session, offering)
