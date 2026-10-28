"""Scenario simulation and ROI calculator routes."""
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_helper import render_template
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User, Dataset, TourismObservation
from app.security.csrf import generate_csrf_token, check_csrf
from app.security.roles import get_current_user, require_permission
from app.services.scenario_service import simulate_scenario, create_and_save_scenario, list_scenarios
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

@router.get("", response_class=HTMLResponse)
def scenarios_view(
    request: Request,
    spend: float = 250000000.0,
    price_pct: float = 5.0,
    season_mult: float = 1.15,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()

    base_vis = 10000
    base_rev = 5000000000.0
    if dataset:
        obs = db.query(TourismObservation).filter(
            TourismObservation.dataset_id == dataset.id,
            TourismObservation.grain == "daily"
        ).all()
        base_vis = sum(o.total_visitors for o in obs) or base_vis
        base_rev = sum(o.total_revenue_idr for o in obs) or base_rev

    sim = simulate_scenario(
        base_visitors=base_vis,
        base_revenue=base_rev,
        marketing_spend_idr=spend,
        price_change_pct=price_pct,
        seasonality_multiplier=season_mult
    )

    saved = list_scenarios(db, dataset.id if dataset else None)

    return render_template(
        request,
        "scenarios.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "dataset": dataset,
            "sim": sim,
            "saved_scenarios": saved,
            "active_page": "scenarios"
        }
    )

@router.post("/save", dependencies=[Depends(check_csrf)])
def save_scenario_route(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    marketing_spend_idr: float = Form(...),
    price_change_pct: float = Form(...),
    seasonality_multiplier: float = Form(...),
    user: User = Depends(require_permission("manage_scenarios")),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()
    if not dataset:
        return RedirectResponse(url="/scenarios", status_code=303)

    sc = create_and_save_scenario(
        db=db,
        dataset_id=dataset.id,
        name=name,
        description=description,
        marketing_spend_idr=marketing_spend_idr,
        price_change_pct=price_change_pct,
        seasonality_multiplier=seasonality_multiplier
    )

    log_audit_event(
        db, action="SCENARIO_SAVE", entity_name="Scenario", entity_id=sc.id, user_id=user.id,
        details={"name": sc.name, "roi": sc.roi_percentage, "spend": marketing_spend_idr}
    )

    return RedirectResponse(url="/scenarios", status_code=303)
