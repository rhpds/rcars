"""RCARS FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from rcars.web.routes import advisor, curate, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


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
