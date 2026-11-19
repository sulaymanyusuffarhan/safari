"""Transport requests module - core workflow."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker, audit_log
from app.models import (
    TransportRequest, TransportRequestCategory, Employee, Directorate, Department,
    Section, MediaOutlet, ZoneOffice, Role, User,
)
from app.config import settings

router = APIRouter()

CREATE = PermissionChecker(["request:create"])
READ = PermissionChecker(["request:read"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


def _gen_reference(db: Session) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"TBC-{today}-"
    last = db.query(TransportRequest).filter(
        TransportRequest.reference_number.like(prefix + "%")
    ).order_by(TransportRequest.id.desc()).first()
    seq = 1
    if last and last.reference_number:
        try:
            seq = int(last.reference_number.split("-")[-1]) + 1
        except Exception:
            seq = 1
    return f"{prefix}{seq:04d}"


def _notify(db, user_id, title, message, link_url):
    from app.models import Notification
    db.add(Notification(user_id=user_id, title=title, message=message,
                        type="request", link_url=link_url))


# ---------------------------------------------------------------------------
# New request form (employee)
# ---------------------------------------------------------------------------
@router.get("/new", response_class=HTMLResponse)
def new_request(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db),
    _=Depends(CREATE),
):
    if not user.employee_id:
        return RedirectResponse(url="/dashboard", status_code=303)
    emp = db.query(Employee).get(user.employee_id)
    categories = db.query(TransportRequestCategory).filter(TransportRequestCategory.is_active == True).all()
    media = db.query(MediaOutlet).filter(MediaOutlet.is_active == True).all()
    zones = db.query(ZoneOffice).filter(ZoneOffice.is_active == True).all()
    directorates = db.query(Directorate).filter(Directorate.is_active == True).all()
    departments = db.query(Department).filter(Department.is_active == True).all()
    sections = db.query(Section).filter(Section.is_active == True).all()
    return templates.TemplateResponse(request, "requests/form.html", {
        "request": request, "user": user, "page_title": "Request transport",
        "employee": emp, "categories": categories, "media": media, "zones": zones,
        "directorates": directorates, "departments": departments, "sections": sections,
    })

# ---------------------------------------------------------------------------
# Create request
# ---------------------------------------------------------------------------
@router.post("/create", response_class=HTMLResponse)
def create_request(
    request: Request,
    directorate_id: int = Form(None),
    department_id: int = Form(None),
    section_id: int = Form(None),
    contact_phone: str = Form(None),
    category_id: int = Form(None),
    media_outlet_id: int = Form(None),
    zone_office_id: int = Form(None),
    purpose: str = Form(...),
    departure_location: str = Form(...),
    destination: str = Form(...),
    travel_date: str = Form(...),
    departure_time: str = Form(None),
    expected_return_date: str = Form(None),
    expected_return_time: str = Form(None),
    number_of_passengers: int = Form(1),
    equipment_luggage: str = Form(None),
    special_requirements: str = Form(None),
    remarks: str = Form(None),
    assignment_title: str = Form(None),
    coverage_subject: str = Form(None),
    assignment_description: str = Form(None),
    coverage_type: str = Form(None),
    journalist_details: str = Form(None),
    camera_operators: str = Form(None),
    photographers: str = Form(None),
    crew_count: int = Form(None),
    coverage_duration: str = Form(None),
    urgency_level: str = Form(None),
    assignment_editor: str = Form(None),
    multiple_destinations: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(CREATE),
):
    if not user.employee_id:
        return RedirectResponse(url="/dashboard", status_code=303)

    ref = _gen_reference(db)
    t_date = datetime.strptime(travel_date, "%Y-%m-%d").date() if travel_date else None
    d_time = datetime.strptime(departure_time, "%H:%M").time() if departure_time else None
    er_date = datetime.strptime(expected_return_date, "%Y-%m-%d").date() if expected_return_date else None
    er_time = datetime.strptime(expected_return_time, "%H:%M").time() if expected_return_time else None

    cat = db.query(TransportRequestCategory).get(category_id) if category_id else None
    status = "submitted"
    if cat and cat.requires_department_approval:
        status = "pending_departmental_approval"

    tr = TransportRequest(
        reference_number=ref, employee_id=user.employee_id,
        directorate_id=directorate_id, department_id=department_id, section_id=section_id,
        contact_phone=contact_phone, category_id=category_id, media_outlet_id=media_outlet_id,
        zone_office_id=zone_office_id, purpose=purpose, departure_location=departure_location,
        destination=destination, travel_date=t_date, departure_time=d_time,
        expected_return_date=er_date, expected_return_time=er_time,
        number_of_passengers=number_of_passengers, equipment_luggage=equipment_luggage,
        special_requirements=special_requirements, remarks=remarks, status=status,
        priority="emergency" if (cat and cat.code == "emergency") else "normal",
        assignment_title=assignment_title, coverage_subject=coverage_subject,
        assignment_description=assignment_description, coverage_type=coverage_type,
        journalist_details=journalist_details, camera_operators=camera_operators,
        photographers=photographers, crew_count=crew_count, coverage_duration=coverage_duration,
        urgency_level=urgency_level, assignment_editor=assignment_editor,
        multiple_destinations=multiple_destinations,
    )
    db.add(tr)
    db.flush()
    audit_log(db, "create", "transport_requests", record_id=tr.id, new_value=ref, user=user,
              ip_address=request.client.host if request.client else None)
    db.commit()

    tos = db.query(User).join(User.role).filter(Role.code == "transport_officer", User.is_active == True).all()
    for to in tos:
        _notify(db, to.id, "New transport request",
                f"Request {ref} submitted by {user.employee.full_name if user.employee else user.username}",
                f"/requests/{tr.id}")
    db.commit()

    _flash(request, f"Request {ref} submitted", "success")
    return RedirectResponse(url=f"/requests/{tr.id}", status_code=303)


# ---------------------------------------------------------------------------
# My requests (employee)
# ---------------------------------------------------------------------------
@router.get("/my", response_class=HTMLResponse)
def my_requests(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db),
    _=Depends(READ),
):
    if not user.employee_id:
        return RedirectResponse(url="/dashboard", status_code=303)
    reqs = db.query(TransportRequest).filter(
        TransportRequest.employee_id == user.employee_id
    ).order_by(TransportRequest.created_at.desc()).all()
    return templates.TemplateResponse(request, "requests/my.html", {
        "request": request, "user": user, "page_title": "My requests", "requests": reqs,
    })


# ---------------------------------------------------------------------------
# All requests (TO / supervisor / admin)
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def list_requests(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db),
    _=Depends(READ),
):
    reqs = db.query(TransportRequest).order_by(TransportRequest.created_at.desc()).all()
    return templates.TemplateResponse(request, "requests/list.html", {
        "request": request, "user": user, "page_title": "All requests", "requests": reqs,
    })


# ---------------------------------------------------------------------------
# Pending approvals (department head / supervisor)
# ---------------------------------------------------------------------------
@router.get("/pending-approval", response_class=HTMLResponse)
def pending_approval(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db),
    _=Depends(READ),
):
    reqs = db.query(TransportRequest).filter(
        TransportRequest.status.in_(["pending_departmental_approval", "pending_transport_review"])
    ).order_by(TransportRequest.created_at.desc()).all()
    return templates.TemplateResponse(request, "requests/pending.html", {
        "request": request, "user": user, "page_title": "Pending approvals", "requests": reqs,
    })


# ---------------------------------------------------------------------------
# View request details
# ---------------------------------------------------------------------------
@router.get("/{req_id}", response_class=HTMLResponse)
def view_request(
    req_id: int, request: Request, user=Depends(get_current_user),
    db: Session = Depends(get_db), _=Depends(READ),
):
    tr = db.query(TransportRequest).options(joinedload(TransportRequest.employee),
                                            joinedload(TransportRequest.category)).get(req_id)
    if not tr:
        return RedirectResponse(url="/requests/", status_code=303)
    if user.role and user.role.code == "employee" and tr.employee_id != user.employee_id:
        return RedirectResponse(url="/requests/my", status_code=303)
    from app.models import RequestApproval
    approvals = db.query(RequestApproval).filter(RequestApproval.request_id == req_id).all()
    return templates.TemplateResponse(request, "requests/view.html", {
        "request": request, "user": user, "page_title": f"Request {tr.reference_number}",
        "tr": tr, "approvals": approvals,
    })


# ---------------------------------------------------------------------------
# Approve / reject
# ---------------------------------------------------------------------------
@router.post("/{req_id}/approve", response_class=HTMLResponse)
def approve_request(
    req_id: int, request: Request,
    comments: str = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(PermissionChecker(["approval:action"])),
):
    tr = db.query(TransportRequest).get(req_id)
    if not tr:
        return RedirectResponse(url="/requests/", status_code=303)
    tr.approved_by = user.id
    tr.approved_at = datetime.utcnow()
    tr.status = "approved"
    from app.models import RequestApproval, Notification
    db.add(RequestApproval(request_id=req_id, approver_id=user.id, action="approve", comments=comments))
    db.commit()
    audit_log(db, "approve", "transport_requests", record_id=req_id, new_value="approved",
              reason=comments, user=user, ip_address=request.client.host if request.client else None)
    emp_user = tr.employee.user if tr.employee else None
    if emp_user:
        db.add(Notification(user_id=emp_user.id, title="Request approved",
                            message=f"Request {tr.reference_number} has been approved",
                            type="request", link_url=f"/requests/{req_id}"))
    db.commit()
    _flash(request, "Request approved", "success")
    return RedirectResponse(url=f"/requests/{req_id}", status_code=303)


@router.post("/{req_id}/reject", response_class=HTMLResponse)
def reject_request(
    req_id: int, request: Request,
    rejection_reason: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(PermissionChecker(["approval:action"])),
):
    tr = db.query(TransportRequest).get(req_id)
    if not tr:
        return RedirectResponse(url="/requests/", status_code=303)
    if not rejection_reason or not rejection_reason.strip():
        _flash(request, "A rejection reason is mandatory", "error")
        return RedirectResponse(url=f"/requests/{req_id}", status_code=303)
    tr.status = "rejected"
    tr.rejection_reason = rejection_reason.strip()
    tr.rejected_at = datetime.utcnow()
    from app.models import RequestApproval, Notification
    db.add(RequestApproval(request_id=req_id, approver_id=user.id, action="reject", comments=rejection_reason.strip()))
    db.commit()
    audit_log(db, "reject", "transport_requests", record_id=req_id, new_value="rejected",
              reason=rejection_reason.strip(), user=user, ip_address=request.client.host if request.client else None)
    emp_user = tr.employee.user if tr.employee else None
    if emp_user:
        db.add(Notification(user_id=emp_user.id, title="Request rejected",
                            message=f"Request {tr.reference_number} was rejected. Reason: {rejection_reason.strip()}",
                            type="request", link_url=f"/requests/{req_id}"))
    db.commit()
    _flash(request, "Request rejected", "warning")
    return RedirectResponse(url=f"/requests/{req_id}", status_code=303)
