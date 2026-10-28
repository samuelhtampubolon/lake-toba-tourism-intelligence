"""Time-series aggregation, seasonality analysis, and destination comparisons."""
from datetime import date
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.entities import TourismObservation, Destination
from app.services.dataset_service import get_cache_key, get_cached_aggregation, set_cached_aggregation

def get_time_series_aggregation(
    db: Session,
    dataset_id: str,
    grain: str = "daily",
    destination_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """Aggregate visitor volume, hotel occupancy, ADR, and revenue by requested grain."""
    cache_key = get_cache_key(dataset_id, grain, str(start_date), str(end_date), destination_id)
    cached = get_cached_aggregation(cache_key)
    if cached:
        return cached

    query = db.query(
        TourismObservation, Destination.name.label("destination_name"), Destination.code.label("destination_code")
    ).join(
        Destination, TourismObservation.destination_id == Destination.id
    ).filter(
        TourismObservation.dataset_id == dataset_id,
        TourismObservation.grain == "daily"
    )

    if destination_id:
        query = query.filter(TourismObservation.destination_id == destination_id)
    if start_date:
        query = query.filter(TourismObservation.date >= start_date)
    if end_date:
        query = query.filter(TourismObservation.date <= end_date)

    records = query.order_by(TourismObservation.date.asc()).all()

    if grain == "daily":
        points_map = defaultdict(lambda: {
            "domestic": 0, "international": 0, "total": 0, "revenue": 0.0, "occ_sum": 0.0, "adr_sum": 0.0, "count": 0
        })
        for obs, _, _ in records:
            key = str(obs.date)
            p = points_map[key]
            p["domestic"] += obs.visitors_domestic
            p["international"] += obs.visitors_international
            p["total"] += obs.total_visitors
            p["revenue"] += obs.total_revenue_idr
            p["occ_sum"] += obs.hotel_occupancy_rate
            p["adr_sum"] += obs.avg_daily_rate_idr
            p["count"] += 1

        series = []
        for d_str in sorted(points_map.keys()):
            p = points_map[d_str]
            cnt = max(1, p["count"])
            series.append({
                "period": d_str,
                "visitors_domestic": p["domestic"],
                "visitors_international": p["international"],
                "total_visitors": p["total"],
                "total_revenue_idr": round(p["revenue"], 2),
                "avg_occupancy_rate": round(p["occ_sum"] / cnt, 2),
                "avg_daily_rate_idr": round(p["adr_sum"] / cnt, 2),
            })

    elif grain == "weekly":
        # Group by YYYY-Www
        points_map = defaultdict(lambda: {
            "domestic": 0, "international": 0, "total": 0, "revenue": 0.0, "occ_sum": 0.0, "adr_sum": 0.0, "count": 0
        })
        for obs, _, _ in records:
            iso_year, iso_week, _ = obs.date.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
            p = points_map[key]
            p["domestic"] += obs.visitors_domestic
            p["international"] += obs.visitors_international
            p["total"] += obs.total_visitors
            p["revenue"] += obs.total_revenue_idr
            p["occ_sum"] += obs.hotel_occupancy_rate
            p["adr_sum"] += obs.avg_daily_rate_idr
            p["count"] += 1

        series = []
        for w_str in sorted(points_map.keys()):
            p = points_map[w_str]
            cnt = max(1, p["count"])
            series.append({
                "period": w_str,
                "visitors_domestic": p["domestic"],
                "visitors_international": p["international"],
                "total_visitors": p["total"],
                "total_revenue_idr": round(p["revenue"], 2),
                "avg_occupancy_rate": round(p["occ_sum"] / cnt, 2),
                "avg_daily_rate_idr": round(p["adr_sum"] / cnt, 2),
            })

    else: # monthly
        points_map = defaultdict(lambda: {
            "domestic": 0, "international": 0, "total": 0, "revenue": 0.0, "occ_sum": 0.0, "adr_sum": 0.0, "count": 0
        })
        for obs, _, _ in records:
            key = obs.date.strftime("%Y-%m")
            p = points_map[key]
            p["domestic"] += obs.visitors_domestic
            p["international"] += obs.visitors_international
            p["total"] += obs.total_visitors
            p["revenue"] += obs.total_revenue_idr
            p["occ_sum"] += obs.hotel_occupancy_rate
            p["adr_sum"] += obs.avg_daily_rate_idr
            p["count"] += 1

        series = []
        for m_str in sorted(points_map.keys()):
            p = points_map[m_str]
            cnt = max(1, p["count"])
            series.append({
                "period": m_str,
                "visitors_domestic": p["domestic"],
                "visitors_international": p["international"],
                "total_visitors": p["total"],
                "total_revenue_idr": round(p["revenue"], 2),
                "avg_occupancy_rate": round(p["occ_sum"] / cnt, 2),
                "avg_daily_rate_idr": round(p["adr_sum"] / cnt, 2),
            })

    result = {
        "dataset_id": dataset_id,
        "grain": grain,
        "total_periods": len(series),
        "series": series
    }
    set_cached_aggregation(cache_key, result)
    return result

def get_seasonality_explorer(db: Session, dataset_id: str) -> Dict[str, Any]:
    """Calculate monthly and weekday seasonality indices across observations."""
    observations = db.query(TourismObservation).filter(
        TourismObservation.dataset_id == dataset_id,
        TourismObservation.grain == "daily"
    ).all()

    month_buckets = defaultdict(lambda: {"total_visitors": 0, "revenue": 0.0, "count": 0})
    weekday_buckets = defaultdict(lambda: {"total_visitors": 0, "revenue": 0.0, "count": 0})

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for obs in observations:
        m_idx = obs.date.month - 1
        w_idx = obs.date.weekday()

        mb = month_buckets[m_idx]
        mb["total_visitors"] += obs.total_visitors
        mb["revenue"] += obs.total_revenue_idr
        mb["count"] += 1

        wb = weekday_buckets[w_idx]
        wb["total_visitors"] += obs.total_visitors
        wb["revenue"] += obs.total_revenue_idr
        wb["count"] += 1

    monthly_summary = []
    for m in range(12):
        mb = month_buckets[m]
        cnt = max(1, mb["count"])
        monthly_summary.append({
            "month_number": m + 1,
            "month_name": month_names[m],
            "avg_daily_visitors": round(mb["total_visitors"] / cnt, 1),
            "avg_daily_revenue_idr": round(mb["revenue"] / cnt, 2),
            "sample_days": mb["count"]
        })

    weekday_summary = []
    weekend_vol = 0
    weekend_days = 0
    weekday_vol = 0
    weekday_days = 0

    for w in range(7):
        wb = weekday_buckets[w]
        cnt = max(1, wb["count"])
        avg_vis = round(wb["total_visitors"] / cnt, 1)
        weekday_summary.append({
            "weekday_number": w,
            "weekday_name": weekday_names[w],
            "avg_visitors": avg_vis,
            "sample_days": wb["count"]
        })
        if w in (4, 5, 6): # Fri, Sat, Sun
            weekend_vol += wb["total_visitors"]
            weekend_days += wb["count"]
        else:
            weekday_vol += wb["total_visitors"]
            weekday_days += wb["count"]

    avg_weekend = (weekend_vol / max(1, weekend_days))
    avg_weekday = (weekday_vol / max(1, weekday_days))
    ratio = round(avg_weekend / max(1.0, avg_weekday), 2)

    return {
        "monthly": monthly_summary,
        "weekday": weekday_summary,
        "weekend_to_weekday_ratio": ratio,
        "explanation": f"Weekend days average {ratio}x the visitor volume of weekday days across Lake Toba destinations."
    }

def get_destination_breakdown(db: Session, dataset_id: str) -> List[Dict[str, Any]]:
    """Compare performance metrics across all Lake Toba destinations."""
    destinations = db.query(Destination).all()
    results = []

    for d in destinations:
        obs = db.query(TourismObservation).filter(
            TourismObservation.dataset_id == dataset_id,
            TourismObservation.destination_id == d.id
        ).all()
        if not obs:
            continue

        tot_vis = sum(o.total_visitors for o in obs)
        dom_vis = sum(o.visitors_domestic for o in obs)
        intl_vis = sum(o.visitors_international for o in obs)
        tot_rev = sum(o.total_revenue_idr for o in obs)
        avg_occ = round(sum(o.hotel_occupancy_rate for o in obs) / max(1, len(obs)), 2)
        avg_adr = round(sum(o.avg_daily_rate_idr for o in obs) / max(1, len(obs)), 2)

        results.append({
            "destination_id": d.id,
            "code": d.code,
            "name": d.name,
            "regency": d.regency,
            "category": d.category,
            "total_visitors": tot_vis,
            "domestic_visitors": dom_vis,
            "international_visitors": intl_vis,
            "intl_percentage": round((intl_vis / max(1, tot_vis)) * 100.0, 1),
            "total_revenue_idr": round(tot_rev, 2),
            "avg_occupancy_rate": avg_occ,
            "avg_daily_rate_idr": avg_adr
        })

    return sorted(results, key=lambda x: x["total_visitors"], reverse=True)
