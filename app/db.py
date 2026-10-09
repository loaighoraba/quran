from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings

# Deterministic constraint names, so Alembic can alter/drop them in later migrations
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def build_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url, echo=settings.db_echo, pool_pre_ping=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


type SessionDep = Annotated[Session, Depends(get_session)]
