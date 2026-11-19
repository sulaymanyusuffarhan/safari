"""Notifications."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user
from app.models import Notification

router = APIRouter()


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_notifications(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    notes = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "notifications/list.html", {"request": request, "user": user, "page_title": "Notifications", "notes": notes})


@router.post("/{note_id}/read")
def mark_read(note_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from datetime import datetime
    note = db.query(Notification).filter(Notification.id == note_id, Notification.user_id == user.id).first()
    if note:
        note.is_read = True
        note.read_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/notifications/", status_code=303)
