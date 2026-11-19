"""SQLAlchemy ORM models for TBC-FTMS.

Relational schema covering:
users, roles, permissions, employees, organisational structure,
vehicles, drivers, transport requests, approvals, assignments,
trips/logbooks, fuel, maintenance, inspections, breakdowns,
notifications, attachments, audit log, system settings.

All tables use soft-deletion (is_active) so historical records are
never destroyed when a user, driver, department or vehicle is deactivated.
"""

import json
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Integer, String, Text, DateTime, Date, Time, Boolean,
    ForeignKey, Numeric, CheckConstraint, Index, func, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )


# ---------------------------------------------------------------------------
# Organisational structure
# ---------------------------------------------------------------------------
class Directorate(Base, TimestampMixin):
    __tablename__ = "directorates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deactivated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deactivation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    departments: Mapped[list["Department"]] = relationship(
        back_populates="directorate", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(back_populates="directorate")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    directorate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("directorates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    directorate: Mapped["Directorate"] = relationship(back_populates="departments")
    sections: Mapped[list["Section"]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class Section(Base, TimestampMixin):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department: Mapped["Department"] = relationship(back_populates="sections")
    employees: Mapped[list["Employee"]] = relationship(back_populates="section")


class MediaOutlet(Base, TimestampMixin):
    __tablename__ = "media_outlets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    outlet_type: Mapped[str] = mapped_column(String(20), nullable=False)  # television / radio
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ZoneOffice(Base, TimestampMixin):
    __tablename__ = "zone_offices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ---------------------------------------------------------------------------
# Security / RBAC
# ---------------------------------------------------------------------------
class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    module: Mapped[str] = mapped_column(String(60), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)  # create, read, update, delete, approve
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")

    __table_args__ = (
        Index("uq_role_permission", "role_id", "permission_id", unique=True),
    )


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    directorate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("directorates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    section_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(String(40), default="active")  # active, leave, retired, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    full_name_property = None  # placeholder, see @property below

    directorate: Mapped[Optional["Directorate"]] = relationship(back_populates="employees")
    department: Mapped[Optional["Department"]] = relationship(back_populates="employees")
    section: Mapped[Optional["Section"]] = relationship(back_populates="employees")
    user: Mapped[Optional["User"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    driver: Mapped[Optional["Driver"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    transport_requests: Mapped[list["TransportRequest"]] = relationship(back_populates="employee")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=True, unique=True, index=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    language: Mapped[str] = mapped_column(String(10), default="sw", nullable=False)  # sw / en
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    employee: Mapped[Optional["Employee"]] = relationship(back_populates="user")
    role: Mapped[Optional["Role"]] = relationship(back_populates="users")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


# ---------------------------------------------------------------------------
# Fleet
# ---------------------------------------------------------------------------
class VehicleCategory(Base, TimestampMixin):
    __tablename__ = "vehicle_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="category")


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registration_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year_of_manufacture: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vehicle_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fuel_type: Mapped[str] = mapped_column(String(40), default="diesel")  # diesel/petrol/electric/hybrid
    engine_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    chassis_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    passenger_capacity: Mapped[int] = mapped_column(Integer, default=5)
    acquisition_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    acquisition_cost: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="available", nullable=False, index=True)
    # available / reserved / assigned / in_use / returning / under_maintenance / under_repair / out_of_service / temporarily_unavailable
    current_mileage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    insurance_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    road_licence_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    road_licence_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    inspection_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    assigned_driver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owned_by_department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    current_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deactivated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deactivation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category: Mapped[Optional["VehicleCategory"]] = relationship(back_populates="vehicles")
    assigned_driver: Mapped[Optional["Driver"]] = relationship(
        foreign_keys=[assigned_driver_id], back_populates="assigned_vehicles"
    )
    owned_department: Mapped[Optional["Department"]] = relationship()
    status_history: Mapped[list["VehicleStatusHistory"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    documents: Mapped[list["VehicleDocument"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    trips: Mapped[list["Trip"]] = relationship(back_populates="vehicle")
    fuel_transactions: Mapped[list["FuelTransaction"]] = relationship(back_populates="vehicle")
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(back_populates="vehicle")
    inspections: Mapped[list["VehicleInspection"]] = relationship(back_populates="vehicle")
    breakdown_reports: Mapped[list["BreakdownReport"]] = relationship(back_populates="vehicle")


class VehicleDocument(Base, TimestampMixin):
    __tablename__ = "vehicle_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="documents")


class VehicleStatusHistory(Base, TimestampMixin):
    __tablename__ = "vehicle_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="status_history")


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------
class Driver(Base, TimestampMixin):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    licence_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    licence_category: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. B, C, D, E
    licence_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(String(40), default="active")
    availability: Mapped[str] = mapped_column(String(40), default="available")  # available / on_duty / on_leave / unavailable
    shift_info: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    training_qualifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="driver")
    assigned_vehicles: Mapped[list["Vehicle"]] = relationship(
        foreign_keys=[Vehicle.assigned_driver_id], back_populates="assigned_driver"
    )
    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")
    fuel_transactions: Mapped[list["FuelTransaction"]] = relationship(back_populates="driver")
    inspections: Mapped[list["VehicleInspection"]] = relationship(back_populates="driver")
    breakdown_reports: Mapped[list["BreakdownReport"]] = relationship(back_populates="driver")


# ---------------------------------------------------------------------------
# Transport requests
# ---------------------------------------------------------------------------
class TransportRequestCategory(Base, TimestampMixin):
    __tablename__ = "transport_request_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requires_department_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    requests: Mapped[list["TransportRequest"]] = relationship(back_populates="category")


class TransportRequest(Base, TimestampMixin):
    __tablename__ = "transport_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reference_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    directorate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("directorates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    section_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("transport_request_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    media_outlet_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("media_outlets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    zone_office_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("zone_offices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    departure_location: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    departure_time: Mapped[Optional[Time]] = mapped_column(Time, nullable=True)
    expected_return_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_return_time: Mapped[Optional[Time]] = mapped_column(Time, nullable=True)
    number_of_passengers: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    equipment_luggage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    special_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # News gathering / media coverage extra fields
    assignment_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    coverage_subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assignment_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coverage_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    journalist_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    camera_operators: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photographers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crew_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    coverage_duration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    urgency_level: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    assignment_editor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    multiple_destinations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list

    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False, index=True)
    # draft / submitted / pending_departmental_approval / pending_transport_review / approved /
    # rejected / vehicle_assigned / driver_assigned / confirmed / in_progress / completed / cancelled / on_hold
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)  # low/normal/high/emergency

    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    department_approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    department_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    transport_reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transport_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="transport_requests")
    category: Mapped[Optional["TransportRequestCategory"]] = relationship(back_populates="requests")
    media_outlet: Mapped[Optional["MediaOutlet"]] = relationship()
    zone_office: Mapped[Optional["ZoneOffice"]] = relationship()
    approvals: Mapped[list["RequestApproval"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["VehicleAssignment"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    trips: Mapped[list["Trip"]] = relationship(back_populates="request")


class RequestApproval(Base, TimestampMixin):
    __tablename__ = "request_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transport_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # approve / reject / hold
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    request: Mapped["TransportRequest"] = relationship(back_populates="approvals")


# ---------------------------------------------------------------------------
# Vehicle & driver assignment
# ---------------------------------------------------------------------------
class VehicleAssignment(Base, TimestampMixin):
    __tablename__ = "vehicle_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("transport_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    start_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    # active / completed / cancelled
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # human override with reason

    request: Mapped[Optional["TransportRequest"]] = relationship(back_populates="assignments")
    vehicle: Mapped["Vehicle"] = relationship()
    driver: Mapped[Optional["Driver"]] = relationship()
    assigned_by_user: Mapped[Optional["User"]] = relationship()


# ---------------------------------------------------------------------------
# Trips / electronic logbook
# ---------------------------------------------------------------------------
class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    request_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("transport_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    start_point: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    departure_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    start_odometer: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    arrival_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_odometer: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_distance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # end - start
    fuel_issued: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fuel_consumed: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    passenger_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False, index=True)
    # draft / in_progress / completed / cancelled / on_hold

    request: Mapped[Optional["TransportRequest"]] = relationship(back_populates="trips")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="trips")
    driver: Mapped["Driver"] = relationship(back_populates="trips")
    stops: Mapped[list["JourneyStop"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )
    fuel_transactions: Mapped[list["FuelTransaction"]] = relationship(back_populates="trip")
    inspections: Mapped[list["VehicleInspection"]] = relationship(back_populates="trip")


class JourneyStop(Base, TimestampMixin):
    __tablename__ = "journey_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    arrival_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    departure_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="stops")


class LogbookCorrection(Base, TimestampMixin):
    __tablename__ = "logbook_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Fuel management
# ---------------------------------------------------------------------------
class FuelType(Base, TimestampMixin):
    __tablename__ = "fuel_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FuelPermit(Base, TimestampMixin):
    __tablename__ = "fuel_permits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    driver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quantity_allowed: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    date_issued: Mapped[date] = mapped_column(Date, nullable=False)
    issued_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    # active / used / expired / cancelled

    vehicle: Mapped[Optional["Vehicle"]] = relationship()
    driver: Mapped[Optional["Driver"]] = relationship()


class FuelTransaction(Base, TimestampMixin):
    __tablename__ = "fuel_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fuel_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("fuel_types.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fuel_station_supplier: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    odometer_reading: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    issue_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    permit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("fuel_permits.id", ondelete="SET NULL"), nullable=True, index=True
    )
    issuing_officer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    receipt_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    trip_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="fuel_transactions")
    driver: Mapped[Optional["Driver"]] = relationship(back_populates="fuel_transactions")
    fuel_type: Mapped[Optional["FuelType"]] = relationship()
    permit: Mapped[Optional["FuelPermit"]] = relationship()
    issuing_officer: Mapped[Optional["User"]] = relationship()
    trip: Mapped[Optional["Trip"]] = relationship(back_populates="fuel_transactions")


# ---------------------------------------------------------------------------
# Maintenance & repairs
# ---------------------------------------------------------------------------
class MaintenanceCategory(Base, TimestampMixin):
    __tablename__ = "maintenance_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MaintenanceRecord(Base, TimestampMixin):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("maintenance_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reported_problem: Mapped[str] = mapped_column(Text, nullable=False)
    date_reported: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mileage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assigned_mechanic_workshop: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    approved_cost: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    actual_cost: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    parts_replaced: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_performed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    approval_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="reported", nullable=False, index=True)
    # reported / approved / in_progress / completed / cancelled

    vehicle: Mapped["Vehicle"] = relationship(back_populates="maintenance_records")
    category: Mapped[Optional["MaintenanceCategory"]] = relationship()


class MaintenanceSchedule(Base, TimestampMixin):
    __tablename__ = "maintenance_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("maintenance_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    due_mileage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Inspections & breakdowns
# ---------------------------------------------------------------------------
class VehicleInspection(Base, TimestampMixin):
    __tablename__ = "vehicle_inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    trip_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True
    )
    inspection_type: Mapped[str] = mapped_column(String(20), nullable=False)  # before_trip / after_trip
    checklist: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    defects: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inspection_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    odometer_reading: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fuel_level: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="inspections")
    driver: Mapped[Optional["Driver"]] = relationship(back_populates="inspections")
    trip: Mapped[Optional["Trip"]] = relationship(back_populates="inspections")


class BreakdownReport(Base, TimestampMixin):
    __tablename__ = "breakdown_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    breakdown_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    nature: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    passengers_safe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    towing_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="reported", nullable=False, index=True)
    # reported / assigned / resolved / cleared
    reported_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notified_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # transport officer
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="breakdown_reports")
    driver: Mapped[Optional["Driver"]] = relationship(back_populates="breakdown_reports")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(60), default="info", nullable=False)
    # info / success / warning / error / request / allocation / maintenance / fuel / breakdown
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    link_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="notifications")


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------
class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(200), nullable=False)
    uploaded_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    previous_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")


# ---------------------------------------------------------------------------
# System settings
# ---------------------------------------------------------------------------
class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
