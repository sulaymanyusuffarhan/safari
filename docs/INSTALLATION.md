# Installation, environments & backup/recovery

## 1. Requirements
- Python 3.11+
- `pip`, `venv`
- SQLite (development) or PostgreSQL (production)
- Modern web browser

## 2. Install
```bash
git clone <repo>
cd safari
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 3. Environment variables (`.env`)
| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Session/JWT signing secret (change in prod) | change-this... |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./tbc_ftms.db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime | 60 |
| `SESSION_IDLE_TIMEOUT_MINUTES` | Session idle timeout | 480 |
| `DEFAULT_LANGUAGE` | `sw` or `en` | `sw` |
| `SEED_DEMO_DATA` | Seed labelled demo data on first run | `true` |

Never commit real secrets. Use environment variables or an approved secrets manager.

## 4. Run
```bash
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5000
```
Visit http://localhost:5000. First run creates tables and seeds reference data.

## 5. Environments
- **Development:** SQLite, `DEBUG=true`, demo data seeded.
- **Testing:** separate test database, run the 12 acceptance scenarios.
- **Production:** PostgreSQL, `DEBUG=false`, strong `SECRET_KEY`, HTTPS, no demo data, approved Government hosting.

The system is not tied to a single OS or database platform; swap `DATABASE_URL` to PostgreSQL for production.

## 6. Migrations
Alembic is configured. To create a migration after model changes:
```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## 7. Backup & recovery
The application database (`tbc_ftms.db` by default, or your configured PostgreSQL database) must be backed up on a regular schedule.

**Backup (SQLite):**
```bash
cp tbc_ftms.db tbc_ftms.db.bak.$(date +%F)
```

**Restore:**
```bash
cp tbc_ftms.db.bak.<date> tbc_ftms.db
```

**PostgreSQL:**
```bash
pg_dump tbc_ftms > backup.sql
psql tbc_ftms < backup.sql
```

Back up uploaded files in `app/static/uploads` alongside the database. Test restoration periodically as part of UAT.

## 8. First-time setup
No users exist initially. Visit `/auth/setup` to create the first System Administrator, who can then create users, roles, permissions and organisational structure through the admin panel.
