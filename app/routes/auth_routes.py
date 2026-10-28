"""Authentication routes: login, session rotation, and logout."""
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.templates_helper import render_template
from app.models.entities import User
from app.security.auth import verify_password, create_user_session, revoke_session
from app.security.csrf import generate_csrf_token, check_csrf
from app.security.roles import get_current_user_optional
from app.services.audit_service import log_audit_event

router = APIRouter(tags=["Authentication"])

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "anonymous")
    csrf_token = generate_csrf_token(session_cookie)
    return render_template(
        request,
        "login.html",
        {"user": None, "csrf_token": csrf_token, "error": None}
    )

@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username.strip(), User.is_active == True).first()
    
    if not user or not verify_password(password, user.password_hash):
        session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "anonymous")
        csrf_token = generate_csrf_token(session_cookie)
        return render_template(
            request,
            "login.html",
            {
                "user": None,
                "csrf_token": csrf_token,
                "error": "Invalid username or password credentials."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Rotate / create new session
    session_obj, raw_token = create_user_session(db, user)
    log_audit_event(
        db, action="LOGIN", entity_name="User", entity_id=user.id, user_id=user.id,
        ip_address=request.client.host if request.client else None
    )

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.SESSION_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE
    )
    return response

@router.post("/logout", dependencies=[Depends(check_csrf)])
def logout(request: Request, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if raw_token:
        revoke_session(db, raw_token)

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response
