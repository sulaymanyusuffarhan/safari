"""Vehicle & driver allocation with conflict prevention."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import (
    VehicleAssignment, TransportRequest, Vehicle, Driver, User,
    RequestApproval, VehicleStatusHistory,
)

router = APIRouter()
WRITE = PermissionChecker(["allocation:create", "allocation:update"])
READ = PermissionChecker(["allocation:read"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


def _check_conflicts(db, vehicle_id, driver_id, start_dt, end_dt, exclude_assignment_id=None):
    """Return (ok, reason). Prevents double-booking vehicles and drivers."""
    q = db.query(VehicleAssignment).filter(VehicleAssignment.status == "active")
    if exclude_assignment_id:
        q = q.filter(VehicleAssignment.id != exclude_assignment_id)
    # vehicle double booking
    if vehicle_id:
        va = q.filter(VehicleAssignment.vehicle_id == vehicle_id).all()
        for a in va:
            s = a.start_datetime or datetime.min
            e = a.end_datetime or datetime.max
            if start_dt < e and end_dt > s:
                return False, f"Vehicle already assigned {s} to {e}"
    # driver double booking
    if driver_id:
        da = q.filter(VehicleAssignment.driver_id == driver_id).all()
        for a in da:
            s = a.start_datetime or datetime.min
            e = a.end_datetime or datetime.max
            if start_dt < e and end_dt > s:
                return False, f"Driver already assigned {s} to {e}"
    return True, ""


# ---------------------------------------------------------------------------
# List: requests ready for allocation (approved, not yet assigned)
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def list_allocations(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    requests = db.query(TransportRequest).options(
        joinedload(TransportRequest.employee),
        joinedload(TransportRequest.category),
    ).filter(TransportRequest.status == "approved").order_by(TransportRequest.created_at.desc()).all()
    vehicles = db.query(Vehicle).filter(Vehicle.status == "available", Vehicle.is_active == True).all()  # noqa
    drivers = db.query(Driver).filter(Driver.availability == "available", Driver.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "allocations/list.html", {
        "request": request, "user": user, "page_title": "Vehicle allocation",
        "requests": requests, "vehicles": vehicles, "drivers": drivers,
    })


# ---------------------------------------------------------------------------
# Allocate vehicle + driver to a request
# ---------------------------------------------------------------------------
@router.post("/allocate", response_class=HTMLResponse)
def allocate(
    request: Request,
    request_id: int = Form(...),
    vehicle_id: int = Form(...),
    driver_id: int = Form(None),
    start_datetime: str = Form(None),
    end_datetime: str = Form(None),
    reason: str = Form("Allocated by Transport Officer"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    tr = db.query(TransportRequest).get(request_id)
    if not tr:
        _flash(request, "Request not found", "error")
        return RedirectResponse(url="/allocations/", status_code=303)
    v = db.query(Vehicle).get(vehicle_id)
    if not v:
        _flash(request, "Vehicle not found", "error")
        return RedirectResponse(url="/allocations/", status_code=303)

    # Capacity check
    if tr.number_of_passengers > v.passenger_capacity:
        _flash(request, f"Vehicle capacity ({v.passenger_capacity}) is less than passengers ({tr.number_of_passengers})", "error")
        return RedirectResponse(url="/allocations/", status_code=303)

    # Vehicle status check
    if v.status not in ("available", "assigned"):
        _flash(request, f"Vehicle is {v.status} and cannot be allocated", "error")
        return RedirectResponse(url="/allocations/", status_code=303)

    s_dt = datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M") if start_datetime else datetime.utcnow()
    e_dt = datetime.strptime(end_datetime, "%Y-%m-%dT%H:%M") if end_datetime else None

    d = None
    if driver_id:
        d = db.query(Driver).get(driver_id)
        if not d or d.availability != "available":
            _flash(request, "Selected driver is not available", "error")
            return RedirectResponse(url="/allocations/", status_code=303)

    ok, reason_conflict = _check_conflicts(db, vehicle_id, driver_id if d else None, s_dt, e_dt)
    if not ok:
        _flash(request, f"Allocation blocked: {reason_conflict}", "error")
        return RedirectResponse(url="/allocations/", status_code=303)

    # Create assignment
    asg = VehicleAssignment(
        request_id=tr.id, vehicle_id=vehicle_id, driver_id=d.id if d else None,
        assigned_by=user.id, start_datetime=s_dt, end_datetime=e_dt,
        status="active", reason=reason,
    )
    db.add(asg)
    db.flush()

    # Update vehicle status
    v.status = "assigned"
    v.assigned_driver_id = d.id if d else None
    db.add(VehicleStatusHistory(vehicle_id=v.id, previous_status=v.status if v.status != "assigned" else "available",
                                new_status="assigned", changed_by=user.id, reason="Allocated to request " + tr.reference_number))

    # Update request status
    tr.status = "driver_assigned" if d else "vehicle_assigned"
    db.commit()

    audit_log(db, "allocate", "vehicle_assignments", record_id=asg.id, user=user,
              ip_address=request.client.host if request.client else None)

    # Notify employee & driver
    from app.models import Notification
    emp_user = tr.employee.user if tr.employee else None
    if emp_user:
        db.add(Notification(user_id=emp_user.id, title="Vehicle allocated",
                            message=f"Request {tr.reference_number}: vehicle {v.registration_number} assigned",
                            type="allocation", link_url=f"/requests/{tr.id}"))
    if d and d.employee and d.employee.user:
        db.add(Notification(user_id=d.employee.user.id, title="New assignment",
                            message=f"You are assigned to drive {v.registration_number} for request {tr.reference_number}",
                            type="allocation", link_url=f"/requests/{tr.id}"))
    db.commit()

    _flash(request, f"Allocated {v.registration_number} to request {tr.reference_number}", "success")
    return RedirectResponse(url="/allocations/", status_code=303)


# ---------------------------------------------------------------------------
# Complete an assignment (return vehicle)
# ---------------------------------------------------------------------------
@router.post("/{asg_id}/complete", response_class=HTMLResponse)
def complete_assignment(
    asg_id: int, request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(WRITE),
):
    asg = db.query(VehicleAssignment).get(asg_id)
    if not asg:
        _flash(request, "Assignment not found", "error")
        return RedirectResponse(url="/allocations/", status_code=303)
    asg.status = "completed"
    asg.end_datetime = datetime.utcnow()
    v = db.query(Vehicle).get(asg.vehicle_id)
    if v:
        v.status = "available"
        db.add(VehicleStatusHistory(vehicle_id=v.id, previous_status="assigned", new_status="available",
                                    changed_by=user.id, reason="Assignment completed"))
    db.commit()
    audit_log(db, "complete", "vehicle_assignments", record_id=asg.id, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Assignment completed; vehicle returned to available", "success")
    return RedirectResponse(url="/allocations/", status_code=303)
