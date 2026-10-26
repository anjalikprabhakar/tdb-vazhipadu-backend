from decimal import Decimal

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from assessment.column_types import Money
from assessment.db import Base


class Offering(Base):
    __tablename__ = "offerings"
    __table_args__ = (UniqueConstraint("temple_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    temple_id: Mapped[int] = mapped_column(ForeignKey("temples.id"))
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Money)
    is_active: Mapped[bool] = mapped_column(default=True)
