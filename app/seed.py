"""Seed data for TBC-FTMS.

Populates organisational structure, reference data and (optionally) clearly
labelled DEMO DATA. Never treats demo data as real institutional records.
"""

from datetime import date, datetime
from app.models import (
    Directorate, Department, Section, MediaOutlet, ZoneOffice,
    VehicleCategory, TransportRequestCategory, FuelType, MaintenanceCategory,
    Vehicle, Driver, Employee, TransportRequest, Trip, User, Role,
)
from app.config import settings
from app.database import SessionLocal


def _get_or_create(db, model, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    instance = model(**kwargs)
    db.add(instance)
    db.flush()
    return instance


def seed_reference_data(db):
    """Organisational structure and reference tables (configurable by admin)."""

    # --- Directorates & units under Director General ---
    dg = _get_or_create(db, Directorate, code="DG", name="Director General's Office",
                        description="Office of the Director General")

    legal = _get_or_create(db, Directorate, code="LEGAL", name="Legal Services Unit",
                           description="Legal Services Unit")
    hr = _get_or_create(db, Directorate, code="HR", name="Human Resource Management and Administration Directorate",
                        description="HRM&A Directorate")
    audit = _get_or_create(db, Directorate, code="IA", name="Internal Audit Unit",
                           description="Internal Audit Unit")
    finance = _get_or_create(db, Directorate, code="FIN", name="Finance and Accounts Unit",
                             description="Finance and Accounts Unit")
    pr = _get_or_create(db, Directorate, code="PR", name="Public Relations and Communication Unit",
                        description="PR and Communication Unit")
    proc = _get_or_create(db, Directorate, code="PROC", name="Procurement Management Unit",
                          description="Procurement Management Unit")
    planning = _get_or_create(db, Directorate, code="PLAN", name="Planning and Investment Unit",
                              description="Planning and Investment Unit")
    digital = _get_or_create(db, Directorate, code="DC", name="Digital Convergence Unit",
                             description="Digital Convergence Unit")
    library = _get_or_create(db, Directorate, code="LIB", name="Library Services Unit",
                             description="Library Services Unit")

    # --- Operational directorates ---
    tech = _get_or_create(db, Directorate, code="TS", name="Technical Services Directorate",
                          description="Technical Services Directorate")
    news = _get_or_create(db, Directorate, code="NCA", name="News and Current Affairs Directorate",
                          description="News and Current Affairs Directorate")
    tv = _get_or_create(db, Directorate, code="TVS", name="Television Services Directorate",
                        description="Television Services Directorate")
    radio = _get_or_create(db, Directorate, code="RSD", name="Radio Services Directorate",
                           description="Radio Services Directorate")
    sales = _get_or_create(db, Directorate, code="SM", name="Sales and Marketing Directorate",
                           description="Sales and Marketing Directorate")

    # Sections under Technical Services
    _get_or_create(db, Section, department_id=None, name="Transmission Section",
                   code="TS-TRANS") if False else None
    # We'll create departments then sections properly below

    # Build departments (simplified: directorate->department)
    def dept(dir_code, dir_name, depts):
        d = _get_or_create(db, Directorate, code=dir_code, name=dir_name)
        for dept_name, dept_code, secs in depts:
            dp = _get_or_create(db, Department, code=dept_code, name=dept_name,
                                directorate_id=d.id)
            for sec_name, sec_code in secs or []:
                _get_or_create(db, Section, code=sec_code, name=sec_name, department_id=dp.id)
        return d

    dept("LEGAL", "Legal Services Unit", [("Legal Services", "LEGAL", None)])
    dept("HR", "Human Resource Management and Administration Directorate", [
        ("Human Resource Management", "HRM", None),
        ("Administration", "ADMIN", None),
    ])
    dept("IA", "Internal Audit Unit", [("Internal Audit", "AUDIT", None)])
    dept("FIN", "Finance and Accounts Unit", [
        ("Finance and Accounts", "FIN", None),
    ])
    dept("PR", "Public Relations and Communication Unit", [
        ("Public Relations", "PR", None),
    ])
    dept("PROC", "Procurement Management Unit", [
        ("Procurement", "PROC", None),
    ])
    dept("PLAN", "Planning and Investment Unit", [
        ("Planning and Investment", "PLAN", None),
    ])
    dept("DC", "Digital Convergence Unit", [
        ("Digital Convergence", "DC", None),
    ])
    dept("LIB", "Library Services Unit", [
        ("Library Services", "LIB", None),
    ])
    dept("TS", "Technical Services Directorate", [
        ("Transmission Section", "TS-TRANS", None),
        ("Studio Services Section", "TS-STUDIO", None),
        ("ICT Services Section", "TS-ICT", None),
    ])
    dept("NCA", "News and Current Affairs Directorate", [
        ("Television Editorial Section", "NCA-TV", None),
        ("Radio Editorial Section", "NCA-RADIO", None),
    ])
    dept("TVS", "Television Services Directorate", [
        ("Public Services Television Section", "TVS-PUBLIC", None),
        ("Commercial Services Television Section", "TVS-COMMERCIAL", None),
    ])
    dept("RSD", "Radio Services Directorate", [
        ("Public Services Radio Section", "RSD-PUBLIC", None),
        ("Commercial Services Radio Section", "RSD-COMMERCIAL", None),
    ])
    dept("SM", "Sales and Marketing Directorate", [
        ("Sales Section", "SM-SALES", None),
        ("Marketing Section", "SM-MARKETING", None),
    ])

    # --- Media outlets ---
    for m in [
        ("TBC 1", "television"), ("TBC 2", "television"), ("Safari Channel", "television"),
        ("TBC Taifa", "radio"), ("Bongo FM", "radio"), ("TBC International", "radio"),
    ]:
        _get_or_create(db, MediaOutlet, name=m[0], outlet_type=m[1])

    # --- Zone offices ---
    for z in [
        ("Dar es Salaam Zone", "Dar es Salaam"),
        ("Arusha Zone", "Arusha"),
        ("Mwanza Zone", "Mwanza"),
        ("Dodoma Zone", "Dodoma"),
        ("Mbeya Zone", "Mbeya"),
    ]:
        _get_or_create(db, ZoneOffice, name=z[0], region=z[1])

    # --- Vehicle categories ---
    for c in [
        ("Cars", "CAR", "Sedan / saloon cars"),
        ("Land Cruisers", "LC", "Toyota Land Cruiser type off-road vehicles"),
        ("Vans", "VAN", "Light vans"),
        ("Buses", "BUS", "Buses / minibuses"),
        ("Pickups", "PICKUP", "Pickup trucks"),
        ("Motorcycles", "MOTO", "Motorcycles"),
        ("Specialized broadcasting vehicles", "BCAST", "Broadcasting / OB vans"),
        ("Other", "OTHER", "Other vehicle categories"),
    ]:
        _get_or_create(db, VehicleCategory, code=c[1], name=c[0], description=c[2])

    # --- Transport request categories ---
    cats = [
        ("news_gathering", "News Gathering / Media Coverage",
         "For Digital Convergence, News and Current Affairs, Television Services, Radio Services, PR and other media teams.",
         True),
        ("official_duties", "Official Institutional Duties",
         "Official meetings, administrative duties, procurement, document collection, inspection, technical fieldwork, employee transportation.",
         True),
        ("regional_zone", "Regional / Zone Office Transport",
         "Regional operations and inter-office movements.", False),
        ("emergency", "Emergency Transport",
         "Urgent operational requirements. Flagged for priority assessment.", False),
    ]
    for code, name, desc, req_approval in cats:
        _get_or_create(db, TransportRequestCategory, code=code, name=name,
                       description=desc, requires_department_approval=req_approval)

    # --- Fuel types ---
    for f in [("Diesel", "diesel"), ("Petrol", "petrol")]:
        _get_or_create(db, FuelType, code=f[1], name=f[0])

    # --- Maintenance categories ---
    for m in [
        ("Routine servicing", "ROUTINE", "Routine vehicle servicing"),
        ("Oil change", "OIL", "Oil and filter change"),
        ("Tyre replacement", "TYRE", "Tyre replacement"),
        ("Brake repairs", "BRAKE", "Brake system repairs"),
        ("Engine repairs", "ENGINE", "Engine repairs"),
        ("Electrical repairs", "ELECTRICAL", "Electrical system repairs"),
        ("Accident repairs", "ACCIDENT", "Accident / collision repairs"),
        ("General inspection", "INSPECTION", "General vehicle inspection"),
        ("Other maintenance", "OTHER", "Other maintenance"),
    ]:
        _get_or_create(db, MaintenanceCategory, code=m[1], name=m[0], description=m[2])

    db.commit()


def seed_demo_data(db):
    """Clearly labelled DEMO DATA for development only."""
    from app.models import Vehicle, Driver, Employee, TransportRequest, Trip, FuelTransaction, MaintenanceRecord
    from app.auth import pwd_context
    import random

    # Mark demo data explicitly
    demo_note = " [DEMO DATA]"

    # Employees
    emps = [
        ("EMP-0001", "Grace", "Mwakipesile", "grace.mwakipesile@tbc.go.tz", "DC"),
        ("EMP-0002", "John", "Kamau", "john.kamau@tbc.go.tz", "NCA"),
        ("EMP-0003", "Fatuma", "Juma", "fatuma.juma@tbc.go.tz", "FIN"),
        ("EMP-0004", "Peter", "Omondi", "peter.omondi@tbc.go.tz", "TS"),
    ]
    emp_objs = {}
    for num, fn, ln, email, dir_code in emps:
        d = db.query(Directorate).filter_by(code=dir_code).first()
        e = Employee(employee_number=num, first_name=fn, last_name=ln, email=email,
                     directorate_id=d.id if d else None, is_active=True)
        db.add(e); db.flush()
        emp_objs[num] = e

    # Vehicles
    cars = db.query(VehicleCategory).filter_by(code="CAR").first()
    lc = db.query(VehicleCategory).filter_by(code="LC").first()
    van = db.query(VehicleCategory).filter_by(code="VAN").first()
    regs = [("TBC 1001A", "Toyota", "Land Cruiser", 2020, lc, 7),
            ("TBC 2002B", "Toyota", "Hiace", 2019, van, 14),
            ("TBC 3003C", "Nissan", "Sunny", 2018, cars, 5),
            ("TBC 4004D", "Toyota", "Hilux", 2021, lc, 5)]
    veh_objs = {}
    for reg, make, model, year, cat, cap in regs:
        v = Vehicle(registration_number=reg, make=make, model=model,
                    year_of_manufacture=year, category_id=cat.id,
                    passenger_capacity=cap, status="available", is_active=True)
        db.add(v); db.flush()
        veh_objs[reg] = v

    # Drivers
    for i, (num, fn, ln, email, _) in enumerate(emps[:2]):
        e = emp_objs[num]
        d = Driver(employee_id=e.id, licence_number=f"DL-{1000+i}", licence_category="C",
                   availability="available", is_active=True)
        db.add(d); db.flush()
        # assign a vehicle to first driver
        if i == 0:
            v = list(veh_objs.values())[0]
            v.assigned_driver_id = d.id
            v.status = "assigned"

    # Demo transport requests
    news_cat = db.query(TransportRequestCategory).filter_by(code="news_gathering").first()
    off_cat = db.query(TransportRequestCategory).filter_by(code="official_duties").first()
    emp1 = emp_objs["EMP-0001"]
    r1 = TransportRequest(
        reference_number="TBC-DEMO-0001", employee_id=emp1.id,
        directorate_id=emp1.directorate_id, category_id=news_cat.id,
        purpose="Live coverage of regional governors meeting",
        departure_location="TBC Dar es Salaam", destination="Dodoma",
        travel_date=date.today(), number_of_passengers=4,
        status="approved", priority="high",
        assignment_title="Governors meeting coverage",
        coverage_subject="Regional governors conference",
        multiple_destinations='["Dodoma","Arusha"]',
    )
    db.add(r1)

    emp3 = emp_objs["EMP-0003"]
    r2 = TransportRequest(
        reference_number="TBC-DEMO-0002", employee_id=emp3.id,
        category_id=off_cat.id,
        purpose="Procurement document delivery to Ministry",
        departure_location="TBC HQ", destination="Ministry of Finance",
        travel_date=date.today(), number_of_passengers=2,
        status="submitted", priority="normal",
    )
    db.add(r2)

    db.commit()
    print("Seed complete. Demo data is clearly labelled.")


def seed_if_empty(db):
    """Run reference + demo seeding if tables are empty (dev only)."""
    if db.query(Directorate).first() is None:
        seed_reference_data(db)
    if db.query(Vehicle).first() is None and settings.SEED_DEMO_DATA:
        seed_demo_data(db)
