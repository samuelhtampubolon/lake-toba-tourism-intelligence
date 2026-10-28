"""Dashboard route handlers."""
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_helper import render_template
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User, Dataset, TourismObservation
from app.security.csrf import generate_csrf_token
from app.security.roles import get_current_user_optional
from app.services.analytics_service import get_time_series_aggregation, get_seasonality_explorer, get_destination_breakdown

router = APIRouter(tags=["Dashboard"])

@router.get("/", response_class=HTMLResponse)
def root(user: User = Depends(get_current_user_optional)):
    if not user:
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/dashboard")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    grain: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse(url="/login")

    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    # Get active or newest dataset
    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()

    if not dataset:
        return render_template(
            request,
            "dashboard.html",
            {
                "user": user,
                "csrf_token": csrf_token,
                "dataset": None,
                "active_page": "dashboard"
            }
        )

    # Calculate overall KPIs
    observations = db.query(TourismObservation).filter(
        TourismObservation.dataset_id == dataset.id,
        TourismObservation.grain == "daily"
    ).all()

    total_vis = sum(o.total_visitors for o in observations)
    dom_vis = sum(o.visitors_domestic for o in observations)
    intl_vis = sum(o.visitors_international for o in observations)
    tot_rev = sum(o.total_revenue_idr for o in observations)
    avg_occ = round(sum(o.hotel_occupancy_rate for o in observations) / max(1, len(observations)), 1)
    avg_adr = round(sum(o.avg_daily_rate_idr for o in observations) / max(1, len(observations)), 0)

    dom_pct = round((dom_vis / max(1, total_vis)) * 100.0, 1)
    intl_pct = round((intl_vis / max(1, total_vis)) * 100.0, 1)

    agg = get_time_series_aggregation(db, dataset.id, grain=grain)
    seasonality = get_seasonality_explorer(db, dataset.id)
    destinations = get_destination_breakdown(db, dataset.id)

    return render_template(
        request,
        "dashboard.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "dataset": dataset,
            "grain": grain,
            "total_visitors": total_vis,
            "domestic_pct": dom_pct,
            "intl_pct": intl_pct,
            "total_revenue": tot_rev,
            "avg_occupancy": avg_occ,
            "avg_adr": avg_adr,
            "series": agg["series"],
            "seasonality": seasonality,
            "destinations": destinations,
            "active_page": "dashboard"
        }
    )
