"""Role-based access control (RBAC) and permission dependencies."""
from typing import List, Optional
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User
from app.security.auth import validate_session

ROLE_HIERARCHY = {
    "business_owner": ["business_owner", "tourism_analyst", "marketing_manager", "read_only_executive"],
    "tourism_analyst": ["tourism_analyst", "read_only_executive"],
    "marketing_manager": ["marketing_manager", "read_only_executive"],
    "read_only_executive": ["read_only_executive"]
}

PERMISSIONS = {
    "read_dashboard": ["business_owner", "tourism_analyst", "marketing_manager", "read_only_executive"],
    "import_data": ["business_owner", "tourism_analyst"],
    "delete_dataset": ["business_owner", "tourism_analyst"],
    "run_forecast": ["business_owner", "tourism_analyst"],
    "manage_scenarios": ["business_owner", "marketing_manager"],
    "export_reports": ["business_owner", "tourism_analyst", "marketing_manager", "read_only_executive"],
    "admin_actions": ["business_owner"]
}

def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieve currently authenticated user from session cookie without throwing."""
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token:
        return None
    return validate_session(db, session_token)

def get_current_user(
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Require valid authenticated user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource."
        )
    return user

def require_roles(allowed_roles: List[str]):
    """Dependency factory checking if current user has one of the allowed roles."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles and "business_owner" not in [user.role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required role in {allowed_roles}, your role is '{user.role}'."
            )
        return user
    return role_checker

def require_permission(permission_key: str):
    """Dependency checking a named permission key."""
    allowed = PERMISSIONS.get(permission_key, ["business_owner"])
    return require_roles(allowed)
