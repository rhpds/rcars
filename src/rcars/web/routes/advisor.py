"""Advisor routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from rcars.web.templates_registry import templates

router = APIRouter()


@router.get("/advisor", response_class=HTMLResponse)
async def advisor(request: Request):
    return templates.TemplateResponse(request=request, name="advisor.html")
