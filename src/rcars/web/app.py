"""RCARS FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path


# Module-level singleton for Jinja2 templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Task 2: initialise DB connection pool here; Task 6: in-memory session store lives here
    yield


def create_app() -> FastAPI:
    # Import routes here to avoid circular imports
    from rcars.web.routes import advisor, curate, admin

    app = FastAPI(title="RCARS", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(advisor.router)
    app.include_router(curate.router)
    app.include_router(admin.router)
    return app


app = create_app()
