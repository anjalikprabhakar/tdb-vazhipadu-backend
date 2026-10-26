from pydantic import BaseModel, ConfigDict, Field


class TempleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)


class TempleRead(TempleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
