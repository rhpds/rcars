from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from rcars.config import Settings
from rcars.db import Database
from rcars.web.routes import advisor, curate, admin

_db: Database | None = None


def get_db() -> Database:
    if _db is None:
        raise RuntimeError("Database not initialized — is the app running?")
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db
    settings = Settings()
    # Only initialize DB if a database URL is provided
    if settings.database_url:
        _db = Database(settings.database_url)
        _db.create_schema()
    yield
    if _db:
        _db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="RCARS", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(advisor.router)
    app.include_router(curate.router)
    app.include_router(admin.router)
    return app


app = create_app()
