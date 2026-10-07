from fastapi import FastAPI

app = FastAPI(title="Quran API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
