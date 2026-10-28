"""Domain calculation tests with hand-verified benchmarks."""
import pytest
from app.services.forecast_service import calculate_mae, calculate_in_sample_naive_mae, run_seasonal_naive_forecast
from app.services.scenario_service import simulate_scenario

def test_seasonal_naive_baseline_hand_checked():
    # 14 days series with 7-day seasonality
    series = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 12.0, 22.0, 32.0, 42.0, 52.0, 62.0, 72.0]
    horizon = 7
    period = 7
    
    preds = run_seasonal_naive_forecast(series, horizon=horizon, period=period)
    # Expected: repeats the last 7 days exactly
    expected = [12.0, 22.0, 32.0, 42.0, 52.0, 62.0, 72.0]
    assert preds == expected

def test_mae_calculation_hand_checked():
    actuals = [100.0, 200.0, 300.0]
    preds = [110.0, 190.0, 315.0]
    # abs diffs: [10, 10, 15] -> sum = 35 -> / 3 = 11.6666...
    mae = calculate_mae(actuals, preds)
    assert round(mae, 4) == round(35.0 / 3.0, 4)

def test_in_sample_naive_mae_hand_checked():
    # series of length 9 with period 4
    # diffs at t=4: |50 - 10| = 40
    # diffs at t=5: |60 - 20| = 40
    # diffs at t=6: |70 - 30| = 40
    # diffs at t=7: |80 - 40| = 40
    # diffs at t=8: |90 - 50| = 40
    # mean = 40.0
    series = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]
    res = calculate_in_sample_naive_mae(series, period=4)
    assert res == 40.0

def test_scenario_roi_zero_spend_no_zero_division():
    # When spend is 0, ROI must return 0.0 without ZeroDivisionError
    res = simulate_scenario(
        base_visitors=10000,
        base_revenue=5_000_000_000.0,
        marketing_spend_idr=0.0,
        price_change_pct=5.0,
        seasonality_multiplier=1.0
    )
    assert res["marketing_spend_idr"] == 0.0
    assert res["roi_percentage"] == 0.0
    assert res["simulated_visitors"] > 0

def test_scenario_roi_positive_spend():
    res = simulate_scenario(
        base_visitors=10000,
        base_revenue=5_000_000_000.0,
        marketing_spend_idr=100_000_000.0,
        price_change_pct=0.0,
        seasonality_multiplier=1.0
    )
    assert res["marketing_spend_idr"] == 100_000_000.0
    assert res["simulated_visitors"] > 10000
    assert res["simulated_revenue_idr"] > 5_000_000_000.0
    expected_roi = round((res["gross_contribution_idr"] / 100_000_000.0) * 100.0, 2)
    assert res["roi_percentage"] == expected_roi

def test_scenario_negative_gross_contribution():
    # Extreme marketing spend with severe price drop causing negative yield delta
    res = simulate_scenario(
        base_visitors=1000,
        base_revenue=100_000_000.0,
        marketing_spend_idr=500_000_000.0, # Huge spend relative to base
        price_change_pct=-40.0,
        seasonality_multiplier=0.5
    )
    assert res["gross_contribution_idr"] < 0
    assert res["roi_percentage"] < 0
