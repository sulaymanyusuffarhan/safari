# Testing and acceptance criteria

The following 12 scenarios must pass before production deployment.

| # | Scenario | Expected result |
|---|---|---|
| 1 | Employee submits request | TO immediately sees all suitable available vehicles |
| 2 | TO allocates vehicle + driver | Employee and driver receive correct assignment info |
| 3 | Double booking | System prevents conflicting vehicle/driver allocations |
| 4 | News assignment | Multiple destinations + broadcasting equipment captured |
| 5 | Administrative assignment | Request supported without news-related fields |
| 6 | Vehicle breakdown | TO notified; vehicle unavailable until cleared |
| 7 | Fuel accountability | Fuel transaction linked to vehicle, driver, journey |
| 8 | Electronic logbook | Distance auto-calculated from odometer readings |
| 9 | Audit | Auditor traces approval, allocation and fuel issuance |
| 10 | Reporting | Monthly report by directorate/department |
| 11 | Permissions | Employee cannot access finance/fleet admin or other departments |
| 12 | Vehicle unavailability | Reason + responsible user recorded |

All critical buttons work, all forms save, dashboards display database-driven data, reports calculate from stored transactions.

## Test credentials (development)
- System Administrator: `admin` / `Admin123!` (create via `/auth/setup`)
