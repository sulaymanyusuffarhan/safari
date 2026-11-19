"""Reports and analytics."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
import csv, io

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker
from app.models import TransportRequest, FuelTransaction, MaintenanceRecord, Vehicle, Driver

router = APIRouter()
READ = PermissionChecker(["report:read"])


@router.get("/", response_class=HTMLResponse)
def reports_home(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(READ)):
    total = db.query(TransportRequest).count()
    approved = db.query(TransportRequest).filter(TransportRequest.status == "approved").count()
    rejected = db.query(TransportRequest).filter(TransportRequest.status == "rejected").count()
    pending = db.query(TransportRequest).filter(TransportRequest.status == "pending_transport_review").count()
    vehicles = db.query(Vehicle).count()
    drivers = db.query(Driver).count()
    return templates.TemplateResponse(request, "reports/home.html", {"request": request, "user": user, "page_title": "Reports", "total": total, "approved": approved, "rejected": rejected, "pending": pending, "vehicles": vehicles, "drivers": drivers})


@router.get("/export/requests.csv")
def export_requests_csv(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db), _=Depends(PermissionChecker(["report:export"]))):
    rows = db.query(TransportRequest).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["reference", "employee", "department", "status", "purpose", "departure", "destination", "travel_date"])
    for r in rows:
        w.writerow([r.reference_number, r.employee.full_name if r.employee else "", r.department.name if r.department else "", r.status, r.purpose, r.departure_location, r.destination, str(r.travel_date)])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=transport_requests.csv"})
