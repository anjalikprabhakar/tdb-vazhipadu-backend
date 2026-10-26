from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from assessment.api.deps import SessionDep
from assessment.models import Item
from assessment.schemas.item import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, session: SessionDep) -> Item:
    item = Item(**payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("", response_model=list[ItemRead])
async def list_items(session: SessionDep) -> list[Item]:
    result = await session.scalars(select(Item).order_by(Item.id))
    return list(result)


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: int, session: SessionDep) -> Item:
    item = await session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
