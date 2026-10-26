from typing import Annotated

from fastapi import APIRouter, Query

from assessment.api.deps import SessionDep
from assessment.ids import PathId
from assessment.schemas.collection import CollectionQuery, DailyCollection
from assessment.services import collections

router = APIRouter(tags=["collections"])


@router.get("/temples/{temple_id}/daily-collection", response_model=DailyCollection)
async def daily_collection(
    temple_id: PathId, query: Annotated[CollectionQuery, Query()], session: SessionDep
) -> DailyCollection:
    return await collections.daily_collection(session, temple_id, query.date)
