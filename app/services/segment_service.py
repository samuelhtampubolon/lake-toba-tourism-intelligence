"""Customer segmentation service with standardized travel metrics and revenue attribution."""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.entities import CustomerSegment, TourismObservation

def get_customer_segments_analysis(db: Session, dataset_id: str) -> Dict[str, Any]:
    """Calculate customer segments behavior and estimated regional economic contribution."""
    segments = db.query(CustomerSegment).filter(CustomerSegment.is_active == True).all()
    
    # Calculate total regional revenue from dataset
    observations = db.query(TourismObservation).filter(
        TourismObservation.dataset_id == dataset_id,
        TourismObservation.grain == "daily"
    ).all()

    total_revenue = sum(o.total_revenue_idr for o in observations) or 1.0
    total_visitors = sum(o.total_visitors for o in observations) or 1

    # Typical regional distribution weights across segments
    segment_weights = {
        "DOM_WEEKEND": {"vis_share": 0.52, "spend_weight": 0.85},
        "CULT_HERITAGE": {"vis_share": 0.22, "spend_weight": 1.15},
        "INTL_ADVENTURE": {"vis_share": 0.16, "spend_weight": 0.72},
        "MICE_EVENTS": {"vis_share": 0.10, "spend_weight": 2.45},
    }

    results = []
    for seg in segments:
        cfg = segment_weights.get(seg.code, {"vis_share": 0.25, "spend_weight": 1.0})
        est_visitors = int(total_visitors * cfg["vis_share"])
        est_revenue = total_revenue * (cfg["vis_share"] * cfg["spend_weight"])
        
        results.append({
            "segment_id": seg.id,
            "code": seg.code,
            "name": seg.name,
            "description": seg.description,
            "travel_party_size": seg.travel_party_size,
            "avg_stay_days": seg.avg_stay_days,
            "avg_spend_per_day_idr": seg.avg_spend_per_day_idr,
            "preference_tags": [t.strip() for t in (seg.preference_tags or "").split(",") if t.strip()],
            "estimated_visitor_volume": est_visitors,
            "visitor_share_percentage": round(cfg["vis_share"] * 100.0, 1),
            "estimated_revenue_idr": round(est_revenue, 2),
            "revenue_share_percentage": round((est_revenue / total_revenue) * 100.0, 1),
        })

    # Sort by revenue contribution descending
    results.sort(key=lambda x: x["estimated_revenue_idr"], reverse=True)

    return {
        "dataset_id": dataset_id,
        "total_regional_visitors": total_visitors,
        "total_regional_revenue_idr": round(total_revenue, 2),
        "segments": results,
        "privacy_notice": "Customer segments are modeled purely on observable travel dynamics (stay duration, group size, seasonal distribution) and do not contain, process, or proxy protected personal demographic attributes."
    }
