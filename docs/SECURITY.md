# Security and data protection

## Authentication & sessions
- Bcrypt password hashing (configurable rounds).
- JWT access tokens for API clients; server-side sessions for the UI.
- Session idle timeout and absolute timeout; automatic logout after inactivity.
- Account lockout after 5 failed login attempts (30 minutes).
- Password reset flow; MFA supported where approved.

## Authorisation
- Role-based access control (RBAC) with fine-grained permissions per module/action.
- Separation of duties: drivers cannot approve their own fuel; TOs cannot erase completed trips; department heads cannot change logbooks; admins cannot silently change operational transactions; auditors are read-only.
- Transport Officers do **not** automatically receive approval rights for fuel/assignments.

## Data protection
- Access controls prevent employees from viewing other departments' confidential records or live vehicle locations.
- Live GPS/location data is never exposed to ordinary employees or unauthorised users.
- File upload validation (type/size limits); secure document storage.
- Audit trail records user, action, before/after values, reason, IP address and timestamp for critical transactions (requests, approvals, allocations, status changes, fuel, logbook corrections, maintenance, deactivations, permission changes).

## Transport-layer & input security
- Passwords, API keys, DB credentials and tokens are never hardcoded; environment variables / secrets manager.
- Parameterised database operations (SQLAlchemy ORM) — SQL injection protection.
- CSRF protection, XSS protection (Jinja2 auto-escaping), input validation.
- Encryption in transit (HTTPS in production); encryption at rest per hosting policy.

## Compliance
Aligned with eGA/EXT/APA/005 v3.0, e-Government Act No. 10 of 2019, and applicable Tanzanian data protection and cybersecurity requirements. Designed for an approved Government hosting environment.
