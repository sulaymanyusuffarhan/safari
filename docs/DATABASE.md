# Database documentation

## Design principles
- Relational schema with proper primary keys, foreign keys, indexes and constraints.
- Soft deletion (`is_active`, `deactivated_at`, `deactivation_reason`) — historical records are **never** destroyed when a user, driver, department or vehicle is deactivated.
- Transactional safeguards prevent double booking and inconsistent records.
- Immutable audit trail (`audit_logs`) for critical transactions.

## Core entities

| Table | Purpose |
|---|---|
| `users` | System accounts (linked to employees), roles, language, MFA, login tracking |
| `employees` | Institutional employee register (directorate/department/section) |
| `roles`, `permissions`, `role_permissions` | RBAC model |
| `directorates`, `departments`, `sections` | Dynamic organisational structure |
| `media_outlets`, `zone_offices` | TBC media outlets and regional offices |
| `vehicle_categories`, `vehicles` | Fleet register with status and compliance dates |
| `vehicle_documents`, `vehicle_status_history` | Attachments and status change audit |
| `drivers` | Driver register, licences, availability, shift info |
| `transport_request_categories`, `transport_requests` | Transport request lifecycle |
| `request_approvals` | Approve/reject history with reasons |
| `vehicle_assignments` | Vehicle + driver allocations |
| `trips` | Journeys and electronic logbook entries |
| `journey_stops`, `logbook_corrections` | Multi-stop trips and correction history |
| `fuel_types`, `fuel_permits`, `fuel_transactions` | Fuel management |
| `maintenance_categories`, `maintenance_records`, `maintenance_schedules` | Maintenance and preventive alerts |
| `vehicle_inspections` | Before/after-trip inspections |
| `breakdown_reports` | Breakdown reporting |
| `notifications` | In-app notifications |
| `attachments` | File attachments |
| `audit_logs` | Immutable audit trail |
| `system_settings` | Configuration |

## Key relationships
- `users.role_id -> roles.id`
- `users.employee_id -> employees.id` (one user per employee)
- `employees.directorate_id/department_id/section_id -> organisational structure`
- `vehicles.category_id -> vehicle_categories`; `vehicles.assigned_driver_id -> drivers`
- `transport_requests.employee_id -> employees`; `...category_id -> transport_request_categories`
- `vehicle_assignments.request_id/vehicle_id/driver_id`
- `trips.request_id/vehicle_id/driver_id`
- `fuel_transactions.vehicle_id/driver_id/trip_id`
- `audit_logs.user_id -> users.id`

## Distance calculation
`trips.total_distance = trips.end_odometer - trips.start_odometer`, calculated automatically on trip completion.

## Soft-delete rule
Deactivating a user/driver/vehicle/department sets `is_active = false` and records `deactivated_at`/`deactivated_by`/`deactivation_reason`. Related historical transactions (requests, trips, fuel, audit) are preserved.
