from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from assessment.clock import now_utc
from assessment.column_types import Money, UtcDateTime
from assessment.db import Base
from assessment.enums import Nakshatra, OrderStatus


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("order_id", "offering_id"),
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    offering_id: Mapped[int] = mapped_column(ForeignKey("offerings.id"))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Money)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_temple_id_id", "temple_id", "id"),
        Index("ix_orders_temple_booking_date_id", "temple_id", "booking_date", "id"),
        Index("ix_orders_temple_status_id", "temple_id", "status", "id"),
        Index("ix_orders_temple_phone_id", "temple_id", "phone", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    temple_id: Mapped[int] = mapped_column(ForeignKey("temples.id"))
    devotee_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(10))
    nakshatra: Mapped[Nakshatra] = mapped_column(Enum(Nakshatra, native_enum=False))
    booking_date: Mapped[date]
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=20), default=OrderStatus.CONFIRMED
    )
    total_amount: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now_utc)
    items: Mapped[list[OrderItem]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by=OrderItem.id
    )
