"""Data quality profiler: null counts, date gaps, duplicate keys, and bounds checks."""
from datetime import timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.entities import TourismObservation, Destination

def profile_dataset_quality(db: Session, dataset_id: str) -> Dict[str, Any]:
    """Execute data quality checks and return comprehensive diagnostic summary."""
    observations = db.query(TourismObservation).filter(
        TourismObservation.dataset_id == dataset_id,
        TourismObservation.grain == "daily"
    ).order_by(TourismObservation.date.asc()).all()

    total_records = len(observations)
    if total_records == 0:
        return {
            "total_records": 0,
            "null_counts": {},
            "duplicate_keys": 0,
            "negative_values": 0,
            "impossible_occupancy": 0,
            "date_gaps": [],
            "coverage_percentage": 0.0,
            "earliest_date": None,
            "latest_date": None,
            "status": "EMPTY"
        }

    # Aggregate metrics
    null_counts = {
        "visitors_domestic": 0,
        "visitors_international": 0,
        "hotel_occupancy_rate": 0,
        "avg_daily_rate_idr": 0,
        "total_revenue_idr": 0
    }
    duplicate_keys = 0
    negative_values = 0
    impossible_occupancy = 0
    seen_keys = set()
    dates_by_dest: Dict[str, List] = {}

    for obs in observations:
        key = (obs.destination_id, obs.date)
        if key in seen_keys:
            duplicate_keys += 1
        seen_keys.add(key)

        if obs.destination_id not in dates_by_dest:
            dates_by_dest[obs.destination_id] = []
        dates_by_dest[obs.destination_id].append(obs.date)

        if obs.visitors_domestic is None: null_counts["visitors_domestic"] += 1
        elif obs.visitors_domestic < 0: negative_values += 1

        if obs.visitors_international is None: null_counts["visitors_international"] += 1
        elif obs.visitors_international < 0: negative_values += 1

        if obs.hotel_occupancy_rate is None: null_counts["hotel_occupancy_rate"] += 1
        elif obs.hotel_occupancy_rate < 0 or obs.hotel_occupancy_rate > 100.0:
            impossible_occupancy += 1

        if obs.avg_daily_rate_idr is None: null_counts["avg_daily_rate_idr"] += 1
        elif obs.avg_daily_rate_idr < 0: negative_values += 1

        if obs.total_revenue_idr is None: null_counts["total_revenue_idr"] += 1
        elif obs.total_revenue_idr < 0: negative_values += 1

    # Date gap analysis across destinations
    all_dates = sorted(list({obs.date for obs in observations}))
    earliest_date = all_dates[0]
    latest_date = all_dates[-1]
    expected_days = (latest_date - earliest_date).days + 1
    actual_days = len(all_dates)
    
    date_gaps = []
    for i in range(len(all_dates) - 1):
        diff = (all_dates[i+1] - all_dates[i]).days
        if diff > 1:
            date_gaps.append({
                "gap_start": str(all_dates[i] + timedelta(days=1)),
                "gap_end": str(all_dates[i+1] - timedelta(days=1)),
                "missing_days": diff - 1
            })

    coverage_pct = round((actual_days / max(expected_days, 1)) * 100.0, 2)
    quality_status = "EXCELLENT" if (negative_values == 0 and duplicate_keys == 0 and coverage_pct >= 95.0) else "WARNINGS_DETECTED"

    return {
        "total_records": total_records,
        "null_counts": null_counts,
        "duplicate_keys": duplicate_keys,
        "negative_values": negative_values,
        "impossible_occupancy": impossible_occupancy,
        "date_gaps": date_gaps[:10], # Top 10 gaps
        "total_gaps_count": len(date_gaps),
        "coverage_percentage": coverage_pct,
        "earliest_date": str(earliest_date),
        "latest_date": str(latest_date),
        "expected_days": expected_days,
        "actual_days": actual_days,
        "status": quality_status
    }
