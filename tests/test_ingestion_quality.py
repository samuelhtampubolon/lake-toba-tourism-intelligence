"""CSV ingestion and data quality profiler tests."""
import codecs
import pytest
from app.services.ingestion_service import preview_csv_content, commit_csv_import
from app.services.quality_service import profile_dataset_quality
from app.models.entities import Destination

def test_csv_preview_and_bom_support():
    # Valid CSV content with UTF-8 BOM
    raw_csv = "date,destination_code,visitors_domestic,visitors_international,hotel_occupancy_rate,avg_daily_rate_idr,total_revenue_idr\n2025-01-01,PARAPAT,1200,300,75.0,650000,1200000000\n"
    bom_bytes = codecs.BOM_UTF8 + raw_csv.encode("utf-8")

    preview = preview_csv_content(bom_bytes, "lake_toba_bom_test.csv")
    assert preview["success"] is True
    assert preview["total_rows"] == 1
    assert preview["has_errors"] is False
    assert len(preview["preview_rows"]) == 1

def test_csv_rejection_on_invalid_date(db_session):
    bad_csv = "date,destination_code,visitors_domestic,visitors_international,hotel_occupancy_rate,avg_daily_rate_idr,total_revenue_idr\nnot-a-valid-date,PARAPAT,100,20,50.0,500000,50000000\n"
    mapping = {
        "date": "date", "destination_code": "destination_code",
        "visitors_domestic": "visitors_domestic", "visitors_international": "visitors_international"
    }

    ok, msg, dataset = commit_csv_import(
        db_session, bad_csv.encode("utf-8"), "bad_date.csv", "Bad Date Test", "Test", None, mapping
    )
    assert ok is False
    assert "Invalid date format" in msg
    assert dataset is None

def test_csv_rejection_on_unknown_destination(db_session):
    bad_dest_csv = "date,destination_code,visitors_domestic,visitors_international,hotel_occupancy_rate,avg_daily_rate_idr,total_revenue_idr\n2025-01-01,UNKNOWN_DEST,100,20,50.0,500000,50000000\n"
    mapping = {
        "date": "date", "destination_code": "destination_code",
        "visitors_domestic": "visitors_domestic", "visitors_international": "visitors_international"
    }

    ok, msg, dataset = commit_csv_import(
        db_session, bad_dest_csv.encode("utf-8"), "bad_dest.csv", "Bad Dest Test", "Test", None, mapping
    )
    assert ok is False
    assert "is not recognized" in msg
    assert dataset is None

def test_data_quality_profiler_metrics(db_session, seeded_dataset):
    profile = profile_dataset_quality(db_session, seeded_dataset.id)
    assert profile["total_records"] > 0
    assert profile["status"] in ("EXCELLENT", "WARNINGS_DETECTED")
    assert profile["coverage_percentage"] > 90.0
    assert "visitors_domestic" in profile["null_counts"]
    assert profile["earliest_date"] is not None
    assert profile["latest_date"] is not None
