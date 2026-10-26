from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, or_, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from assessment.clock import today_ist
from assessment.db import begin_write
from assessment.enums import OrderStatus
from assessment.errors import (
    BusinessRuleError,
    ConflictError,
    DailyLimitExceededError,
    NotFoundError,
)
from assessment.models import Offering, OfferingDailyUsage, Order, OrderItem
from assessment.pagination import encode_cursor
from assessment.schemas.order import OrderCreate, OrderItemCreate, OrderSearch
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


async def _book_capacity(session: AsyncSession, booking_date: date, item: OrderItemCreate) -> bool:
    await session.execute(
        insert(OfferingDailyUsage)
        .values(offering_id=item.offering_id, booking_date=booking_date, booked=0)
        .on_conflict_do_nothing()
    )
    limit = select(Offering.daily_limit).where(Offering.id == item.offering_id).scalar_subquery()
    booked = await session.scalar(
        update(OfferingDailyUsage)
        .where(
            OfferingDailyUsage.offering_id == item.offering_id,
            OfferingDailyUsage.booking_date == booking_date,
            or_(limit.is_(None), OfferingDailyUsage.booked + item.quantity <= limit),
        )
        .values(booked=OfferingDailyUsage.booked + item.quantity)
        .returning(OfferingDailyUsage.booked)
        .execution_options(synchronize_session=False)
    )
    return booked is not None


async def _remaining_capacity(
    session: AsyncSession, booking_date: date, offering_ids: list[int]
) -> dict[int, int]:
    rows = await session.execute(
        select(Offering.id, Offering.daily_limit, OfferingDailyUsage.booked)
        .join(OfferingDailyUsage, OfferingDailyUsage.offering_id == Offering.id)
        .where(Offering.id.in_(offering_ids), OfferingDailyUsage.booking_date == booking_date)
    )
    return {offering_id: max((limit or 0) - booked, 0) for offering_id, limit, booked in rows}


async def _reserve_daily_capacity(
    session: AsyncSession, booking_date: date, items: list[OrderItemCreate]
) -> None:
    exceeded = [
        item
        for item in sorted(items, key=lambda item: item.offering_id)
        if not await _book_capacity(session, booking_date, item)
    ]
    if not exceeded:
        return
    remaining = await _remaining_capacity(
        session, booking_date, [item.offering_id for item in exceeded]
    )
    await session.rollback()
    raise DailyLimitExceededError(
        [
            {
                "offering_id": item.offering_id,
                "booking_date": booking_date.isoformat(),
                "requested": item.quantity,
                "remaining": remaining[item.offering_id],
            }
            for item in exceeded
        ]
    )


async def place_order(session: AsyncSession, temple_id: int, data: OrderCreate) -> Order:
    await begin_write(session)
    await get_temple(session, temple_id)
    offerings = await _load_bookable_offerings(
        session, temple_id, [item.offering_id for item in data.items]
    )
    await _reserve_daily_capacity(session, data.booking_date, data.items)

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


def _already_cancelled(order_id: int) -> ConflictError:
    return ConflictError(f"Order {order_id} is already cancelled", code="order_already_cancelled")


async def cancel_order(session: AsyncSession, order_id: int) -> Order:
    await begin_write(session)
    order = await get_order(session, order_id)
    if order.status == OrderStatus.CANCELLED:
        raise _already_cancelled(order_id)
    if order.booking_date < today_ist():
        raise ConflictError(
            f"Order {order_id} was for {order.booking_date.isoformat()}, which has passed (IST)",
            code="order_not_cancellable",
        )

    cancelled = await session.scalar(
        update(Order)
        .where(Order.id == order_id, Order.status == OrderStatus.CONFIRMED)
        .values(status=OrderStatus.CANCELLED)
        .returning(Order.id)
    )
    if cancelled is None:
        await session.rollback()
        raise _already_cancelled(order_id)
    for item in order.items:
        await session.execute(
            update(OfferingDailyUsage)
            .where(
                OfferingDailyUsage.offering_id == item.offering_id,
                OfferingDailyUsage.booking_date == order.booking_date,
            )
            .values(booked=OfferingDailyUsage.booked - item.quantity)
            .execution_options(synchronize_session=False)
        )
    await session.commit()
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
