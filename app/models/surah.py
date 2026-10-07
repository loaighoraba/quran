from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.aya import Aya


class Surah(Base):
    __tablename__ = "surahs"
    __table_args__ = (
        CheckConstraint("revelation_type IN ('meccan', 'medinan')", name="revelation_type"),
    )

    # The surah number (1..114); there is no separate `number` column.
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    name_arabic: Mapped[str] = mapped_column(String(50))
    name_transliterated: Mapped[str] = mapped_column(String(50))
    name_english: Mapped[str] = mapped_column(String(100))
    revelation_type: Mapped[str] = mapped_column(String(7))
    revelation_order: Mapped[int] = mapped_column(SmallInteger, unique=True)
    aya_count: Mapped[int] = mapped_column(SmallInteger)
    # False for 1 (the basmala is aya 1 itself) and 9 (no basmala)
    has_basmala: Mapped[bool]

    ayas: Mapped[list[Aya]] = relationship(back_populates="surah", order_by="Aya.number")
