"""Breakdown reporting."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import BreakdownReport, Vehicle, Driver

router = APIRouter()
WRITE = PermissionChecker(["breakdown:create"])
READ = PermissionChecker(["breakdown:read"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_breakdowns(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    records = db.query(BreakdownReport).options(joinedload(BreakdownReport.vehicle)).order_by(BreakdownReport.breakdown_datetime.desc()).all()
    return templates.TemplateResponse(request, "breakdowns/list.html", {"request": request, "user": user, "page_title": "Breakdown reports", "records": records})


@router.get("/new", response_class=HTMLResponse)
def new_breakdown(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "breakdowns/form.html", {"request": request, "user": user, "page_title": "Report breakdown", "vehicles": vehicles, "drivers": drivers, "rec": None})


@router.post("/create", response_class=HTMLResponse)
def create_breakdown(
    request: Request,
    vehicle_id: int = Form(...),
    driver_id: int = Form(None),
    location: str = Form(...),
    breakdown_datetime: str = Form(...),
    nature: str = Form(...),
    description: str = Form(None),
    passengers_safe: str = Form("true"),
    towing_required: str = Form("false"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    rec = BreakdownReport(
        vehicle_id=vehicle_id, driver_id=driver_id, location=location,
        breakdown_datetime=datetime.strptime(breakdown_datetime, "%Y-%m-%dT%H:%M"),
        nature=nature, description=description,
        passengers_safe=(passengers_safe == "true"), towing_required=(towing_required == "true"),
        reported_by=user.id, status="reported",
    )
    db.add(rec)
    db.flush()
    # mark vehicle unavailable
    v = db.query(Vehicle).get(vehicle_id)
    if v:
        v.status = "out_of_service"
    db.commit()
    audit_log(db, "create", "breakdown_reports", record_id=rec.id, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Breakdown reported; vehicle marked out of service", "success")
    return RedirectResponse(url="/breakdowns/", status_code=303)
