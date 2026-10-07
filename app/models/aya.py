from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.surah import Surah
    from app.models.word import Word


class Aya(Base):
    __tablename__ = "ayas"
    __table_args__ = (
        UniqueConstraint("surah_id", "number"),
        CheckConstraint("number >= 1", name="number_positive"),
    )

    # Tanzil's global aya index (1..6236)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    surah_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("surahs.id"))
    # Aya number within the surah
    number: Mapped[int] = mapped_column(SmallInteger)
    # Basmala stripped from aya 1; see Surah.has_basmala
    text_simple: Mapped[str] = mapped_column(Text)
    text_uthmani: Mapped[str] = mapped_column(Text)

    surah: Mapped[Surah] = relationship(back_populates="ayas")
    words: Mapped[list[Word]] = relationship(back_populates="aya", order_by="Word.number")
