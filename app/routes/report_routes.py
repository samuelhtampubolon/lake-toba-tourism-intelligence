"""Executive reporting and safe CSV export routes."""
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_helper import render_template
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User, Dataset, Report, TourismObservation
from app.security.csrf import generate_csrf_token, check_csrf
from app.security.roles import get_current_user, require_permission
from app.services.export_service import export_observations_to_safe_csv, create_report_record
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", response_class=HTMLResponse)
def reports_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()
    reports = db.query(Report).order_by(Report.created_at.desc()).all()

    return render_template(
        request,
        "reports.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "dataset": dataset,
            "reports": reports,
            "active_page": "reports"
        }
    )

@router.post("/generate", dependencies=[Depends(check_csrf)])
def generate_report_route(
    request: Request,
    title: str = Form(...),
    report_type: str = Form(...),
    analyst_notes: Optional[str] = Form(None),
    user: User = Depends(require_permission("export_reports")),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()
    v = dataset.version if dataset else 1

    summary = {"generated_by": user.username, "scope": "Lake Toba Regional Model"}
    rep = create_report_record(
        db=db,
        title=title,
        report_type=report_type,
        dataset_version=v,
        metrics_summary=summary,
        analyst_notes=analyst_notes,
        user_id=user.id
    )

    log_audit_event(
        db, action="EXPORT_REPORT", entity_name="Report", entity_id=rep.id, user_id=user.id,
        details={"title": title, "type": report_type}
    )

    return RedirectResponse(url="/reports", status_code=303)

@router.get("/export-csv")
def download_safe_csv(
    dataset_id: Optional[str] = None,
    user: User = Depends(require_permission("export_reports")),
    db: Session = Depends(get_db)
):
    target_id = dataset_id
    if not target_id:
        ds = db.query(Dataset).order_by(Dataset.created_at.desc()).first()
        if not ds:
            raise HTTPException(status_code=404, detail="No dataset available to export.")
        target_id = ds.id

    csv_content = export_observations_to_safe_csv(db, target_id)
    filename = f"lake_toba_observations_{target_id[:8]}.csv"

    log_audit_event(
        db, action="EXPORT_CSV", entity_name="Dataset", entity_id=target_id, user_id=user.id,
        details={"filename": filename}
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
