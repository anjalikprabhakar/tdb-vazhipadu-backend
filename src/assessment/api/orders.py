from typing import Annotated

from fastapi import APIRouter, Query, status

from assessment.api.deps import SessionDep
from assessment.ids import PathId
from assessment.models import Order
from assessment.schemas.order import OrderCreate, OrderPage, OrderRead, OrderSearch
from assessment.services import orders

router = APIRouter(tags=["orders"])


@router.post(
    "/temples/{temple_id}/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def place_order(temple_id: PathId, payload: OrderCreate, session: SessionDep) -> Order:
    return await orders.place_order(session, temple_id, payload)


@router.get("/temples/{temple_id}/orders", response_model=OrderPage)
async def search_orders(
    temple_id: PathId, search: Annotated[OrderSearch, Query()], session: SessionDep
) -> orders.OrderSearchResult:
    return await orders.search_orders(session, temple_id, search)


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(order_id: PathId, session: SessionDep) -> Order:
    return await orders.get_order(session, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(order_id: PathId, session: SessionDep) -> Order:
    return await orders.cancel_order(session, order_id)
