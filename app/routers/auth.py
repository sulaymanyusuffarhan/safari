"""Authentication routes: login, logout, first-setup."""

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.templating import templates
from app.auth import (
    authenticate_user, create_access_token, get_user_by_username,
    get_user_by_id, get_user_permission_codes, audit_log, pwd_context,
)
from app.models import (
    User, Role, Permission, RolePermission, Employee, Directorate,
)
from app.config import settings

router = APIRouter()


def flash(request: Request, message: str, category: str = "info"):
    flashes = request.session.get("_flash", [])
    flashes.append({"text": message, "category": category})
    request.session["_flash"] = flashes


def _setup_complete(db: Session) -> bool:
    return db.query(User).first() is not None


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, db: Session = Depends(get_db)):
    if not _setup_complete(db):
        return RedirectResponse(url="/auth/setup", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {"request": request, "page_title": "Sign in"})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if not _setup_complete(db):
        return RedirectResponse(url="/auth/setup", status_code=303)

    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "page_title": "Sign in", "error": "Invalid username or password"},
        )

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["language"] = user.language or settings.DEFAULT_LANGUAGE
    request.session["_perms"] = list(get_user_permission_codes(db, user))
    request.session["_role"] = user.role.code if user.role else ""
    request.session["access_token"] = create_access_token({"sub": str(user.id), "username": user.username})

    audit_log(
        db, "login", "users", record_id=user.id,
        user=user, ip_address=request.client.host if request.client else None,
    )

    display = user.employee.full_name if user.employee else user.username
    flash(request, f"Welcome back, {display}", "success")
    return RedirectResponse(url="/dashboard", status_code=303)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@router.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        user = get_user_by_id(db, int(user_id))
        if user:
            audit_log(
                db, "logout", "users", record_id=user.id,
                user=user, ip_address=request.client.host if request.client else None,
            )
    request.session.clear()
    flash(request, "You have signed out", "info")
    return RedirectResponse(url="/auth/login", status_code=303)


# ---------------------------------------------------------------------------
# First-time setup
# ---------------------------------------------------------------------------
@router.get("/setup", response_class=HTMLResponse)
async def setup_form(request: Request, db: Session = Depends(get_db)):
    if _setup_complete(db):
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(request, "auth/setup.html", {"request": request, "page_title": "System setup"})


@router.post("/setup", response_class=HTMLResponse)
async def setup_create(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form("System Administrator"),
    db: Session = Depends(get_db),
):
    if _setup_complete(db):
        return RedirectResponse(url="/auth/login", status_code=303)

    if get_user_by_username(db, username):
        return templates.TemplateResponse(
            "auth/setup.html",
            {"request": request, "page_title": "System setup", "error": "Username already exists"},
        )

    # Core organisational record (get-or-create; seed may already exist)
    dg = db.query(Directorate).filter_by(code="DG").first()
    if not dg:
        dg = Directorate(name="Director General's Office", code="DG", description="Director General office")
        db.add(dg)
        db.flush()
    emp = db.query(Employee).filter_by(employee_number="ADM-0001").first()
    if not emp:
        parts = full_name.split(" ")
        emp = Employee(
            employee_number="ADM-0001",
            first_name=parts[0] if parts else "System",
            last_name=parts[-1] if len(parts) > 1 else "Administrator",
            email=email,
            directorate_id=dg.id,
            is_active=True,
        )
        db.add(emp)
        db.flush()

    # Roles
    roles = {
        "system_administrator": "System Administrator",
        "transport_officer": "Transport Officer",
        "transport_supervisor": "Transport Supervisor",
        "driver": "Driver",
        "employee": "Employee",
        "department_head": "Department Head",
        "finance_accounts": "Finance & Accounts",
        "internal_audit": "Internal Audit",
        "management_director_general": "Management / Director General",
    }
    role_objs = {}
    for code, name in roles.items():
        r = Role(code=code, name=name, description=f"{name} role")
        db.add(r)
        db.flush()
        role_objs[code] = r

    # Permissions
    perms_data = [
        ("user:create", "Create users", "users", "create"),
        ("user:read", "Read users", "users", "read"),
        ("user:update", "Update users", "users", "update"),
        ("user:delete", "Delete users", "users", "delete"),
        ("role:manage", "Manage roles", "roles", "manage"),
        ("permission:manage", "Manage permissions", "permissions", "manage"),
        ("org:manage", "Manage organisational structure", "org", "manage"),
        ("vehicle:create", "Create vehicles", "vehicles", "create"),
        ("vehicle:read", "Read vehicles", "vehicles", "read"),
        ("vehicle:update", "Update vehicles", "vehicles", "update"),
        ("vehicle:delete", "Delete vehicles", "vehicles", "delete"),
        ("vehicle:status:change", "Change vehicle status", "vehicles", "status_change"),
        ("driver:create", "Create drivers", "drivers", "create"),
        ("driver:read", "Read drivers", "drivers", "read"),
        ("driver:update", "Update drivers", "drivers", "update"),
        ("request:create", "Create transport requests", "requests", "create"),
        ("request:read", "Read transport requests", "requests", "read"),
        ("request:update", "Update transport requests", "requests", "update"),
        ("request:delete", "Delete transport requests", "requests", "delete"),
        ("approval:read", "Read approvals", "approvals", "read"),
        ("approval:action", "Approve/reject requests", "approvals", "action"),
        ("allocation:create", "Create allocations", "allocations", "create"),
        ("allocation:read", "Read allocations", "allocations", "read"),
        ("allocation:update", "Update allocations", "allocations", "update"),
        ("trip:create", "Create trips", "trips", "create"),
        ("trip:read", "Read trips", "trips", "read"),
        ("trip:update", "Update trips", "trips", "update"),
        ("logbook:read", "Read logbooks", "logbooks", "read"),
        ("logbook:verify", "Verify logbooks", "logbooks", "verify"),
        ("fuel:create", "Create fuel transactions", "fuel", "create"),
        ("fuel:read", "Read fuel transactions", "fuel", "read"),
        ("fuel:update", "Update fuel transactions", "fuel", "update"),
        ("maintenance:create", "Create maintenance records", "maintenance", "create"),
        ("maintenance:read", "Read maintenance records", "maintenance", "read"),
        ("maintenance:update", "Update maintenance records", "maintenance", "update"),
        ("maintenance:approve", "Approve maintenance", "maintenance", "approve"),
        ("inspection:create", "Create inspections", "inspections", "create"),
        ("inspection:read", "Read inspections", "inspections", "read"),
        ("breakdown:create", "Create breakdown reports", "breakdowns", "create"),
        ("breakdown:read", "Read breakdown reports", "breakdowns", "read"),
        ("notification:read", "Read notifications", "notifications", "read"),
        ("report:read", "Read reports", "reports", "read"),
        ("report:export", "Export reports", "reports", "export"),
        ("audit:read", "Read audit logs", "audit", "read"),
        ("admin:read", "Read admin panel", "admin", "read"),
        ("admin:manage", "Manage admin panel", "admin", "manage"),
        ("setting:manage", "Manage system settings", "settings", "manage"),
        ("backup:manage", "Manage backup/recovery", "backup", "manage"),
    ]
    perm_objs = {}
    for code, name, module, action in perms_data:
        p = Permission(code=code, name=name, module=module, action=action, description=name)
        db.add(p)
        db.flush()
        perm_objs[code] = p

    grants = {
        "system_administrator": [p[0] for p in perms_data],
        "transport_officer": [
            "vehicle:read", "vehicle:status:change", "driver:read",
            "request:read", "request:update", "approval:read",
            "allocation:create", "allocation:read", "allocation:update",
            "trip:create", "trip:read", "trip:update",
            "logbook:read", "logbook:verify",
            "fuel:create", "fuel:read", "fuel:update",
            "maintenance:create", "maintenance:read", "maintenance:update", "maintenance:approve",
            "inspection:read", "breakdown:create", "breakdown:read",
            "notification:read", "report:read",
        ],
        "transport_supervisor": [
            "vehicle:read", "driver:read", "request:read", "approval:read",
            "approval:action", "allocation:read", "trip:read",
            "fuel:read", "maintenance:read", "maintenance:approve",
            "report:read", "notification:read",
        ],
        "driver": [
            "trip:read", "trip:update", "inspection:create", "breakdown:create",
            "notification:read",
        ],
        "employee": [
            "request:create", "request:read",
        ],
        "department_head": [
            "request:read", "approval:read", "approval:action", "report:read",
        ],
        "finance_accounts": [
            "fuel:read", "maintenance:read", "report:read", "report:export",
        ],
        "internal_audit": [
            "audit:read", "report:read", "report:export", "fuel:read",
            "maintenance:read", "trip:read", "request:read",
        ],
        "management_director_general": [
            "vehicle:read", "driver:read", "request:read", "allocation:read",
            "trip:read", "fuel:read", "maintenance:read", "report:read",
            "audit:read", "notification:read",
        ],
    }
    for role_code, codes in grants.items():
        r = role_objs[role_code]
        for code in codes:
            db.add(RolePermission(role_id=r.id, permission_id=perm_objs[code].id))

    admin_role = role_objs["system_administrator"]
    user = User(
        employee_id=emp.id,
        username=username,
        email=email,
        password_hash=pwd_context.hash(password),
        role_id=admin_role.id,
        language="sw",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()

    flash(request, "Setup complete. Please sign in.", "success")
    return RedirectResponse(url="/auth/login", status_code=303)
