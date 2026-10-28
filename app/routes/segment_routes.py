"""Customer segmentation routes."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.templates_helper import render_template
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User, Dataset
from app.security.csrf import generate_csrf_token
from app.security.roles import get_current_user
from app.services.segment_service import get_customer_segments_analysis

router = APIRouter(prefix="/segments", tags=["Segments"])

@router.get("", response_class=HTMLResponse)
def segments_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    dataset = db.query(Dataset).order_by(Dataset.created_at.desc()).first()
    if not dataset:
        return render_template(
            request,
            "segments.html",
            {
                "user": user,
                "csrf_token": csrf_token,
                "seg_data": {"segments": [], "privacy_notice": "Load a dataset to view segmented profiles."},
                "active_page": "segments"
            }
        )

    seg_data = get_customer_segments_analysis(db, dataset.id)

    return render_template(
        request,
        "segments.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "seg_data": seg_data,
            "active_page": "segments"
        }
    )
