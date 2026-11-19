# Administrator manual — TBC-FTMS

## Roles covered
System Administrator (ICT).

## 1. First-time setup
Visit `/auth/setup` to create the first System Administrator account. That admin can then manage everything through the admin panel.

## 2. Users & access control
- Create and manage user accounts; link each to an employee record.
- Assign roles (System Administrator, Transport Officer, Transport Supervisor, Driver, Employee, Department Head, Finance & Accounts, Internal Audit, Management/DG).
- Manage permissions per role and module.
- Administrators do **not** automatically receive approval rights for operational requests, fuel or assignments.

## 3. Organisational structure
Manage directorates, departments, sections, media outlets and zone offices. Add, edit, deactivate and reorganise as needed. Every transport request is associated with an employee's department/directorate/section or authorised office.

## 4. Fleet & drivers
- Register vehicles (registration, make, model, category, fuel type, capacity, insurance/licence/inspection expiry, photos, documents).
- Set vehicle status with a mandatory reason (audited).
- Deactivate disposed vehicles without deleting history.
- Register drivers (licence number/category/expiry, availability, shift).
- Maintain driver assignment and journey history.

## 5. Configuration
- Vehicle categories, request categories, fuel types, maintenance categories.
- Notification templates and system settings.
- Approval workflows (configurable per TBC procedures).

## 6. Backup & recovery
Back up the database and `app/static/uploads` regularly. Test restoration (see `docs/INSTALLATION.md`).

## 7. Logs & audit
Review technical logs and the immutable audit trail (who did what, when, and why).
