"""Append-only audit event service for high-impact actions."""
import json
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from app.models.entities import AuditEvent

def log_audit_event(
    db: Session,
    action: str,
    entity_name: str,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> AuditEvent:
    """Record an audit event while redacting credentials and sensitive fields."""
    safe_details = {}
    if details:
        for k, v in details.items():
            if any(secret_term in k.lower() for secret_term in ["pass", "token", "secret", "cookie", "key"]):
                safe_details[k] = "[REDACTED]"
            else:
                safe_details[k] = v

    event = AuditEvent(
        action=action,
        entity_name=entity_name,
        entity_id=entity_id,
        user_id=user_id,
        ip_address=ip_address,
        details_json=json.dumps(safe_details) if safe_details else None,
        created_at=datetime.now(timezone.utc)
    )
    db.add(event)
    db.commit()
    return event
