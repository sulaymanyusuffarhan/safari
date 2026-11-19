"""Fuel management."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import FuelTransaction, Vehicle, Driver, FuelType, User

router = APIRouter()
WRITE = PermissionChecker(["fuel:create", "fuel:update"])
READ = PermissionChecker(["fuel:read"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_fuel(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    txns = db.query(FuelTransaction).options(joinedload(FuelTransaction.vehicle), joinedload(FuelTransaction.driver)).order_by(FuelTransaction.transaction_date.desc()).all()
    return templates.TemplateResponse(request, "fuel/list.html", {"request": request, "user": user, "page_title": "Fuel management", "txns": txns})


@router.get("/new", response_class=HTMLResponse)
def new_fuel(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa
    fuel_types = db.query(FuelType).filter(FuelType.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "fuel/form.html", {"request": request, "user": user, "page_title": "Record fuel transaction", "vehicles": vehicles, "drivers": drivers, "fuel_types": fuel_types, "txn": None})


@router.post("/create", response_class=HTMLResponse)
def create_fuel(
    request: Request,
    vehicle_id: int = Form(...),
    driver_id: int = Form(None),
    fuel_type_id: int = Form(None),
    quantity: float = Form(...),
    unit_price: float = Form(None),
    transaction_date: str = Form(...),
    fuel_station_supplier: str = Form(None),
    odometer_reading: int = Form(None),
    issue_reference: str = Form(None),
    trip_id: int = Form(None),
    receipt_path: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    txn = FuelTransaction(
        reference=f"FUEL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        vehicle_id=vehicle_id, driver_id=driver_id, fuel_type_id=fuel_type_id,
        quantity=quantity, unit_price=unit_price,
        total_amount=(quantity * unit_price) if unit_price else None,
        transaction_date=datetime.strptime(transaction_date, "%Y-%m-%d").date(),
        fuel_station_supplier=fuel_station_supplier, odometer_reading=odometer_reading,
        issue_reference=issue_reference, issuing_officer_id=user.id, receipt_path=receipt_path, trip_id=trip_id,
    )
    db.add(txn)
    db.flush()
    audit_log(db, "create", "fuel_transactions", record_id=txn.id, user=user,
              ip_address=request.client.host if request.client else None)
    db.commit()
    _flash(request, "Fuel transaction recorded", "success")
    return RedirectResponse(url="/fuel/", status_code=303)
