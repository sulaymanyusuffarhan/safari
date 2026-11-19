"""api module - placeholder (to be implemented)."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.auth import get_current_user

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def list_api(request: Request, user=Depends(get_current_user)):
    return HTMLResponse(f"<html><body><h2>api module</h2><p>Implementation in progress.</p><a href='/dashboard'>Back to dashboard</a></body></html>")
