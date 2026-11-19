"""Audit trail."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker
from app.models import AuditLog

router = APIRouter()
READ = PermissionChecker(["audit:read"])


@router.get("/", response_class=HTMLResponse)
def list_audit(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return templates.TemplateResponse(request, "audit/list.html", {"request": request, "user": user, "page_title": "Audit trail", "logs": logs})
