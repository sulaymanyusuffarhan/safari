"""Authentication and authorization utilities.

- Password hashing with bcrypt (passlib)
- JWT access tokens (python-jose)
- Role-based access control (RBAC) with configurable permissions
- Session idle / absolute timeout tracking
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Set

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models import User, RolePermission, Permission, AuditLog, Employee

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_db_session() -> Session:
    return SessionLocal()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not user.is_active:
        return None
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        return None
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.commit()
        return None
    # successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    return user


# ---------------------------------------------------------------------------
# Current user dependency
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Prefer session-based auth (HTML UI); fall back to bearer token (API clients)
    user_id = request.session.get("user_id")
    if user_id:
        user = get_user_by_id(db, int(user_id))
        if user and user.is_active:
            request.state.user = user
            request.state.db = db
            return user

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = get_user_by_id(db, int(sub))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    # Session idle / absolute timeout enforcement
    now = datetime.now(timezone.utc)
    if user.last_login:
        idle_minutes = (now - user.last_login.replace(tzinfo=timezone.utc)).total_seconds() / 60.0
        if idle_minutes > settings.SESSION_IDLE_TIMEOUT_MINUTES:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired (idle)")
    # touch last_login as activity marker (bounded write)
    user.last_login = now
    db.add(user)
    db.commit()

    # Attach request metadata for audit
    request.state.user = user
    request.state.db = db
    return user


def require_user(user: User = Depends(get_current_user)) -> User:
    return user


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
def get_user_permission_codes(db: Session, user: User) -> Set[str]:
    """Return the set of permission codes granted to a user via their role."""
    if not user.role or not user.role.is_active:
        return set()
    rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == user.role_id)
        .filter(Permission.is_active == True)  # noqa: E712
        .all()
    )
    return {r[0] for r in rows}


class PermissionChecker:
    def __init__(self, required_permissions: List[str], require_all: bool = True):
        self.required = required_permissions
        self.require_all = require_all

    def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        codes = get_user_permission_codes(db, user)
        if self.require_all:
            ok = all(p in codes for p in self.required)
        else:
            ok = any(p in codes for p in self.required)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user


def has_permission(db: Session, user: User, code: str) -> bool:
    return code in get_user_permission_codes(db, user)


# ---------------------------------------------------------------------------
# Audit logging helper
# ---------------------------------------------------------------------------
def audit_log(
    db: Session,
    action: str,
    table_name: str,
    record_id: Optional[int] = None,
    previous_value: Optional[str] = None,
    new_value: Optional[str] = None,
    reason: Optional[str] = None,
    user: Optional[User] = None,
    ip_address: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        table_name=table_name,
        record_id=record_id,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry
