from fastapi import APIRouter, status

from assessment.api.deps import SessionDep
from assessment.models import Temple
from assessment.schemas.temple import TempleCreate, TempleRead
from assessment.services import temples

router = APIRouter(prefix="/temples", tags=["temples"])


@router.post("", response_model=TempleRead, status_code=status.HTTP_201_CREATED)
async def create_temple(payload: TempleCreate, session: SessionDep) -> Temple:
    return await temples.create_temple(session, payload)


@router.get("/{temple_id}", response_model=TempleRead)
async def get_temple(temple_id: int, session: SessionDep) -> Temple:
    return await temples.get_temple(session, temple_id)
