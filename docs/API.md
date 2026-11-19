# API documentation

TBC-FTMS is primarily a server-rendered web application. A documented JSON API is available under `/api` for future institutional integrations (HR, finance, SMS, GPS, mapping). Integrations are optional and configurable; where no API exists, secure manual entry and CSV/Excel import/export are provided.

## Authentication
API clients use JWT bearer tokens obtained via `POST /auth/login` (returns `access_token`). Include `Authorization: Bearer <token>` in requests.

## Key endpoints
- `POST /auth/login` — authenticate, returns JWT
- `GET /auth/logout` — end session
- `GET /vehicles` — fleet register
- `GET /drivers` — driver register
- `GET /requests` — transport requests
- `POST /requests/create` — submit request
- `POST /requests/{id}/approve`, `/reject` — approval workflow
- `POST /allocations/allocate` — vehicle/driver allocation
- `GET /trips`, `POST /trips/create` — journeys / logbook
- `GET /fuel`, `POST /fuel/create` — fuel transactions
- `GET /maintenance`, `GET /breakdowns`, `GET /inspections` — operations
- `GET /notifications` — user notifications
- `GET /audit` — audit trail (auditors only)
- `GET /reports/export/requests.csv` — CSV export
- `GET /language/{sw,en}` — switch language

Role-based permissions apply to every endpoint; unauthorised calls return 403.
