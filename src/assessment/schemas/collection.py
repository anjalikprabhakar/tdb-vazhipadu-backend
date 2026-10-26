from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CollectionQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date


class CollectionLine(BaseModel):
    offering_id: int
    offering_name: str
    count: int
    amount: Decimal


class DailyCollection(BaseModel):
    temple_id: int
    date: date
    offerings: list[CollectionLine]
    total_amount: Decimal
