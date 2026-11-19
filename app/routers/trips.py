"""Trips and electronic logbook."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import Trip, Vehicle, Driver, TransportRequest, LogbookCorrection

router = APIRouter()
READ = PermissionChecker(["trip:read"])
WRITE = PermissionChecker(["trip:create", "trip:update"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_trips(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    trips = db.query(Trip).options(joinedload(Trip.vehicle), joinedload(Trip.driver)).order_by(Trip.created_at.desc()).all()
    return templates.TemplateResponse(request, "trips/list.html", {
        "request": request, "user": user, "page_title": "Trips / logbook", "trips": trips,
    })


@router.get("/new", response_class=HTMLResponse)
def new_trip(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa
    requests = db.query(TransportRequest).filter(TransportRequest.status.in_(["vehicle_assigned","driver_assigned","confirmed"])).all()
    return templates.TemplateResponse(request, "trips/form.html", {
        "request": request, "user": user, "page_title": "Start journey",
        "vehicles": vehicles, "drivers": drivers, "requests": requests, "trip": None,
    })


@router.post("/create", response_class=HTMLResponse)
def create_trip(
    request: Request,
    reference: str = Form(None),
    request_id: int = Form(None),
    vehicle_id: int = Form(...),
    driver_id: int = Form(...),
    purpose: str = Form(...),
    start_point: str = Form(...),
    destination: str = Form(...),
    departure_datetime: str = Form(None),
    start_odometer: int = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    trip = Trip(
        reference=reference or f"TRIP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        request_id=request_id, vehicle_id=vehicle_id, driver_id=driver_id,
        purpose=purpose, start_point=start_point, destination=destination,
        status="draft",
    )
    if departure_datetime:
        trip.departure_datetime = datetime.strptime(departure_datetime, "%Y-%m-%dT%H:%M")
    if start_odometer is not None:
        trip.start_odometer = start_odometer
    if departure_datetime or start_odometer is not None:
        trip.status = "in_progress"
    db.add(trip)
    db.flush()
    audit_log(db, "create", "trips", record_id=trip.id, user=user,
              ip_address=request.client.host if request.client else None)
    db.commit()
    _flash(request, "Journey started", "success")
    return RedirectResponse(url=f"/trips/{trip.id}/edit", status_code=303)


@router.get("/{trip_id}/edit", response_class=HTMLResponse)
def edit_trip(trip_id: int, request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(WRITE)):
    trip = db.query(Trip).options(joinedload(Trip.vehicle), joinedload(Trip.driver)).get(trip_id)
    if not trip:
        return RedirectResponse(url="/trips/", status_code=303)
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "trips/form.html", {
        "request": request, "user": user, "page_title": "Edit journey",
        "trip": trip, "vehicles": vehicles, "drivers": drivers,
    })


@router.post("/{trip_id}/update", response_class=HTMLResponse)
def update_trip(
    trip_id: int, request: Request,
    arrival_datetime: str = Form(None),
    end_odometer: int = Form(None),
    fuel_issued: float = Form(None),
    fuel_consumed: float = Form(None),
    passenger_count: int = Form(0),
    remarks: str = Form(None),
    status: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    trip = db.query(Trip).get(trip_id)
    if not trip:
        return RedirectResponse(url="/trips/", status_code=303)
    # log corrections for odometer changes
    if end_odometer is not None and end_odometer != trip.end_odometer:
        db.add(LogbookCorrection(trip_id=trip.id, field_name="end_odometer",
                                 old_value=str(trip.end_odometer), new_value=str(end_odometer),
                                 corrected_by=user.id, reason="Driver update"))
    if arrival_datetime:
        trip.arrival_datetime = datetime.strptime(arrival_datetime, "%Y-%m-%dT%H:%M")
    trip.end_odometer = end_odometer
    if fuel_issued is not None: trip.fuel_issued = fuel_issued
    if fuel_consumed is not None: trip.fuel_consumed = fuel_consumed
    trip.passenger_count = passenger_count
    trip.remarks = remarks
    if status: trip.status = status
    # auto distance
    if trip.start_odometer is not None and trip.end_odometer is not None:
        trip.total_distance = trip.end_odometer - trip.start_odometer
    if trip.status == "completed" or (arrival_datetime and end_odometer is not None):
        trip.status = "completed"
    db.commit()
    audit_log(db, "update", "trips", record_id=trip.id, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Journey updated", "success")
    return RedirectResponse(url=f"/trips/{trip_id}/edit", status_code=303)
