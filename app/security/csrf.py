"""Synchronizer CSRF protection using HMAC tokens."""
import hmac
import hashlib
from typing import Optional
from fastapi import Request, HTTPException, status
from app.config import settings

def generate_csrf_token(session_token: str) -> str:
    """Generate deterministic HMAC-SHA256 CSRF token tied to the user's session token."""
    if not session_token:
        return ""
    key = settings.APP_SECRET_KEY.encode("utf-8")
    msg = f"csrf:{session_token}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def verify_csrf_token(session_token: str, submitted_token: str) -> bool:
    """Validate submitted CSRF token against expected HMAC."""
    if not session_token or not submitted_token:
        return False
    expected = generate_csrf_token(session_token)
    return hmac.compare_digest(expected, submitted_token)

async def check_csrf(request: Request):
    """FastAPI dependency to enforce CSRF validation on state-changing requests."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for state-changing operations."
        )

    # Check form body or header
    submitted_token = None
    if "application/x-www-form-urlencoded" in request.headers.get("content-type", "") or \
       "multipart/form-data" in request.headers.get("content-type", ""):
        form = await request.form()
        submitted_token = form.get("csrf_token")
    
    if not submitted_token:
        submitted_token = request.headers.get("X-CSRF-Token")

    if not submitted_token or not verify_csrf_token(session_token, str(submitted_token)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF security token."
        )
