"""Routes package."""
from app.routes.health_routes import router as health_router
from app.routes.auth_routes import router as auth_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.dataset_routes import router as dataset_router
from app.routes.forecast_routes import router as forecast_router
from app.routes.scenario_routes import router as scenario_router
from app.routes.segment_routes import router as segment_router
from app.routes.report_routes import router as report_router
from app.routes.admin_routes import router as admin_router
