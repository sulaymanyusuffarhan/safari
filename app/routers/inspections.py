"""Vehicle inspections."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import VehicleInspection, Vehicle, Driver

router = APIRouter()
WRITE = PermissionChecker(["inspection:create"])
READ = PermissionChecker(["inspection:read"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_inspections(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    records = db.query(VehicleInspection).options(joinedload(VehicleInspection.vehicle)).order_by(VehicleInspection.inspection_date.desc()).all()
    return templates.TemplateResponse(request, "inspections/list.html", {"request": request, "user": user, "page_title": "Vehicle inspections", "records": records})


@router.get("/new", response_class=HTMLResponse)
def new_inspection(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "inspections/form.html", {"request": request, "user": user, "page_title": "Vehicle inspection", "vehicles": vehicles, "drivers": drivers, "rec": None})


@router.post("/create", response_class=HTMLResponse)
def create_inspection(
    request: Request,
    vehicle_id: int = Form(...),
    driver_id: int = Form(None),
    inspection_type: str = Form("before_trip"),
    checklist: str = Form("{}"),
    defects: str = Form(None),
    passed: str = Form("true"),
    odometer_reading: int = Form(None),
    fuel_level: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    rec = VehicleInspection(
        vehicle_id=vehicle_id, driver_id=driver_id, inspection_type=inspection_type,
        checklist=checklist, defects=defects, inspection_date=datetime.utcnow(),
        odometer_reading=odometer_reading, fuel_level=fuel_level, passed=(passed == "true"),
    )
    db.add(rec)
    db.flush()
    audit_log(db, "create", "vehicle_inspections", record_id=rec.id, user=user,
              ip_address=request.client.host if request.client else None)
    db.commit()
    _flash(request, "Inspection recorded", "success")
    return RedirectResponse(url="/inspections/", status_code=303)
