from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assessment.errors import BusinessRuleError, NotFoundError
from assessment.models import Offering, Order, OrderItem
from assessment.schemas.order import OrderCreate
from assessment.services.temples import get_temple


async def _load_bookable_offerings(
    session: AsyncSession, temple_id: int, offering_ids: list[int]
) -> dict[int, Offering]:
    result = await session.scalars(
        select(Offering).where(Offering.id.in_(offering_ids), Offering.temple_id == temple_id)
    )
    offerings = {offering.id: offering for offering in result}

    missing = [offering_id for offering_id in offering_ids if offering_id not in offerings]
    if missing:
        raise BusinessRuleError(
            "offering_not_found",
            "Some offerings do not exist in this temple",
            [{"offering_id": offering_id} for offering_id in missing],
        )

    inactive = [offering_id for offering_id in offering_ids if not offerings[offering_id].is_active]
    if inactive:
        raise BusinessRuleError(
            "offering_inactive",
            "Some offerings are not currently available",
            [{"offering_id": offering_id} for offering_id in inactive],
        )
    return offerings


async def place_order(session: AsyncSession, temple_id: int, data: OrderCreate) -> Order:
    await get_temple(session, temple_id)
    offerings = await _load_bookable_offerings(
        session, temple_id, [item.offering_id for item in data.items]
    )

    items = [
        OrderItem(
            offering_id=item.offering_id,
            quantity=item.quantity,
            unit_price=offerings[item.offering_id].price,
        )
        for item in data.items
    ]
    order = Order(
        temple_id=temple_id,
        devotee_name=data.devotee_name,
        phone=data.phone,
        nakshatra=data.nakshatra,
        booking_date=data.booking_date,
        items=items,
        total_amount=sum((item.line_total for item in items), Decimal("0.00")),
    )
    session.add(order)
    await session.commit()
    return order


async def get_order(session: AsyncSession, order_id: int) -> Order:
    order = await session.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order", order_id)
    return order
