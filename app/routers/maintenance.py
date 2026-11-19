"""Maintenance management."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import MaintenanceRecord, Vehicle, MaintenanceCategory

router = APIRouter()
WRITE = PermissionChecker(["maintenance:create", "maintenance:update"])
READ = PermissionChecker(["maintenance:read"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_maintenance(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    records = db.query(MaintenanceRecord).options(joinedload(MaintenanceRecord.vehicle)).order_by(MaintenanceRecord.date_reported.desc()).all()
    return templates.TemplateResponse(request, "maintenance/list.html", {"request": request, "user": user, "page_title": "Maintenance & repairs", "records": records})


@router.get("/new", response_class=HTMLResponse)
def new_maintenance(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()  # noqa
    cats = db.query(MaintenanceCategory).filter(MaintenanceCategory.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "maintenance/form.html", {"request": request, "user": user, "page_title": "Record maintenance", "vehicles": vehicles, "cats": cats, "rec": None})


@router.post("/create", response_class=HTMLResponse)
def create_maintenance(
    request: Request,
    vehicle_id: int = Form(...),
    category_id: int = Form(None),
    reported_problem: str = Form(...),
    date_reported: str = Form(...),
    mileage: int = Form(None),
    assigned_mechanic_workshop: str = Form(None),
    estimated_cost: float = Form(None),
    actual_cost: float = Form(None),
    status: str = Form("reported"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    rec = MaintenanceRecord(
        vehicle_id=vehicle_id, category_id=category_id, reported_problem=reported_problem,
        date_reported=datetime.strptime(date_reported, "%Y-%m-%d").date(), mileage=mileage,
        assigned_mechanic_workshop=assigned_mechanic_workshop, estimated_cost=estimated_cost,
        actual_cost=actual_cost, status=status,
    )
    db.add(rec)
    db.flush()
    audit_log(db, "create", "maintenance_records", record_id=rec.id, user=user,
              ip_address=request.client.host if request.client else None)
    db.commit()
    _flash(request, "Maintenance record created", "success")
    return RedirectResponse(url="/maintenance/", status_code=303)
