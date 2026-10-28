"""Forecasting engine with Seasonal-Naive baseline, Damped Trend model, chronological splits, and MASE evaluation."""
import math
from datetime import timedelta, date
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.models.entities import TourismObservation, ForecastRun, ForecastPoint

def calculate_mae(actuals: List[float], predicted: List[float]) -> float:
    """Mean Absolute Error."""
    if not actuals or len(actuals) != len(predicted):
        return 0.0
    return sum(abs(a - p) for a, p in zip(actuals, predicted)) / len(actuals)

def calculate_in_sample_naive_mae(series: List[float], period: int = 7) -> float:
    """Calculate in-sample seasonal naive MAE for MASE denominator."""
    if len(series) <= period:
        return 1.0
    diffs = [abs(series[t] - series[t - period]) for t in range(period, len(series))]
    denom = sum(diffs) / max(1, len(diffs))
    return denom if denom > 0 else 1.0

def run_seasonal_naive_forecast(
    historical_values: List[float],
    horizon: int,
    period: int = 7
) -> List[float]:
    """Seasonal-Naive baseline: repeat the values from the corresponding seasonal cycle."""
    predictions = []
    n = len(historical_values)
    for h in range(horizon):
        # Look back to the corresponding point in the latest completed cycle
        offset = (h % period)
        source_idx = n - period + offset
        if source_idx >= 0 and source_idx < n:
            val = historical_values[source_idx]
        else:
            val = historical_values[-1]
        predictions.append(max(0.0, float(val)))
    return predictions

def run_damped_trend_forecast(
    historical_values: List[float],
    horizon: int,
    alpha: float = 0.35,
    beta: float = 0.15,
    phi: float = 0.90,
    period: int = 7
) -> List[float]:
    """Lightweight Holt-Winters style Damped Trend with additive seasonality."""
    n = len(historical_values)
    if n < period * 2:
        return run_seasonal_naive_forecast(historical_values, horizon, period)

    # Initialize level, trend, and seasonal components
    level = sum(historical_values[:period]) / period
    trend = (sum(historical_values[period:2*period]) - sum(historical_values[:period])) / (period ** 2)
    seasonals = [historical_values[i] - level for i in range(period)]

    # Update through history
    for t in range(period, n):
        y = historical_values[t]
        s_idx = t % period
        s_prev = seasonals[s_idx]
        
        last_level = level
        level = alpha * (y - s_prev) + (1.0 - alpha) * (last_level + phi * trend)
        trend = beta * (level - last_level) + (1.0 - beta) * (phi * trend)
        seasonals[s_idx] = 0.2 * (y - level) + 0.8 * s_prev

    # Extrapolate forecast
    forecasts = []
    accum_phi = 0.0
    for h in range(1, horizon + 1):
        accum_phi += (phi ** h)
        s_idx = (n + h - 1) % period
        pred = level + accum_phi * trend + seasonals[s_idx]
        forecasts.append(max(0.0, float(pred)))

    return forecasts

def execute_forecast_analysis(
    db: Session,
    dataset_id: str,
    target_metric: str = "total_visitors",
    horizon_days: int = 30
) -> Dict[str, Any]:
    """Train, evaluate against chronological split, and generate forward projection."""
    # Retrieve daily observations chronologically
    records = db.query(TourismObservation).filter(
        TourismObservation.dataset_id == dataset_id,
        TourismObservation.grain == "daily"
    ).order_by(TourismObservation.date.asc()).all()

    # Aggregate by date across all destinations for overall regional demand
    date_val_map = {}
    for r in records:
        val = getattr(r, target_metric, 0.0) or 0.0
        date_val_map[r.date] = date_val_map.get(r.date, 0.0) + float(val)

    sorted_dates = sorted(date_val_map.keys())
    if len(sorted_dates) < (horizon_days * 2):
        return {
            "success": False,
            "error": f"Insufficient historical observations. Found {len(sorted_dates)} days, but minimum required is {horizon_days * 2} days for a {horizon_days}-day horizon."
        }

    all_values = [date_val_map[d] for d in sorted_dates]

    # Chronological Split (Train: 0 to -horizon_days, Validation: last horizon_days)
    train_dates = sorted_dates[:-horizon_days]
    val_dates = sorted_dates[-horizon_days:]
    train_values = all_values[:-horizon_days]
    val_values = all_values[-horizon_days:]

    period = 7 # Weekly seasonality in daily tourism data

    # 1. Evaluate baseline on validation window
    baseline_val_preds = run_seasonal_naive_forecast(train_values, horizon=horizon_days, period=period)
    baseline_mae = calculate_mae(val_values, baseline_val_preds)

    # 2. Evaluate candidate damped trend model on validation window
    candidate_val_preds = run_damped_trend_forecast(train_values, horizon=horizon_days, period=period)
    candidate_mae = calculate_mae(val_values, candidate_val_preds)

    # In-sample MAE for MASE computation
    in_sample_mae = calculate_in_sample_naive_mae(train_values, period=period)
    candidate_mase = round(candidate_mae / max(0.001, in_sample_mae), 3)

    model_won = candidate_mae < baseline_mae

    # Residuals for standard error and 95% confidence interval (z=1.96)
    residuals = [a - p for a, p in zip(val_values, candidate_val_preds)]
    variance = sum(r ** 2 for r in residuals) / max(1, len(residuals))
    std_err = math.sqrt(variance)

    # Forward projection into the future starting after latest date
    last_known_date = sorted_dates[-1]
    future_dates = [last_known_date + timedelta(days=i) for i in range(1, horizon_days + 1)]
    future_baseline = run_seasonal_naive_forecast(all_values, horizon=horizon_days, period=period)
    future_candidate = run_damped_trend_forecast(all_values, horizon=horizon_days, period=period)

    # Save to database
    run_record = ForecastRun(
        dataset_id=dataset_id,
        target_metric=target_metric,
        model_type="damped_trend_with_seasonal_baseline",
        horizon_days=horizon_days,
        train_start_date=train_dates[0],
        train_end_date=train_dates[-1],
        mae=round(candidate_mae, 2),
        mase=candidate_mase,
        baseline_mae=round(baseline_mae, 2),
        model_won=model_won
    )
    db.add(run_record)
    db.flush()

    points_to_save = []
    points_summary = []

    for f_date, c_val, b_val in zip(future_dates, future_candidate, future_baseline):
        lower = max(0.0, c_val - (1.96 * std_err))
        upper = c_val + (1.96 * std_err)

        pt = ForecastPoint(
            forecast_run_id=run_record.id,
            forecast_date=f_date,
            predicted_value=round(c_val, 2),
            lower_bound=round(lower, 2),
            upper_bound=round(upper, 2),
            is_baseline=False
        )
        points_to_save.append(pt)
        points_summary.append({
            "date": str(f_date),
            "predicted": round(c_val, 1),
            "baseline": round(b_val, 1),
            "lower_95": round(lower, 1),
            "upper_95": round(upper, 1)
        })

    db.bulk_save_objects(points_to_save)
    db.commit()

    comparison_status = "Candidate Model Outperformed Baseline" if model_won else "Baseline (Seasonal-Naive) Outperformed Candidate"

    return {
        "success": True,
        "run_id": run_record.id,
        "target_metric": target_metric,
        "horizon_days": horizon_days,
        "train_period": f"{train_dates[0]} to {train_dates[-1]}",
        "validation_period": f"{val_dates[0]} to {val_dates[-1]}",
        "candidate_mae": round(candidate_mae, 2),
        "baseline_mae": round(baseline_mae, 2),
        "candidate_mase": candidate_mase,
        "model_won": model_won,
        "comparison_status": comparison_status,
        "points": points_summary,
        "limitations": "Forecast assumes continuation of historical seasonal patterns. Significant macroeconomic disruptions, unannounced weather anomalies, or ferry route closures are not captured in statistical time-series extrapolation."
    }
