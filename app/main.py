"""FastAPI Application entrypoint with security headers, error handling, and router registration."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, BASE_DIR
from app.database import init_db, SessionLocal
from app.services.demo_data_service import seed_destinations_and_segments
from app.routes import (
    health_router,
    auth_router,
    dashboard_router,
    dataset_router,
    forecast_router,
    scenario_router,
    segment_router,
    report_router,
    admin_router,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("lake_toba")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize schema and baseline seed records."""
    logger.info("Initializing Lake Toba Tourism Intelligence SQLite schema...")
    init_db()
    with SessionLocal() as db:
        seed_destinations_and_segments(db)
    logger.info("Database schema and core reference destinations verified.")
    yield
    logger.info("Application shutting down cleanly.")

app = FastAPI(
    title="Lake Toba Tourism Intelligence",
    description="Local-first decision-support platform for tourism demand forecasting and scenario modeling.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        "object-src 'none'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
        "img-src 'self' data:; connect-src 'self';"
    )
    return response

# Global Exception Handler returning safe, non-leaking diagnostic responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing request to {request.url.path}: {exc}", exc_info=True)
    if "text/html" in request.headers.get("accept", ""):
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>System Error | Lake Toba Intelligence</title><style>
          body { background: #0a0f1d; color: #f9fafb; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
          .err-card { background: #111827; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 32px; max-width: 480px; text-align: center; }
          a { color: #38bdf8; text-decoration: none; }
        </style></head>
        <body>
          <div class="err-card">
            <h1 style="color: #f87171; font-size: 20px; margin-bottom: 8px;">An Unexpected System Error Occurred</h1>
            <p style="color: #9ca3af; font-size: 14px; margin-bottom: 20px;">The request could not be processed. Internal diagnostics have been safely logged.</p>
            <a href="/dashboard">&larr; Return to Dashboard</a>
          </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An internal server error occurred. Please contact the administrator."}
    )

# Static files
static_path = BASE_DIR / "app" / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Register Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(dataset_router)
app.include_router(forecast_router)
app.include_router(scenario_router)
app.include_router(segment_router)
app.include_router(report_router)
app.include_router(admin_router)
