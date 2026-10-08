from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db import SessionDep, engine
from app.routers import stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="Quran API", lifespan=lifespan)
app.include_router(stats.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Welcome to the Quran statistics API! Work is under progress"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
