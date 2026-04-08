"""Advisor routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/advisor", response_class=HTMLResponse)
async def advisor(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="advisor.html",
        context={"request": request}
    )
