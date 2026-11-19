"""TBC-FTMS FastAPI application entry point."""

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from app.config import settings
from app.database import engine, Base, get_db
from app.auth import get_current_user, require_user
from app.models import User
from app.seed import seed_if_empty

# Create tables on startup (dev). Production uses Alembic migrations.
Base.metadata.create_all(bind=engine)

# Seed reference data (and demo data if enabled)
from app.database import SessionLocal
_seed_db = SessionLocal()
try:
    seed_if_empty(_seed_db)
finally:
    _seed_db.close()

app = FastAPI(
    title=settings.APP_NAME,
    description="Tanzania Broadcasting Corporation Fleet and Transport Management System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.ALLOWED_HOSTS] if settings.ALLOWED_HOSTS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.templating import templates
BASE_DIR = Path(__file__).resolve().parent

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Jinja2 globals
templates.env.globals["settings"] = settings
templates.env.globals["app_name"] = settings.APP_NAME
templates.env.globals["institution"] = settings.INSTITUTION_NAME
templates.env.globals["motto"] = settings.INSTITUTION_MOTTO
templates.env.globals["short"] = settings.INSTITUTION_SHORT

from app.i18n import t, status_label, vehicle_status_label, role_label  # noqa: E402

templates.env.globals["t"] = t
templates.env.globals["status_label"] = status_label
templates.env.globals["vehicle_status_label"] = vehicle_status_label
templates.env.globals["role_label"] = role_label


def current_lang(request: Request) -> str:
    return request.session.get("language", settings.DEFAULT_LANGUAGE)


templates.env.globals["current_lang"] = current_lang


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.routers import auth as auth_router  # noqa: E402
from app.routers import dashboard as dashboard_router  # noqa: E402
from app.routers import employees as employees_router  # noqa: E402
from app.routers import directorates as directorates_router  # noqa: E402
from app.routers import vehicles as vehicles_router  # noqa: E402
from app.routers import drivers as drivers_router  # noqa: E402
from app.routers import requests as requests_router  # noqa: E402
from app.routers import allocations as allocations_router  # noqa: E402
from app.routers import trips as trips_router  # noqa: E402
from app.routers import logbooks as logbooks_router  # noqa: E402
from app.routers import fuel as fuel_router  # noqa: E402
from app.routers import maintenance as maintenance_router  # noqa: E402
from app.routers import inspections as inspections_router  # noqa: E402
from app.routers import breakdowns as breakdowns_router  # noqa: E402
from app.routers import notifications as notifications_router  # noqa: E402
from app.routers import reports as reports_router  # noqa: E402
from app.routers import audit as audit_router  # noqa: E402
from app.routers import admin as admin_router  # noqa: E402
from app.routers import api as api_router  # noqa: E402

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard_router.router, tags=["dashboard"])
app.include_router(employees_router.router, prefix="/employees", tags=["employees"])
app.include_router(directorates_router.router, prefix="/directorates", tags=["directorates"])
app.include_router(vehicles_router.router, prefix="/vehicles", tags=["vehicles"])
app.include_router(drivers_router.router, prefix="/drivers", tags=["drivers"])
app.include_router(requests_router.router, prefix="/requests", tags=["requests"])
app.include_router(allocations_router.router, prefix="/allocations", tags=["allocations"])
app.include_router(trips_router.router, prefix="/trips", tags=["trips"])
app.include_router(logbooks_router.router, prefix="/logbooks", tags=["logbooks"])
app.include_router(fuel_router.router, prefix="/fuel", tags=["fuel"])
app.include_router(maintenance_router.router, prefix="/maintenance", tags=["maintenance"])
app.include_router(inspections_router.router, prefix="/inspections", tags=["inspections"])
app.include_router(breakdowns_router.router, prefix="/breakdowns", tags=["breakdowns"])
app.include_router(notifications_router.router, prefix="/notifications", tags=["notifications"])
app.include_router(reports_router.router, prefix="/reports", tags=["reports"])
app.include_router(audit_router.router, prefix="/audit", tags=["audit"])
app.include_router(admin_router.router, prefix="/admin", tags=["admin"])
app.include_router(api_router.router, prefix="/api", tags=["api"])


# ---------------------------------------------------------------------------
# Middleware: load user permissions into session for template rendering
# ---------------------------------------------------------------------------
@app.middleware("http")
async def load_session_context(request: Request, call_next):
    user_id = request.session.get("user_id")
    if user_id:
        from app.database import SessionLocal
        from app.auth import get_user_permission_codes, get_user_by_id
        db = SessionLocal()
        try:
            user = get_user_by_id(db, int(user_id))
            if user and user.is_active:
                request.session["_perms"] = list(get_user_permission_codes(db, user))
                request.session["_role"] = user.role.code if user.role else ""
                request.session["_username"] = user.username
        finally:
            db.close()
    response = await call_next(request)
    return response


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="tbc_ftms_session",
    max_age=settings.SESSION_IDLE_TIMEOUT_MINUTES * 60,
    same_site="lax",
    https_only=False,
)


# ---------------------------------------------------------------------------
# Root / shell pages
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request, db: Session = Depends(get_db)):
    from app.auth import get_user_by_username
    # If no users exist, redirect to setup
    if db.query(User).first() is None:
        return RedirectResponse(url="/auth/setup", status_code=303)
    # If users exist but not authenticated, redirect to login
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
async def dashboard_home(request: Request, user: User = Depends(get_current_user)):
    from app.routers.dashboard import role_dashboard
    return await role_dashboard(request, user)


@app.get("/user-manual", response_class=HTMLResponse, include_in_schema=False)
async def user_manual(request: Request, user=Depends(get_current_user)):
    from app.templating import templates
    return templates.TemplateResponse(request, "user_manual.html", {"request": request, "user": user, "page_title": "User manual"})


@app.get("/language/{lang}", include_in_schema=False)
async def set_language(lang: str, request: Request):
    if lang in ("sw", "en"):
        request.session["language"] = lang
    referer = request.headers.get("referer") or "/dashboard"
    return RedirectResponse(url=referer, status_code=303)
