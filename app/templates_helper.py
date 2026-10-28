"""Template rendering helper ensuring consistent keyword argument binding for Starlette."""
from typing import Dict, Any, Optional
from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

def render_template(
    request: Request,
    name: str,
    context: Optional[Dict[str, Any]] = None,
    status_code: int = 200
):
    """Render Jinja2 template with explicit keyword arguments compatible with Starlette 0.38+."""
    ctx = context or {}
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=ctx,
        status_code=status_code
    )
