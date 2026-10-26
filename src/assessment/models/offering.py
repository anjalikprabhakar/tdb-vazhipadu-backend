from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from assessment.column_types import Money
from assessment.db import Base


class Offering(Base):
    __tablename__ = "offerings"
    __table_args__ = (
        UniqueConstraint("temple_id", "name"),
        CheckConstraint("daily_limit > 0", name="ck_offerings_daily_limit_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    temple_id: Mapped[int] = mapped_column(ForeignKey("temples.id"))
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Money)
    is_active: Mapped[bool] = mapped_column(default=True)
    daily_limit: Mapped[int | None]


class OfferingDailyUsage(Base):
    __tablename__ = "offering_daily_usage"
    __table_args__ = (CheckConstraint("booked >= 0", name="ck_offering_daily_usage_booked"),)

    offering_id: Mapped[int] = mapped_column(ForeignKey("offerings.id"), primary_key=True)
    booking_date: Mapped[date] = mapped_column(primary_key=True)
    booked: Mapped[int] = mapped_column(default=0)
