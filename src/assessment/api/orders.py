from fastapi import APIRouter, status

from assessment.api.deps import SessionDep
from assessment.models import Order
from assessment.schemas.order import OrderCreate, OrderRead
from assessment.services import orders

router = APIRouter(tags=["orders"])


@router.post(
    "/temples/{temple_id}/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def place_order(temple_id: int, payload: OrderCreate, session: SessionDep) -> Order:
    return await orders.place_order(session, temple_id, payload)


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, session: SessionDep) -> Order:
    return await orders.get_order(session, order_id)
