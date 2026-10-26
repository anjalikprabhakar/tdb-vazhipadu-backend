from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from assessment.db import Base


class Temple(Base):
    __tablename__ = "temples"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
