# TBC-FTMS — Tanzania Broadcasting Corporation Fleet & Transport Management System

A complete, production-oriented fleet and transport management system for the Tanzania Broadcasting Corporation (TBC), built to give management visibility, Transport Officers operational control, drivers clear responsibilities, and employees a transparent way to request and obtain transport.

**Primary success measure:** No employee is told transport is unavailable without the responsible Transport Officer being able to establish and explain the actual availability of suitable vehicles and drivers at the requested time.

## Key features
- Employee transport request portal (news gathering, official duties, regional/zone, emergency)
- Role-based access control: System Admin, Transport Officer, Transport Supervisor, Driver, Employee, Department Head, Finance, Internal Audit, Management/DG
- Central vehicle availability dashboard with real-time status board and unavailability explanations
- Intelligent vehicle/driver allocation engine with double-booking prevention
- Electronic logbooks (auto distance = end odometer − start odometer, correction history)
- Fuel management & accountability
- Maintenance, preventive alerts, inspections, breakdown reporting
- Notifications, audit trail, reporting & CSV export
- Kiswahili (default) / English bilingual UI, responsive design
- TBC branding (logo & emblem), eGA/EXT/APA/005 v3.0 aligned

## Tech stack
- Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite (dev) / PostgreSQL (prod)
- JWT authentication, bcrypt passwords, session management
- Server-rendered Jinja2 UI with Tailwind CSS, HTMX, Chart.js
- Alembic migrations

## Quick start

```bash
# 1. Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment config
cp .env.example .env
# (edit .env for production: SECRET_KEY, DATABASE_URL, etc.)

# 4. Run the server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5000
```

Then open http://localhost:5000. The first visit initialises the database and seeds reference data (organisational structure, vehicle categories, request categories, etc.).

## First-time setup
Because no users exist, you are redirected to `/auth/setup` to create the first System Administrator. Demo credentials (development only): `admin` / `Admin123!`.

## Demo data
`settings.SEED_DEMO_DATA=true` seeds clearly-labelled **DEMO DATA** (vehicles, drivers, employees, requests). Replace with authorised TBC institutional records before production.

## Documentation (in `docs/`)
- `INSTALLATION.md` — installation, environments, backup & recovery
- `DATABASE.md` — entity-relationship schema and table reference
- `API.md` — API endpoints and authentication
- `USER_MANUAL.md` — employee, driver, Transport Officer procedures
- `ADMIN_MANUAL.md` — user, role, permission and organisational management
- `SECURITY.md` — security controls and data protection
- `TESTING.md` — test scenarios and acceptance criteria

## Compliance
Aligned with eGA/EXT/APA/005 v3.0 (Standards for e-Government Applications), e-Government Act No. 10 of 2019, and Tanzanian data protection/cybersecurity requirements. Designed for deployment in an approved Government hosting environment.
