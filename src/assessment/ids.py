from typing import Annotated

from fastapi import Path
from pydantic import Field

MAX_DB_ID = 2**63 - 1

DbId = Annotated[int, Field(gt=0, le=MAX_DB_ID)]
PathId = Annotated[int, Path(gt=0, le=MAX_DB_ID)]
