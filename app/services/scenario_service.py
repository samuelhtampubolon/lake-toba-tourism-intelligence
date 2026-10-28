"""Scenario assumptions and budget/pricing simulation service."""
import math
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import Scenario, ScenarioAssumption, TourismObservation, Dataset

def simulate_scenario(
    base_visitors: int,
    base_revenue: float,
    marketing_spend_idr: float,
    price_change_pct: float = 0.0,
    seasonality_multiplier: float = 1.0,
    spend_elasticity: float = 0.18,
    price_elasticity: float = 0.65
) -> Dict[str, Any]:
    """Execute mathematical simulation of marketing and pricing adjustments.
    
    All figures are simulated estimates, not observed causal claims.
    """
    safe_spend = max(0.0, float(marketing_spend_idr))
    safe_price_pct = float(price_change_pct) / 100.0
    safe_season_mult = max(0.1, float(seasonality_multiplier))

    # Logarithmic response curve for diminishing returns on marketing spend
    # Normalization scale S0 = 100,000,000 IDR (approx 100M IDR baseline campaign scale)
    s0 = 100_000_000.0
    spend_uplift = math.log1p(safe_spend / s0) * spend_elasticity if safe_spend > 0 else 0.0

    # Price elasticity of demand (negative impact of price increase on volume)
    price_volume_factor = max(0.2, 1.0 - (safe_price_pct * price_elasticity))

    # Combined simulated visitor volume
    simulated_visitors = int(base_visitors * (1.0 + spend_uplift) * price_volume_factor * safe_season_mult)

    # Base average revenue per visitor
    avg_rev_per_visitor = (base_revenue / max(1, base_visitors))
    adjusted_rev_per_visitor = avg_rev_per_visitor * (1.0 + safe_price_pct)

    simulated_revenue = round(simulated_visitors * adjusted_rev_per_visitor, 2)
    revenue_delta = simulated_revenue - base_revenue
    gross_contribution = round(revenue_delta - safe_spend, 2)

    # Safe ROI calculation with zero-denominator handling
    if safe_spend > 0.0:
        roi_percentage = round((gross_contribution / safe_spend) * 100.0, 2)
    else:
        roi_percentage = 0.0

    return {
        "base_visitors": base_visitors,
        "base_revenue_idr": round(base_revenue, 2),
        "marketing_spend_idr": safe_spend,
        "price_change_percentage": price_change_pct,
        "seasonality_multiplier": safe_season_mult,
        "simulated_visitors": simulated_visitors,
        "visitor_delta": simulated_visitors - base_visitors,
        "simulated_revenue_idr": simulated_revenue,
        "revenue_delta_idr": round(revenue_delta, 2),
        "gross_contribution_idr": gross_contribution,
        "roi_percentage": roi_percentage,
        "disclaimer": "Simulated estimates are based on parameter response curves and do not represent guaranteed or observed causal effects."
    }

def create_and_save_scenario(
    db: Session,
    dataset_id: str,
    name: str,
    description: Optional[str],
    marketing_spend_idr: float,
    price_change_pct: float,
    seasonality_multiplier: float
) -> Scenario:
    """Run simulation against dataset baseline and persist scenario with assumptions."""
    # Compute baseline from dataset observations
    observations = db.query(TourismObservation).filter(
        TourismObservation.dataset_id == dataset_id,
        TourismObservation.grain == "daily"
    ).all()

    base_visitors = sum(o.total_visitors for o in observations) or 10000
    base_revenue = sum(o.total_revenue_idr for o in observations) or 5_000_000_000.0

    sim_result = simulate_scenario(
        base_visitors=base_visitors,
        base_revenue=base_revenue,
        marketing_spend_idr=marketing_spend_idr,
        price_change_pct=price_change_pct,
        seasonality_multiplier=seasonality_multiplier
    )

    scenario = Scenario(
        name=name,
        description=description,
        dataset_id=dataset_id,
        baseline_revenue_idr=sim_result["base_revenue_idr"],
        simulated_revenue_idr=sim_result["simulated_revenue_idr"],
        total_marketing_spend_idr=sim_result["marketing_spend_idr"],
        gross_contribution_idr=sim_result["gross_contribution_idr"],
        roi_percentage=sim_result["roi_percentage"],
        is_archived=False
    )
    db.add(scenario)
    db.flush()

    # Save assumptions
    assumptions = [
        ScenarioAssumption(scenario_id=scenario.id, assumption_key="marketing_spend_idr", assumption_value=marketing_spend_idr, unit="IDR", note="Incremental campaign budget"),
        ScenarioAssumption(scenario_id=scenario.id, assumption_key="price_change_pct", assumption_value=price_change_pct, unit="%", note="Average room and tour ticket price adjustment"),
        ScenarioAssumption(scenario_id=scenario.id, assumption_key="seasonality_multiplier", assumption_value=seasonality_multiplier, unit="multiplier", note="Event/season demand adjustment factor"),
        ScenarioAssumption(scenario_id=scenario.id, assumption_key="spend_elasticity", assumption_value=0.18, unit="coefficient", note="Logarithmic visitor response elasticity"),
        ScenarioAssumption(scenario_id=scenario.id, assumption_key="price_elasticity", assumption_value=0.65, unit="coefficient", note="Price sensitivity coefficient")
    ]
    db.bulk_save_objects(assumptions)
    db.commit()
    db.refresh(scenario)
    return scenario

def list_scenarios(db: Session, dataset_id: Optional[str] = None) -> List[Scenario]:
    """Retrieve non-archived scenarios."""
    query = db.query(Scenario).filter(Scenario.is_archived == False)
    if dataset_id:
        query = query.filter(Scenario.dataset_id == dataset_id)
    return query.order_by(Scenario.created_at.desc()).all()
