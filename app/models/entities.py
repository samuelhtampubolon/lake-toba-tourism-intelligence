"""Domain entities and SQLAlchemy ORM models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    """Generate an opaque UUID string for primary keys."""
    return str(uuid.uuid4())

def utc_now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="read_only_executive")
    # Roles: 'business_owner', 'tourism_analyst', 'marketing_manager', 'read_only_executive'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="author")

class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_accessed_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="sessions")

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    provenance_source = Column(String(150), nullable=False)
    source_url = Column(String(255), nullable=True)
    license = Column(String(50), nullable=False, default="CC-BY-4.0")
    collection_date = Column(Date, nullable=False)
    geography = Column(String(100), nullable=False, default="Lake Toba Region, North Sumatra")
    unit = Column(String(50), nullable=False, default="visitors / IDR")
    row_count = Column(Integer, default=0, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    sources = relationship("DataSource", back_populates="dataset", cascade="all, delete-orphan")
    observations = relationship("TourismObservation", back_populates="dataset", cascade="all, delete-orphan")
    forecast_runs = relationship("ForecastRun", back_populates="dataset", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="dataset", cascade="all, delete-orphan")

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False)
    original_columns = Column(Text, nullable=False)
    mapped_columns = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    dataset = relationship("Dataset", back_populates="sources")

class Destination(Base):
    __tablename__ = "destinations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    regency = Column(String(80), nullable=False) # Simalungun, Samosir, Toba, Karo, etc.
    category = Column(String(50), nullable=False) # Cultural, Island, Mountain/Water, Transit
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    observations = relationship("TourismObservation", back_populates="destination")

class TourismObservation(Base):
    __tablename__ = "tourism_observations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    destination_id = Column(String(36), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    grain = Column(String(20), default="daily", nullable=False) # 'daily', 'weekly', 'monthly'
    visitors_domestic = Column(Integer, default=0, nullable=False)
    visitors_international = Column(Integer, default=0, nullable=False)
    total_visitors = Column(Integer, default=0, nullable=False)
    hotel_rooms_occupied = Column(Integer, default=0, nullable=False)
    hotel_occupancy_rate = Column(Float, default=0.0, nullable=False)
    avg_daily_rate_idr = Column(Float, default=0.0, nullable=False)
    total_revenue_idr = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("dataset_id", "destination_id", "date", "grain", name="uq_dataset_dest_date_grain"),
        Index("ix_obs_dataset_date", "dataset_id", "date"),
    )

    dataset = relationship("Dataset", back_populates="observations")
    destination = relationship("Destination", back_populates="observations")

class SeasonalityCalendar(Base):
    __tablename__ = "seasonality_calendar"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    date = Column(Date, unique=True, nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False) # 0=Monday, 6=Sunday
    is_weekend = Column(Boolean, default=False, nullable=False)
    event_name = Column(String(100), nullable=True) # e.g., 'Lake Toba Festival', 'F1H2O Powerboat'
    season_tier = Column(String(20), default="regular", nullable=False) # 'low', 'regular', 'high', 'peak'
    multiplier = Column(Float, default=1.0, nullable=False)

class CustomerSegment(Base):
    __tablename__ = "customer_segments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    travel_party_size = Column(Float, default=2.5, nullable=False)
    avg_stay_days = Column(Float, default=2.5, nullable=False)
    avg_spend_per_day_idr = Column(Float, default=750000.0, nullable=False)
    preference_tags = Column(String(255), nullable=True) # e.g., "Culture, Heritage, Culinary"
    is_active = Column(Boolean, default=True, nullable=False)

    campaigns = relationship("Campaign", back_populates="target_segment")

class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    target_metric = Column(String(50), nullable=False) # 'total_visitors', 'total_revenue_idr'
    model_type = Column(String(50), nullable=False) # 'seasonal_naive', 'damped_trend'
    horizon_days = Column(Integer, default=30, nullable=False)
    train_start_date = Column(Date, nullable=False)
    train_end_date = Column(Date, nullable=False)
    mae = Column(Float, nullable=False)
    mase = Column(Float, nullable=False)
    baseline_mae = Column(Float, nullable=False)
    model_won = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    dataset = relationship("Dataset", back_populates="forecast_runs")
    points = relationship("ForecastPoint", back_populates="forecast_run", cascade="all, delete-orphan")

class ForecastPoint(Base):
    __tablename__ = "forecast_points"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    forecast_run_id = Column(String(36), ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    predicted_value = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)
    is_baseline = Column(Boolean, default=False, nullable=False)

    forecast_run = relationship("ForecastRun", back_populates="points")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False) # 'Digital Ads', 'Influencer', 'Travel Expo', 'Local Tourism Board'
    budget_allocated_idr = Column(Float, default=0.0, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_segment_id = Column(String(36), ForeignKey("customer_segments.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    target_segment = relationship("CustomerSegment", back_populates="campaigns")

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_revenue_idr = Column(Float, default=0.0, nullable=False)
    simulated_revenue_idr = Column(Float, default=0.0, nullable=False)
    total_marketing_spend_idr = Column(Float, default=0.0, nullable=False)
    gross_contribution_idr = Column(Float, default=0.0, nullable=False)
    roi_percentage = Column(Float, default=0.0, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    dataset = relationship("Dataset", back_populates="scenarios")
    assumptions = relationship("ScenarioAssumption", back_populates="scenario", cascade="all, delete-orphan")

class ScenarioAssumption(Base):
    __tablename__ = "scenario_assumptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scenario_id = Column(String(36), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    assumption_key = Column(String(80), nullable=False)
    assumption_value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=False) # '%', 'IDR', 'multiplier'
    note = Column(Text, nullable=True)

    scenario = relationship("Scenario", back_populates="assumptions")

class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(150), nullable=False)
    report_type = Column(String(50), nullable=False) # 'Executive Brief', 'Demand & Forecast', 'Scenario Impact'
    dataset_version = Column(Integer, default=1, nullable=False)
    filters_json = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    analyst_notes = Column(Text, nullable=True)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    author = relationship("User", back_populates="reports")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    action = Column(String(50), nullable=False, index=True) # 'LOGIN', 'DATASET_IMPORT', 'DATASET_DELETE', 'FORECAST_RUN', 'SCENARIO_SAVE', 'EXPORT_REPORT'
    entity_name = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
