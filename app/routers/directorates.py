"""Organisational structure - directorates/departments/sections."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import Directorate, Department, Section

router = APIRouter()
WRITE = PermissionChecker(["org:manage"])
READ = PermissionChecker(["org:manage"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_directorates(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    dirs = db.query(Directorate).order_by(Directorate.name).all()
    return templates.TemplateResponse(request, "directorates/list.html", {"request": request, "user": user, "page_title": "Organisational structure", "dirs": dirs})


@router.post("/create", response_class=HTMLResponse)
def create_directorate(request: Request, name: str = Form(...), code: str = Form(...), user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    d = Directorate(name=name, code=code)
    db.add(d)
    db.commit()
    audit_log(db, "create", "directorates", record_id=d.id, user=user)
    _flash(request, "Directorate created", "success")
    return RedirectResponse(url="/directorates/", status_code=303)
