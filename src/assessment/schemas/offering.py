from decimal import Decimal
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

PAISA = Decimal("0.01")
MAX_DAILY_LIMIT = 10_000
NULLABLE_FIELDS = frozenset({"daily_limit"})


def _to_paisa(value: Decimal) -> Decimal:
    return value.quantize(PAISA)


Price = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2), AfterValidator(_to_paisa)]
OfferingName = Annotated[str, Field(min_length=1, max_length=100)]
DailyLimit = Annotated[int, Field(strict=True, ge=1, le=MAX_DAILY_LIMIT)]


class OfferingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: OfferingName
    price: Price
    is_active: bool = True
    daily_limit: DailyLimit | None = None


class OfferingUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: OfferingName | None = None
    price: Price | None = None
    is_active: bool | None = None
    daily_limit: DailyLimit | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        nulls = sorted(
            field
            for field in self.model_fields_set - NULLABLE_FIELDS
            if getattr(self, field) is None
        )
        if nulls:
            raise ValueError(f"{', '.join(nulls)} cannot be null")
        return self


class OfferingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    temple_id: int
    name: str
    price: Decimal
    is_active: bool
    daily_limit: int | None
