from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from assessment.errors import BusinessRuleError, NotFoundError
from assessment.models import Offering, Order, OrderItem
from assessment.pagination import encode_cursor
from assessment.schemas.order import OrderCreate, OrderSearch
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


@dataclass(frozen=True)
class OrderSearchResult:
    items: list[Order]
    next_cursor: str | None


def build_order_search(temple_id: int, search: OrderSearch) -> Select[Order]:
    query = select(Order).where(Order.temple_id == temple_id)
    if search.booking_date is not None:
        query = query.where(Order.booking_date == search.booking_date)
    if search.status is not None:
        query = query.where(Order.status == search.status)
    if search.phone is not None:
        query = query.where(Order.phone == search.phone)
    if search.cursor is not None:
        query = query.where(Order.id < search.cursor)
    return query.order_by(Order.id.desc()).limit(search.limit + 1)


async def search_orders(
    session: AsyncSession, temple_id: int, search: OrderSearch
) -> OrderSearchResult:
    await get_temple(session, temple_id)
    found = list(await session.scalars(build_order_search(temple_id, search)))
    page = found[: search.limit]
    next_cursor = encode_cursor(page[-1].id) if len(found) > search.limit else None
    return OrderSearchResult(items=page, next_cursor=next_cursor)
