from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import Integer, Select, func, select, type_coerce
from sqlalchemy.ext.asyncio import AsyncSession

from assessment.clock import IST
from assessment.column_types import Money
from assessment.enums import OrderStatus
from assessment.models import Offering, Order, OrderItem
from assessment.schemas.collection import CollectionLine, DailyCollection
from assessment.services.temples import get_temple


def ist_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=IST)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=IST)
    return start, end


def build_collection_query(temple_id: int, day: date) -> Select[int, str, int, Decimal]:
    start, end = ist_day_bounds(day)
    paise = type_coerce(OrderItem.unit_price, Integer) * OrderItem.quantity
    return (
        select(
            Offering.id,
            Offering.name,
            func.sum(OrderItem.quantity),
            type_coerce(func.sum(paise), Money),
        )
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Offering, Offering.id == OrderItem.offering_id)
        .where(
            Order.temple_id == temple_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status != OrderStatus.CANCELLED,
        )
        .group_by(Offering.id, Offering.name)
        .order_by(Offering.name, Offering.id)
    )


async def daily_collection(session: AsyncSession, temple_id: int, day: date) -> DailyCollection:
    await get_temple(session, temple_id)
    rows = await session.execute(build_collection_query(temple_id, day))
    lines = [
        CollectionLine(offering_id=offering_id, offering_name=name, count=count, amount=amount)
        for offering_id, name, count, amount in rows
    ]
    return DailyCollection(
        temple_id=temple_id,
        date=day,
        offerings=lines,
        total_amount=sum((line.amount for line in lines), Decimal("0.00")),
    )
