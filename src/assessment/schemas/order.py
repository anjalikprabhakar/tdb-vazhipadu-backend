from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    WithJsonSchema,
    field_validator,
    model_validator,
)

from assessment.clock import today_ist
from assessment.enums import Nakshatra, OrderStatus
from assessment.ids import DbId
from assessment.pagination import decode_cursor
from assessment.phone import normalise_phone

MAX_QUANTITY_PER_ITEM = 100
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _canonical_nakshatra(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().upper().replace(" ", "_").replace("-", "_")
    return value


Phone = Annotated[str, AfterValidator(normalise_phone)]
NakshatraInput = Annotated[Nakshatra, BeforeValidator(_canonical_nakshatra)]
Cursor = Annotated[int, BeforeValidator(decode_cursor), WithJsonSchema({"type": "string"})]


class OrderItemCreate(BaseModel):
    offering_id: DbId
    quantity: int = Field(ge=1, le=MAX_QUANTITY_PER_ITEM)


class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    devotee_name: str = Field(min_length=1, max_length=200)
    phone: Phone
    nakshatra: NakshatraInput
    booking_date: date
    items: list[OrderItemCreate] = Field(min_length=1)

    @field_validator("booking_date")
    @classmethod
    def reject_past_dates(cls, value: date) -> date:
        if value < today_ist():
            raise ValueError("booking_date cannot be in the past (IST)")
        return value

    @model_validator(mode="after")
    def reject_repeated_offerings(self) -> Self:
        counts = Counter(item.offering_id for item in self.items)
        repeated = sorted(offering_id for offering_id, count in counts.items() if count > 1)
        if repeated:
            raise ValueError(f"offering ids appear more than once: {repeated}")
        return self


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offering_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    temple_id: int
    devotee_name: str
    phone: str
    nakshatra: Nakshatra
    booking_date: date
    status: OrderStatus
    items: list[OrderItemRead]
    total_amount: Decimal
    created_at: datetime


class OrderSearch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    booking_date: date | None = None
    status: OrderStatus | None = None
    phone: Phone | None = None
    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    cursor: Cursor | None = None


class OrderPage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[OrderRead]
    next_cursor: str | None
