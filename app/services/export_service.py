"""Safe CSV export with CSV formula-injection defense and report generation."""
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import TourismObservation, Destination, Report

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

def sanitize_csv_value(value: Any) -> str:
    """Neutralize formula injection triggers by prefixing dangerous leading characters with a single quote."""
    if value is None:
        return ""
    str_val = str(value)
    if str_val.startswith(FORMULA_PREFIXES):
        return f"'{str_val}"
    return str_val

def export_observations_to_safe_csv(
    db: Session,
    dataset_id: str,
    destination_id: Optional[str] = None
) -> str:
    """Export allowlisted observation columns into a CSV formula-safe string."""
    query = db.query(
        TourismObservation, Destination.name.label("destination_name"), Destination.code.label("destination_code")
    ).join(
        Destination, TourismObservation.destination_id == Destination.id
    ).filter(
        TourismObservation.dataset_id == dataset_id
    )

    if destination_id:
        query = query.filter(TourismObservation.destination_id == destination_id)

    records = query.order_by(TourismObservation.date.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Allowlisted header
    headers = [
        "date", "destination_code", "destination_name", "grain",
        "visitors_domestic", "visitors_international", "total_visitors",
        "hotel_occupancy_rate", "avg_daily_rate_idr", "total_revenue_idr"
    ]
    writer.writerow(headers)

    for obs, dest_name, dest_code in records:
        row = [
            sanitize_csv_value(obs.date),
            sanitize_csv_value(dest_code),
            sanitize_csv_value(dest_name),
            sanitize_csv_value(obs.grain),
            sanitize_csv_value(obs.visitors_domestic),
            sanitize_csv_value(obs.visitors_international),
            sanitize_csv_value(obs.total_visitors),
            sanitize_csv_value(obs.hotel_occupancy_rate),
            sanitize_csv_value(obs.avg_daily_rate_idr),
            sanitize_csv_value(obs.total_revenue_idr)
        ]
        writer.writerow(row)

    return output.getvalue()

def create_report_record(
    db: Session,
    title: str,
    report_type: str,
    dataset_version: int,
    metrics_summary: Dict[str, Any],
    analyst_notes: Optional[str],
    user_id: Optional[str] = None
) -> Report:
    """Persist generated report with provenance and audit metadata."""
    import json
    report = Report(
        title=title,
        report_type=report_type,
        dataset_version=dataset_version,
        metrics_json=json.dumps(metrics_summary),
        analyst_notes=analyst_notes,
        created_by_user_id=user_id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
