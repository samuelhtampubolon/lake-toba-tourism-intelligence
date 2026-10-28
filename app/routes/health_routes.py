"""Health and readiness probes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(tags=["Health"])

@router.get("/health/live")
def health_live():
    """Liveness probe: verifies process is responding."""
    return {"status": "alive", "service": "lake-toba-tourism-intelligence"}

@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    """Readiness probe: verifies database connectivity without leaking internal state."""
    try:
        db.execute(text("SELECT 1;"))
        return {
            "status": "ready",
            "database": "connected",
            "service": "lake-toba-tourism-intelligence"
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connectivity check failed."
        )
