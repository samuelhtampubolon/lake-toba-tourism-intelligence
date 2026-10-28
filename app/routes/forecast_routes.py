"""Forecasting routes."""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from app.templates_helper import render_template
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User, Dataset
from app.security.csrf import generate_csrf_token, check_csrf
from app.security.roles import get_current_user, require_permission
from app.services.forecast_service import execute_forecast_analysis
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/forecasts", tags=["Forecasting"])

@router.get("", response_class=HTMLResponse)
def forecast_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()

    return render_template(
        request,
        "forecast.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "dataset": dataset,
            "target_metric": "total_visitors",
            "horizon_days": 30,
            "forecast_result": None,
            "active_page": "forecasts"
        }
    )

@router.post("/run", response_class=HTMLResponse, dependencies=[Depends(check_csrf)])
def run_forecast_route(
    request: Request,
    target_metric: str = Form("total_visitors"),
    horizon_days: int = Form(30),
    user: User = Depends(require_permission("run_forecast")),
    db: Session = Depends(get_db)
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()
    if not dataset:
        return render_template(
            request,
            "forecast.html",
            {
                "user": user,
                "csrf_token": csrf_token,
                "dataset": None,
                "target_metric": target_metric,
                "horizon_days": horizon_days,
                "forecast_result": {"success": False, "error": "No dataset found. Please load or import a dataset first."},
                "active_page": "forecasts"
            }
        )

    result = execute_forecast_analysis(
        db, dataset_id=dataset.id, target_metric=target_metric, horizon_days=horizon_days
    )

    if result["success"]:
        log_audit_event(
            db, action="FORECAST_RUN", entity_name="ForecastRun", entity_id=result.get("run_id"),
            user_id=user.id, details={"target": target_metric, "horizon": horizon_days, "model_won": result.get("model_won")}
        )

    return render_template(
        request,
        "forecast.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "dataset": dataset,
            "target_metric": target_metric,
            "horizon_days": horizon_days,
            "forecast_result": result,
            "active_page": "forecasts"
        }
    )
