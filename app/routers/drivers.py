"""Driver register."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import Driver, Employee

router = APIRouter()

READ = PermissionChecker(["driver:read"])
WRITE = PermissionChecker(["driver:create", "driver:update"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_drivers(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    drivers = db.query(Driver).filter(Driver.is_active == True).order_by(Driver.created_at.desc()).all()  # noqa
    return templates.TemplateResponse(request, "drivers/list.html", {
        "request": request, "user": user, "page_title": "Driver register", "drivers": drivers,
    })


@router.get("/new", response_class=HTMLResponse)
def new_driver(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    employees = db.query(Employee).filter(Employee.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "drivers/form.html", {
        "request": request, "user": user, "page_title": "Register driver",
        "driver": None, "employees": employees,
    })


@router.post("/create", response_class=HTMLResponse)
def create_driver(
    request: Request,
    employee_id: int = Form(...),
    licence_number: str = Form(...),
    licence_category: str = Form(...),
    licence_expiry: str = Form(None),
    availability: str = Form("available"),
    shift_info: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    d = Driver(
        employee_id=employee_id, licence_number=licence_number, licence_category=licence_category,
        availability=availability, shift_info=shift_info, is_active=True,
    )
    if licence_expiry:
        from datetime import datetime
        d.licence_expiry = datetime.strptime(licence_expiry, "%Y-%m-%d").date()
    db.add(d)
    db.commit()
    audit_log(db, "create", "drivers", record_id=d.id, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Driver registered", "success")
    return RedirectResponse(url="/drivers/", status_code=303)


@router.get("/{d_id}/edit", response_class=HTMLResponse)
def edit_driver(d_id: int, request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    d = db.query(Driver).get(d_id)
    if not d:
        return RedirectResponse(url="/drivers/", status_code=303)
    employees = db.query(Employee).filter(Employee.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "drivers/form.html", {
        "request": request, "user": user, "page_title": "Edit driver",
        "driver": d, "employees": employees,
    })


@router.post("/{d_id}/update", response_class=HTMLResponse)
def update_driver(
    d_id: int, request: Request,
    licence_number: str = Form(...), licence_category: str = Form(...),
    licence_expiry: str = Form(None), availability: str = Form("available"),
    shift_info: str = Form(None), is_active: str = Form("true"),
    user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE),
):
    d = db.query(Driver).get(d_id)
    if not d:
        return RedirectResponse(url="/drivers/", status_code=303)
    d.licence_number = licence_number
    d.licence_category = licence_category
    d.availability = availability
    d.shift_info = shift_info
    d.is_active = (is_active == "true")
    if licence_expiry:
        from datetime import datetime
        d.licence_expiry = datetime.strptime(licence_expiry, "%Y-%m-%d").date()
    db.commit()
    audit_log(db, "update", "drivers", record_id=d.id, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Driver updated", "success")
    return RedirectResponse(url="/drivers/", status_code=303)


@router.post("/{d_id}/delete", response_class=HTMLResponse)
def delete_driver(d_id: int, request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    d = db.query(Driver).get(d_id)
    if d:
        d.is_active = False
        db.commit()
        audit_log(db, "deactivate", "drivers", record_id=d.id, user=user,
                  ip_address=request.client.host if request.client else None)
        _flash(request, "Driver deactivated", "success")
    return RedirectResponse(url="/drivers/", status_code=303)
