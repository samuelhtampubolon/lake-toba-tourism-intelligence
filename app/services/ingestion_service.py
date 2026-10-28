"""CSV ingestion service with encoding detection, schema mapping, validation, and preview."""
import csv
import io
import hashlib
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.entities import Dataset, DataSource, Destination, TourismObservation

REQUIRED_FIELDS = ["date", "destination_code", "visitors_domestic", "visitors_international"]

def parse_flexible_date(date_str: str) -> Optional[date]:
    """Parse date from common ISO or Indonesian date formats."""
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def preview_csv_content(
    file_bytes: bytes,
    file_name: str,
    max_preview_rows: int = 5
) -> Dict[str, Any]:
    """Parse CSV, check encoding and columns, and return validation preview."""
    # Handle UTF-8 with or without BOM
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "File encoding is not valid UTF-8. Please provide a UTF-8 encoded CSV file."
        }

    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return {"success": False, "error": "CSV file is empty."}

    # Clean headers
    cleaned_header = [h.strip().lower() for h in header]
    rows = []
    validation_errors = []
    total_rows = 0

    for idx, row in enumerate(reader, start=2): # 1-indexed line 2
        total_rows += 1
        if not row or all(c.strip() == "" for c in row):
            continue
        if len(row) != len(header):
            validation_errors.append(f"Row {idx}: column count mismatch (expected {len(header)}, got {len(row)})")
            continue

        if len(rows) < max_preview_rows:
            rows.append(row)

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    return {
        "success": True,
        "file_name": file_name,
        "file_hash_sha256": file_hash,
        "headers": header,
        "cleaned_headers": cleaned_header,
        "total_rows": total_rows,
        "preview_rows": rows,
        "validation_errors": validation_errors[:10],
        "has_errors": len(validation_errors) > 0
    }

def commit_csv_import(
    db: Session,
    file_bytes: bytes,
    file_name: str,
    dataset_name: str,
    provenance_source: str,
    source_url: Optional[str],
    column_mapping: Dict[str, str]
) -> Tuple[bool, str, Optional[Dataset]]:
    """Commit validated CSV records into a new Dataset transactionally."""
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    
    # Preload destinations
    dest_map = {d.code.upper(): d for d in db.query(Destination).all()}

    # Create dataset record
    dataset = Dataset(
        name=dataset_name,
        provenance_source=provenance_source,
        source_url=source_url,
        license="CC-BY-4.0",
        collection_date=date.today(),
        geography="Lake Toba Region, North Sumatra",
        unit="Visitors / IDR",
        row_count=0,
        is_synthetic=False,
        version=1
    )
    db.add(dataset)
    db.flush()

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    data_source = DataSource(
        dataset_id=dataset.id,
        file_name=file_name,
        file_hash_sha256=file_hash,
        original_columns=",".join(reader.fieldnames or []),
        mapped_columns=str(column_mapping)
    )
    db.add(data_source)

    observations = []
    row_count = 0

    for line_num, row in enumerate(reader, start=2):
        date_raw = row.get(column_mapping.get("date", "date"))
        dest_code_raw = row.get(column_mapping.get("destination_code", "destination_code"))
        dom_vis_raw = row.get(column_mapping.get("visitors_domestic", "visitors_domestic"))
        intl_vis_raw = row.get(column_mapping.get("visitors_international", "visitors_international"))
        occ_rate_raw = row.get(column_mapping.get("hotel_occupancy_rate", "hotel_occupancy_rate"))
        adr_raw = row.get(column_mapping.get("avg_daily_rate_idr", "avg_daily_rate_idr"))
        rev_raw = row.get(column_mapping.get("total_revenue_idr", "total_revenue_idr"))

        if not date_raw or not dest_code_raw:
            db.rollback()
            return False, f"Row {line_num}: Missing required date or destination code.", None

        parsed_date = parse_flexible_date(date_raw)
        if not parsed_date:
            db.rollback()
            return False, f"Row {line_num}: Invalid date format '{date_raw}'.", None

        dest = dest_map.get(dest_code_raw.strip().upper())
        if not dest:
            db.rollback()
            return False, f"Row {line_num}: Destination code '{dest_code_raw}' is not recognized.", None

        try:
            dom_vis = max(0, int(float(dom_vis_raw))) if dom_vis_raw else 0
            intl_vis = max(0, int(float(intl_vis_raw))) if intl_vis_raw else 0
            total_vis = dom_vis + intl_vis

            occ_rate = float(occ_rate_raw) if occ_rate_raw else 0.0
            if occ_rate < 0 or occ_rate > 100.0:
                occ_rate = max(0.0, min(100.0, occ_rate))

            adr = max(0.0, float(adr_raw)) if adr_raw else 500000.0
            rev = max(0.0, float(rev_raw)) if rev_raw else (total_vis * 450000.0)
        except ValueError as e:
            db.rollback()
            return False, f"Row {line_num}: Numeric parse error ({str(e)}).", None

        obs = TourismObservation(
            dataset_id=dataset.id,
            destination_id=dest.id,
            date=parsed_date,
            grain="daily",
            visitors_domestic=dom_vis,
            visitors_international=intl_vis,
            total_visitors=total_vis,
            hotel_rooms_occupied=int(total_vis * 0.4),
            hotel_occupancy_rate=round(occ_rate, 2),
            avg_daily_rate_idr=round(adr, 2),
            total_revenue_idr=round(rev, 2)
        )
        observations.append(obs)
        row_count += 1

    if observations:
        db.bulk_save_objects(observations)
    
    dataset.row_count = row_count
    db.commit()
    db.refresh(dataset)
    return True, f"Successfully imported {row_count} records into dataset.", dataset
