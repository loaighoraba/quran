from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db import SessionDep, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="Quran API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
