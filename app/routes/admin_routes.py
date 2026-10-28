"""Administrative and system operation routes."""
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_helper import render_template
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db, backup_sqlite_database
from app.models.entities import User, AuditEvent
from app.security.csrf import generate_csrf_token, check_csrf
from app.security.roles import require_roles
from app.services.demo_data_service import generate_lake_toba_demo_dataset
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_view(
    request: Request,
    user: User = Depends(require_roles(["business_owner"])),
    db: Session = Depends(get_db)
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100).all()

    return render_template(
        request,
        "audit.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "audit_events": events,
            "active_page": "audit"
        }
    )

@router.post("/seed-demo", dependencies=[Depends(check_csrf)])
def seed_demo_route(
    request: Request,
    user: User = Depends(require_roles(["business_owner", "tourism_analyst"])),
    db: Session = Depends(get_db)
):
    dataset = generate_lake_toba_demo_dataset(db, seed=42)
    log_audit_event(
        db, action="SEED_DEMO_DATA", entity_name="Dataset", entity_id=dataset.id, user_id=user.id,
        details={"name": dataset.name, "rows": dataset.row_count}
    )
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/backup", dependencies=[Depends(check_csrf)])
def trigger_backup(
    user: User = Depends(require_roles(["business_owner"])),
    db: Session = Depends(get_db)
):
    backup_dir = settings.data_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_path = str(backup_dir / f"lake_toba_backup_{timestamp}.sqlite")

    backup_sqlite_database(dest_path)
    log_audit_event(
        db, action="DATABASE_BACKUP", entity_name="Database", entity_id=None, user_id=user.id,
        details={"path": dest_path}
    )

    return RedirectResponse(url="/dashboard", status_code=303)
