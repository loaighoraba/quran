# Import every model module here so Base.metadata is complete for Alembic autogenerate.
from app.db import Base
from app.models.aya import Aya
from app.models.segment import Segment
from app.models.surah import Surah
from app.models.word import Word

__all__ = ["Aya", "Base", "Segment", "Surah", "Word"]
