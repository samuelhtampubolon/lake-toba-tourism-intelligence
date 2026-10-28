"""Authentication, password hashing, and opaque session management."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)
    _USE_ARGON2 = True
except ImportError:
    _USE_ARGON2 = False

from app.config import settings
from app.models.entities import User, UserSession

def hash_password(password: str) -> str:
    """Hash a password using Argon2id or strong PBKDF2-SHA256 fallback."""
    if _USE_ARGON2:
        return _hasher.hash(password)
    # Fallback to PBKDF2 with 310,000 iterations (OWASP recommendation)
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310000)
    return f"pbkdf2:sha256:310000${salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash."""
    if not hashed_password or not plain_password:
        return False
    if hashed_password.startswith("$argon2"):
        if _USE_ARGON2:
            try:
                return _hasher.verify(hashed_password, plain_password)
            except VerifyMismatchError:
                return False
            except Exception:
                return False
        return False
    elif hashed_password.startswith("pbkdf2:"):
        try:
            parts = hashed_password.split("$")
            salt = bytes.fromhex(parts[1])
            expected_key = bytes.fromhex(parts[2])
            actual_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 310000)
            return hmac.compare_digest(actual_key, expected_key)
        except Exception:
            return False
    return False

def generate_session_token() -> Tuple[str, str]:
    """Generate an opaque session token and its SHA-256 database hash."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash

def hash_token(token: str) -> str:
    """Hash an opaque token for DB lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_user_session(db: Session, user: User) -> Tuple[UserSession, str]:
    """Create a new authenticated session in database."""
    raw_token, token_hash = generate_session_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)

    session_obj = UserSession(
        user_id=user.id,
        session_token_hash=token_hash,
        created_at=now,
        last_accessed_at=now,
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj, raw_token

def validate_session(db: Session, raw_token: str) -> Optional[User]:
    """Validate raw session token with inactivity and absolute timeout checks."""
    if not raw_token:
        return None

    token_hash = hash_token(raw_token)
    session_obj = db.query(UserSession).filter(
        UserSession.session_token_hash == token_hash,
        UserSession.is_revoked == False
    ).first()

    if not session_obj:
        return None

    now = datetime.now(timezone.utc)
    # Check absolute expiry
    if session_obj.expires_at.replace(tzinfo=timezone.utc) < now:
        session_obj.is_revoked = True
        db.commit()
        return None

    # Check inactivity timeout
    last_accessed = session_obj.last_accessed_at.replace(tzinfo=timezone.utc)
    if (now - last_accessed).total_seconds() > (settings.SESSION_INACTIVITY_MINUTES * 60):
        session_obj.is_revoked = True
        db.commit()
        return None

    # Update last accessed
    session_obj.last_accessed_at = now
    db.commit()

    user = db.query(User).filter(User.id == session_obj.user_id, User.is_active == True).first()
    return user

def revoke_session(db: Session, raw_token: str) -> None:
    """Revoke session upon logout."""
    if not raw_token:
        return
    token_hash = hash_token(raw_token)
    session_obj = db.query(UserSession).filter(
        UserSession.session_token_hash == token_hash
    ).first()
    if session_obj:
        session_obj.is_revoked = True
        db.commit()
