"""Employee management."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app.auth import get_current_user, PermissionChecker
from app.models import Employee, Directorate, Department, Section, User
from app.auth import audit_log

router = APIRouter()

TO_ADMIN = PermissionChecker(["user:read", "user:create", "user:update", "user:delete"])


def _flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


@router.get("/", response_class=HTMLResponse)
def list_employees(
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(TO_ADMIN),
):
    employees = db.query(Employee).order_by(Employee.created_at.desc()).all()
    return templates.TemplateResponse(request, "employees/list.html", {
        "request": request, "user": user, "page_title": "Employees",
        "employees": employees,
    })


@router.get("/new", response_class=HTMLResponse)
def new_employee(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db),
    _=Depends(TO_ADMIN),
):
    directorates = db.query(Directorate).filter(Directorate.is_active == True).all()  # noqa
    return templates.TemplateResponse(request, "employees/form.html", {
        "request": request, "user": user, "page_title": "Add employee",
        "directorates": directorates, "employee": None,
    })


@router.post("/create", response_class=HTMLResponse)
def create_employee(
    request: Request,
    employee_number: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    directorate_id: int = Form(None),
    department_id: int = Form(None),
    section_id: int = Form(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(TO_ADMIN),
):
    emp = Employee(
        employee_number=employee_number, first_name=first_name, last_name=last_name,
        email=email, phone=phone, directorate_id=directorate_id,
        department_id=department_id, section_id=section_id, is_active=True,
    )
    db.add(emp)
    db.commit()
    audit_log(db, "create", "employees", record_id=emp.id, new_value=emp.full_name, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Employee created", "success")
    return RedirectResponse(url="/employees/", status_code=303)


@router.get("/{emp_id}/edit", response_class=HTMLResponse)
def edit_employee(
    emp_id: int, request: Request, user=Depends(get_current_user),
    db: Session = Depends(get_db), _=Depends(TO_ADMIN),
):
    emp = db.query(Employee).get(emp_id)
    if not emp:
        return RedirectResponse(url="/employees/", status_code=303)
    directorates = db.query(Directorate).filter(Directorate.is_active == True).all()  # noqa
    departments = db.query(Department).filter(Department.directorate_id == emp.directorate_id).all() if emp.directorate_id else []
    sections = db.query(Section).filter(Section.department_id == emp.department_id).all() if emp.department_id else []
    return templates.TemplateResponse(request, "employees/form.html", {
        "request": request, "user": user, "page_title": "Edit employee",
        "employee": emp, "directorates": directorates,
        "departments": departments, "sections": sections,
    })


@router.post("/{emp_id}/update", response_class=HTMLResponse)
def update_employee(
    emp_id: int,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    directorate_id: int = Form(None),
    department_id: int = Form(None),
    section_id: int = Form(None),
    is_active: str = Form("true"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(TO_ADMIN),
):
    emp = db.query(Employee).get(emp_id)
    if not emp:
        return RedirectResponse(url="/employees/", status_code=303)
    emp.first_name = first_name
    emp.last_name = last_name
    emp.email = email
    emp.phone = phone
    emp.directorate_id = directorate_id
    emp.department_id = department_id
    emp.section_id = section_id
    emp.is_active = (is_active == "true")
    db.commit()
    audit_log(db, "update", "employees", record_id=emp.id, user=user,
              ip_address=request.client.host if request.client else None)
    _flash(request, "Employee updated", "success")
    return RedirectResponse(url="/employees/", status_code=303)


@router.post("/{emp_id}/delete", response_class=HTMLResponse)
def delete_employee(
    emp_id: int, request: Request, user=Depends(get_current_user),
    db: Session = Depends(get_db), _=Depends(TO_ADMIN),
):
    emp = db.query(Employee).get(emp_id)
    if emp:
        emp.is_active = False
        db.commit()
        audit_log(db, "deactivate", "employees", record_id=emp.id, user=user,
                  ip_address=request.client.host if request.client else None)
        _flash(request, "Employee deactivated", "success")
    return RedirectResponse(url="/employees/", status_code=303)
