"""Role-based dashboards."""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, require_user, audit_log
from app.models import (
    User, Vehicle, Driver, TransportRequest, Trip, FuelTransaction,
    MaintenanceRecord, BreakdownReport, AuditLog, Notification,
)

router = APIRouter()


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


# ---------------------------------------------------------------------------
# Role dispatcher
# ---------------------------------------------------------------------------
async def role_dashboard(request: Request, user: User):
    role = user.role.code if user.role else ""
    db = next(get_db())

    try:
        if role == "system_administrator":
            return _admin_dashboard(request, user, db)
        if role == "transport_officer":
            return _to_dashboard(request, user, db)
        if role == "transport_supervisor":
            return _supervisor_dashboard(request, user, db)
        if role == "driver":
            return _driver_dashboard(request, user, db)
        if role == "employee":
            return _employee_dashboard(request, user, db)
        if role == "department_head":
            return _department_head_dashboard(request, user, db)
        if role == "finance_accounts":
            return _finance_dashboard(request, user, db)
        if role == "internal_audit":
            return _audit_dashboard(request, user, db)
        if role == "management_director_general":
            return _management_dashboard(request, user, db)
        return _generic_dashboard(request, user, db)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Generic / fallback
# ---------------------------------------------------------------------------
def _generic_dashboard(request: Request, user: User, db: Session):
    total_requests = db.query(TransportRequest).count()
    my_requests = db.query(TransportRequest).filter(TransportRequest.employee_id == user.employee_id).count() if user.employee_id else 0
    return templates.TemplateResponse(request, "dashboard/generic.html", {
        "request": request, "user": user, "page_title": "Dashboard",
        "total_requests": total_requests, "my_requests": my_requests,
    })


# ---------------------------------------------------------------------------
# Transport Officer dashboard (the central fleet dashboard)
# ---------------------------------------------------------------------------
def _to_dashboard(request: Request, user: User, db: Session):
    total_vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).count()  # noqa: E712
    available = db.query(Vehicle).filter(Vehicle.status == "available", Vehicle.is_active == True).count()  # noqa
    in_use = db.query(Vehicle).filter(Vehicle.status == "in_use", Vehicle.is_active == True).count()  # noqa
    assigned = db.query(Vehicle).filter(Vehicle.status == "assigned", Vehicle.is_active == True).count()  # noqa
    maintenance = db.query(Vehicle).filter(Vehicle.status.like("%maintenance%"), Vehicle.is_active == True).count()  # noqa
    out_of_service = db.query(Vehicle).filter(Vehicle.status == "out_of_service", Vehicle.is_active == True).count()  # noqa

    pending_requests = db.query(TransportRequest).filter(
        TransportRequest.status.in_(["submitted", "pending_departmental_approval", "pending_transport_review"])
    ).count()
    approved_unassigned = db.query(TransportRequest).filter(
        TransportRequest.status == "approved"
    ).count()
    in_progress_trips = db.query(Trip).filter(Trip.status == "in_progress").count()

    total_drivers = db.query(Driver).filter(Driver.is_active == True).count()  # noqa
    available_drivers = db.query(Driver).filter(Driver.availability == "available", Driver.is_active == True).count()  # noqa

    # Recent activity
    recent_requests = db.query(TransportRequest).order_by(TransportRequest.created_at.desc()).limit(8).all()
    recent_breakdowns = db.query(BreakdownReport).filter(
        BreakdownReport.status != "resolved"
    ).order_by(BreakdownReport.breakdown_datetime.desc()).limit(5).all()

    # Vehicles needing attention (maintenance due soon / breakdowns)
    maintenance_due = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.status.in_(["reported", "approved"])
    ).order_by(MaintenanceRecord.date_reported.desc()).limit(5).all()

    audit_log(db, "view_dashboard", "dashboard", user=user, ip_address=request.client.host if request.client else None)

    return templates.TemplateResponse(request, "dashboard/transport_officer.html", {
        "request": request, "user": user, "page_title": "Transport Officer Dashboard",
        "total_vehicles": total_vehicles, "available": available, "in_use": in_use,
        "assigned": assigned, "maintenance": maintenance, "out_of_service": out_of_service,
        "pending_requests": pending_requests, "approved_unassigned": approved_unassigned,
        "in_progress_trips": in_progress_trips,
        "total_drivers": total_drivers, "available_drivers": available_drivers,
        "recent_requests": recent_requests, "recent_breakdowns": recent_breakdowns,
        "maintenance_due": maintenance_due,
    })


# ---------------------------------------------------------------------------
# Management / Director General dashboard
# ---------------------------------------------------------------------------
def _management_dashboard(request: Request, user: User, db: Session):
    total_vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).count()  # noqa
    available = db.query(Vehicle).filter(Vehicle.status == "available", Vehicle.is_active == True).count()  # noqa
    in_use = db.query(Vehicle).filter(Vehicle.status == "in_use", Vehicle.is_active == True).count()  # noqa
    maintenance = db.query(Vehicle).filter(Vehicle.status.like("%maintenance%"), Vehicle.is_active == True).count()  # noqa
    out_of_service = db.query(Vehicle).filter(Vehicle.status == "out_of_service", Vehicle.is_active == True).count()  # noqa

    total_requests = db.query(TransportRequest).count()
    pending = db.query(TransportRequest).filter(TransportRequest.status == "pending_transport_review").count()
    rejected = db.query(TransportRequest).filter(TransportRequest.status == "rejected").count()
    completed = db.query(TransportRequest).filter(TransportRequest.status == "completed").count()

    total_fuel = db.query(func.coalesce(FuelTransaction.total_amount, 0)).scalar() or 0
    total_maintenance_cost = db.query(func.coalesce(MaintenanceRecord.actual_cost, 0)).scalar() or 0

    audit_log(db, "view_dashboard", "dashboard", user=user, ip_address=request.client.host if request.client else None)

    return templates.TemplateResponse(request, "dashboard/management.html", {
        "request": request, "user": user, "page_title": "Management Dashboard",
        "total_vehicles": total_vehicles, "available": available, "in_use": in_use,
        "maintenance": maintenance, "out_of_service": out_of_service,
        "total_requests": total_requests, "pending": pending, "rejected": rejected, "completed": completed,
        "total_fuel": total_fuel, "total_maintenance_cost": total_maintenance_cost,
    })


# ---------------------------------------------------------------------------
# Employee dashboard
# ---------------------------------------------------------------------------
def _employee_dashboard(request: Request, user: User, db: Session):
    if not user.employee_id:
        _flash(request, "No employee record linked to your account.", "warning")
        return RedirectResponse(url="/dashboard", status_code=303)
    my_requests = db.query(TransportRequest).filter(
        TransportRequest.employee_id == user.employee_id
    ).order_by(TransportRequest.created_at.desc()).limit(10).all()
    return templates.TemplateResponse(request, "dashboard/employee.html", {
        "request": request, "user": user, "page_title": "My Dashboard",
        "my_requests": my_requests,
    })


# ---------------------------------------------------------------------------
# Driver dashboard
# ---------------------------------------------------------------------------
def _driver_dashboard(request: Request, user: User, db: Session):
    if not user.employee_id:
        _flash(request, "No employee record linked to your account.", "warning")
        return RedirectResponse(url="/dashboard", status_code=303)
    driver = db.query(Driver).filter(Driver.employee_id == user.employee_id).first()
    my_trips = []
    if driver:
        my_trips = db.query(Trip).filter(Trip.driver_id == driver.id).order_by(Trip.created_at.desc()).limit(10).all()
    return templates.TemplateResponse(request, "dashboard/driver.html", {
        "request": request, "user": user, "page_title": "Driver Dashboard",
        "driver": driver, "my_trips": my_trips,
    })


# ---------------------------------------------------------------------------
# Department head dashboard
# ---------------------------------------------------------------------------
def _department_head_dashboard(request: Request, user: User, db: Session):
    if not user.employee_id:
        _flash(request, "No employee record linked to your account.", "warning")
        return RedirectResponse(url="/dashboard", status_code=303)
    dept_requests = db.query(TransportRequest).filter(
        TransportRequest.department_id == user.employee.department_id
    ).order_by(TransportRequest.created_at.desc()).limit(10).all() if user.employee and user.employee.department_id else []
    return templates.TemplateResponse(request, "dashboard/department_head.html", {
        "request": request, "user": user, "page_title": "Department Dashboard",
        "dept_requests": dept_requests,
    })


# ---------------------------------------------------------------------------
# Finance dashboard
# ---------------------------------------------------------------------------
def _finance_dashboard(request: Request, user: User, db: Session):
    total_fuel = db.query(func.coalesce(FuelTransaction.total_amount, 0)).scalar() or 0
    total_maintenance = db.query(func.coalesce(MaintenanceRecord.actual_cost, 0)).scalar() or 0
    fuel_count = db.query(FuelTransaction).count()
    maint_count = db.query(MaintenanceRecord).count()
    return templates.TemplateResponse(request, "dashboard/finance.html", {
        "request": request, "user": user, "page_title": "Finance Dashboard",
        "total_fuel": total_fuel, "total_maintenance": total_maintenance,
        "fuel_count": fuel_count, "maint_count": maint_count,
    })


# ---------------------------------------------------------------------------
# Internal audit dashboard
# ---------------------------------------------------------------------------
def _audit_dashboard(request: Request, user: User, db: Session):
    recent_audit = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(20).all()
    return templates.TemplateResponse(request, "dashboard/audit.html", {
        "request": request, "user": user, "page_title": "Audit Dashboard",
        "recent_audit": recent_audit,
    })


# ---------------------------------------------------------------------------
# System administrator dashboard
# ---------------------------------------------------------------------------
def _admin_dashboard(request: Request, user: User, db: Session):
    total_users = db.query(User).count()
    total_vehicles = db.query(Vehicle).count()
    total_requests = db.query(TransportRequest).count()
    recent_audit = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
    return templates.TemplateResponse(request, "dashboard/admin.html", {
        "request": request, "user": user, "page_title": "System Administration",
        "total_users": total_users, "total_vehicles": total_vehicles,
        "total_requests": total_requests, "recent_audit": recent_audit,
    })


# ---------------------------------------------------------------------------
# Supervisor dashboard
# ---------------------------------------------------------------------------
def _supervisor_dashboard(request: Request, user: User, db: Session):
    pending = db.query(TransportRequest).filter(
        TransportRequest.status == "pending_transport_review"
    ).count()
    return templates.TemplateResponse(request, "dashboard/supervisor.html", {
        "request": request, "user": user, "page_title": "Transport Supervisor",
        "pending": pending,
    })
