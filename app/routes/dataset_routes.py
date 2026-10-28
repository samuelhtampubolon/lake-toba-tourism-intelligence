"""Dataset management and CSV ingestion routes."""
from typing import Optional
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_helper import render_template
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User
from app.security.csrf import generate_csrf_token, check_csrf
from app.security.roles import get_current_user, require_permission
from app.services.dataset_service import list_datasets, get_dataset_by_id, delete_dataset
from app.services.quality_service import profile_dataset_quality
from app.services.ingestion_service import preview_csv_content, commit_csv_import
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/datasets", tags=["Datasets"])

# Temporary cache for previewed file bytes awaiting commit
_PREVIEW_STORE = {}

@router.get("", response_class=HTMLResponse)
def datasets_list_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)
    all_datasets = list_datasets(db)

    return render_template(
        request,
        "datasets.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "datasets": all_datasets,
            "active_page": "datasets"
        }
    )

@router.get("/upload", response_class=HTMLResponse)
def upload_view(
    request: Request,
    user: User = Depends(require_permission("import_data"))
):
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    return render_template(
        request,
        "upload.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "preview": None,
            "active_page": "datasets"
        }
    )

@router.post("/upload", response_class=HTMLResponse, dependencies=[Depends(check_csrf)])
async def upload_csv_file(
    request: Request,
    csv_file: UploadFile = File(...),
    user: User = Depends(require_permission("import_data"))
):
    file_bytes = await csv_file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size ({settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB)."
        )

    preview_res = preview_csv_content(file_bytes, csv_file.filename)
    if not preview_res["success"]:
        session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
        csrf_token = generate_csrf_token(session_cookie)
        return render_template(
            request,
            "upload.html",
            {
                "user": user,
                "csrf_token": csrf_token,
                "preview": None,
                "flash_message": preview_res["error"],
                "flash_type": "danger",
                "active_page": "datasets"
            }
        )

    # Store bytes in preview store keyed by hash
    _PREVIEW_STORE[preview_res["file_hash_sha256"]] = {
        "bytes": file_bytes,
        "filename": csv_file.filename
    }

    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    return render_template(
        request,
        "upload.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "preview": preview_res,
            "active_page": "datasets"
        }
    )

@router.post("/commit", dependencies=[Depends(check_csrf)])
def commit_import(
    request: Request,
    file_hash: str = Form(...),
    dataset_name: str = Form(...),
    provenance_source: str = Form(...),
    source_url: Optional[str] = Form(None),
    user: User = Depends(require_permission("import_data")),
    db: Session = Depends(get_db)
):
    stored = _PREVIEW_STORE.pop(file_hash, None)
    if not stored:
        return RedirectResponse(url="/datasets/upload", status_code=status.HTTP_303_SEE_OTHER)

    # Default mapping
    default_mapping = {
        "date": "date",
        "destination_code": "destination_code",
        "visitors_domestic": "visitors_domestic",
        "visitors_international": "visitors_international",
        "hotel_occupancy_rate": "hotel_occupancy_rate",
        "avg_daily_rate_idr": "avg_daily_rate_idr",
        "total_revenue_idr": "total_revenue_idr"
    }

    ok, msg, dataset = commit_csv_import(
        db=db,
        file_bytes=stored["bytes"],
        file_name=stored["filename"],
        dataset_name=dataset_name,
        provenance_source=provenance_source,
        source_url=source_url,
        column_mapping=default_mapping
    )

    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    log_audit_event(
        db, action="DATASET_IMPORT", entity_name="Dataset", entity_id=dataset.id, user_id=user.id,
        details={"name": dataset.name, "rows": dataset.row_count}
    )

    return RedirectResponse(url="/datasets", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{dataset_id}/quality", response_class=HTMLResponse)
def quality_profile_view(
    dataset_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dataset = get_dataset_by_id(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    profile = profile_dataset_quality(db, dataset_id)
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    csrf_token = generate_csrf_token(session_cookie)

    return render_template(
        request,
        "quality.html",
        {
            "user": user,
            "csrf_token": csrf_token,
            "dataset": dataset,
            "profile": profile,
            "active_page": "datasets"
        }
    )

@router.post("/{dataset_id}/delete", dependencies=[Depends(check_csrf)])
def delete_dataset_route(
    dataset_id: str,
    request: Request,
    user: User = Depends(require_permission("delete_dataset")),
    db: Session = Depends(get_db)
):
    dataset = get_dataset_by_id(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    ds_name = dataset.name
    delete_dataset(db, dataset_id)
    log_audit_event(
        db, action="DATASET_DELETE", entity_name="Dataset", entity_id=dataset_id, user_id=user.id,
        details={"deleted_name": ds_name}
    )

    return RedirectResponse(url="/datasets", status_code=status.HTTP_303_SEE_OTHER)
