from fastapi import APIRouter, status

from assessment.api.deps import SessionDep
from assessment.ids import PathId
from assessment.models import Offering
from assessment.schemas.offering import OfferingCreate, OfferingRead, OfferingUpdate
from assessment.services import offerings

router = APIRouter(tags=["offerings"])


@router.post(
    "/temples/{temple_id}/offerings",
    response_model=OfferingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_offering(
    temple_id: PathId, payload: OfferingCreate, session: SessionDep
) -> Offering:
    return await offerings.create_offering(session, temple_id, payload)


@router.get("/temples/{temple_id}/offerings", response_model=list[OfferingRead])
async def list_offerings(
    temple_id: PathId, session: SessionDep, active: bool | None = None
) -> list[Offering]:
    return await offerings.list_offerings(session, temple_id, active)


@router.get("/offerings/{offering_id}", response_model=OfferingRead)
async def get_offering(offering_id: PathId, session: SessionDep) -> Offering:
    return await offerings.get_offering(session, offering_id)


@router.patch("/offerings/{offering_id}", response_model=OfferingRead)
async def update_offering(
    offering_id: PathId, payload: OfferingUpdate, session: SessionDep
) -> Offering:
    return await offerings.update_offering(session, offering_id, payload)
