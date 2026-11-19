"""Vehicle register and availability."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import Vehicle, VehicleCategory, Department, Driver, VehicleStatusHistory

router = APIRouter()

READ = PermissionChecker(["vehicle:read"])
WRITE = PermissionChecker(["vehicle:create", "vehicle:update", "vehicle:delete", "vehicle:status:change"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def list_vehicles(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db),
    _=Depends(READ),
):
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).order_by(Vehicle.registration_number).all()  # noqa
    categories = db.query(VehicleCategory).filter(VehicleCategory.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "vehicles/list.html", {
        "request": request, "user": user, "page_title": "Fleet register",
        "vehicles": vehicles, "categories": categories,
    })


# ---------------------------------------------------------------------------
# Create / edit
# ---------------------------------------------------------------------------
@router.get("/new", response_class=HTMLResponse)
def new_vehicle(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    categories = db.query(VehicleCategory).filter(VehicleCategory.is_active == True).all()  # noqa
    departments = db.query(Department).filter(Department.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "vehicles/form.html", {
        "request": request, "user": user, "page_title": "Register vehicle",
        "vehicle": None, "categories": categories,
        "departments": departments, "drivers": drivers,
    })


@router.post("/create", response_class=HTMLResponse)
def create_vehicle(
    request: Request,
    registration_number: str = Form(...),
    make: str = Form(...),
    model: str = Form(...),
    year_of_manufacture: int = Form(None),
    category_id: int = Form(None),
    fuel_type: str = Form("diesel"),
    passenger_capacity: int = Form(5),
    acquisition_date: str = Form(None),
    acquisition_cost: float = Form(None),
    status: str = Form("available"),
    owned_by_department_id: int = Form(None),
    assigned_driver_id: int = Form(None),
    notes: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    v = Vehicle(
        registration_number=registration_number.upper(), make=make, model=model,
        year_of_manufacture=year_of_manufacture, category_id=category_id, fuel_type=fuel_type,
        passenger_capacity=passenger_capacity, status=status,
        owned_by_department_id=owned_by_department_id, assigned_driver_id=assigned_driver_id,
        notes=notes, is_active=True,
    )
    if acquisition_date:
        from datetime import datetime
        v.acquisition_date = datetime.strptime(acquisition_date, "%Y-%m-%d").date()
    if acquisition_cost:
        v.acquisition_cost = acquisition_cost
    db.add(v)
    db.flush()
    # status history
    db.add(VehicleStatusHistory(vehicle_id=v.id, previous_status=None, new_status=status,
                                changed_by=user.id, reason="Initial registration"))
    db.commit()
    audit_log(db, "create", "vehicles", record_id=v.id, new_value=registration_number, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Vehicle registered", "success")
    return RedirectResponse(url="/vehicles/", status_code=303)


@router.get("/{v_id}/edit", response_class=HTMLResponse)
def edit_vehicle(
    v_id: int, request: Request, user=Depends(get_current_user),
    db: Session = Depends(get_db), _=Depends(WRITE),
):
    v = db.query(Vehicle).get(v_id)
    if not v:
        return RedirectResponse(url="/vehicles/", status_code=303)
    categories = db.query(VehicleCategory).filter(VehicleCategory.is_active == True).all()  # noqa
    departments = db.query(Department).filter(Department.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "vehicles/form.html", {
        "request": request, "user": user, "page_title": "Edit vehicle",
        "vehicle": v, "categories": categories,
        "departments": departments, "drivers": drivers,
    })


@router.post("/{v_id}/update", response_class=HTMLResponse)
def update_vehicle(
    v_id: int, request: Request,
    make: str = Form(...), model: str = Form(...),
    year_of_manufacture: int = Form(None), category_id: int = Form(None),
    fuel_type: str = Form("diesel"), passenger_capacity: int = Form(5),
    acquisition_date: str = Form(None), acquisition_cost: float = Form(None),
    owned_by_department_id: int = Form(None), assigned_driver_id: int = Form(None),
    notes: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db), _=Depends(WRITE),
):
    v = db.query(Vehicle).get(v_id)
    if not v:
        return RedirectResponse(url="/vehicles/", status_code=303)
    v.make = make; v.model = model; v.year_of_manufacture = year_of_manufacture
    v.category_id = category_id; v.fuel_type = fuel_type
    v.passenger_capacity = passenger_capacity
    v.owned_by_department_id = owned_by_department_id
    v.assigned_driver_id = assigned_driver_id; v.notes = notes
    if acquisition_date:
        from datetime import datetime
        v.acquisition_date = datetime.strptime(acquisition_date, "%Y-%m-%d").date()
    if acquisition_cost:
        v.acquisition_cost = acquisition_cost
    db.commit()
    audit_log(db, "update", "vehicles", record_id=v.id, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Vehicle updated", "success")
    return RedirectResponse(url="/vehicles/", status_code=303)


# ---------------------------------------------------------------------------
# Status change (with mandatory reason + audit) - transparency feature
# ---------------------------------------------------------------------------
@router.post("/{v_id}/status", response_class=HTMLResponse)
def change_vehicle_status(
    v_id: int, request: Request,
    new_status: str = Form(...), reason: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db), _=Depends(WRITE),
):
    v = db.query(Vehicle).get(v_id)
    if not v:
        return RedirectResponse(url="/vehicles/", status_code=303)
    if not reason or not reason.strip():
        _flash(request, "A reason is required to change vehicle status", "error")
        return RedirectResponse(url="/vehicles/", status_code=303)
    old = v.status
    v.status = new_status
    db.add(VehicleStatusHistory(vehicle_id=v.id, previous_status=old, new_status=new_status,
                                changed_by=user.id, reason=reason.strip()))
    db.commit()
    audit_log(db, "status_change", "vehicles", record_id=v.id,
              previous_value=old, new_value=new_status, reason=reason.strip(), user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, f"Vehicle status changed to {new_status}", "success")
    return RedirectResponse(url="/vehicles/", status_code=303)


@router.post("/{v_id}/deactivate", response_class=HTMLResponse)
def deactivate_vehicle(
    v_id: int, request: Request,
    reason: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db), _=Depends(WRITE),
):
    v = db.query(Vehicle).get(v_id)
    if not v:
        return RedirectResponse(url="/vehicles/", status_code=303)
    v.is_active = False
    v.deactivated_at = None
    from datetime import datetime
    v.deactivated_at = datetime.utcnow()
    v.deactivation_reason = reason
    db.commit()
    audit_log(db, "deactivate", "vehicles", record_id=v.id, reason=reason, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Vehicle deactivated (history preserved)", "success")
    return RedirectResponse(url="/vehicles/", status_code=303)


# ---------------------------------------------------------------------------
# Availability check (HTMX) - explain why a vehicle is unavailable
# ---------------------------------------------------------------------------
@router.get("/api/availability/{v_id}")
def vehicle_availability(v_id: int, db: Session = Depends(get_db)):
    v = db.query(Vehicle).get(v_id)
    if not v:
        return JSONResponse({"error": "not found"}, status_code=404)
    reasons = []
    if v.status != "available":
        reasons.append(f"Status: {v.status}")
    if v.assigned_driver_id:
        d = db.query(Driver).get(v.assigned_driver_id)
        reasons.append(f"Driver: {d.employee.full_name if d and d.employee else d} ({d.availability if d else 'unknown'})")
    return JSONResponse({"registration": v.registration_number, "status": v.status, "reasons": reasons})
