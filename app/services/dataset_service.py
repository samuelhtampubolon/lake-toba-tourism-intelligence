"""Dataset registry, provenance tracking, and cache lifecycle management."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import Dataset, TourismObservation, ForecastRun, Scenario, DataSource

# In-memory bounded cache for deterministic aggregations
_AGGREGATION_CACHE: Dict[str, Any] = {}

def get_cache_key(dataset_id: str, grain: str, start_date: str, end_date: str, dest_id: Optional[str]) -> str:
    """Generate deterministic cache key."""
    return f"{dataset_id}:{grain}:{start_date}:{end_date}:{dest_id or 'all'}"

def get_cached_aggregation(key: str) -> Optional[Any]:
    return _AGGREGATION_CACHE.get(key)

def set_cached_aggregation(key: str, data: Any) -> None:
    # Bound cache size to 100 entries to maintain <2GB RAM profile
    if len(_AGGREGATION_CACHE) > 100:
        _AGGREGATION_CACHE.clear()
    _AGGREGATION_CACHE[key] = data

def invalidate_dataset_cache(dataset_id: str) -> None:
    """Invalidate all cached aggregations for the specified dataset."""
    keys_to_remove = [k for k in _AGGREGATION_CACHE if k.startswith(f"{dataset_id}:")]
    for k in keys_to_remove:
        _AGGREGATION_CACHE.pop(k, None)

def list_datasets(db: Session) -> List[Dataset]:
    """Retrieve all registered datasets ordered by newest first."""
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()

def get_dataset_by_id(db: Session, dataset_id: str) -> Optional[Dataset]:
    """Retrieve a single dataset by ID."""
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()

def delete_dataset(db: Session, dataset_id: str) -> bool:
    """Delete a dataset and all associated observations, forecasts, and cached items."""
    ds = get_dataset_by_id(db, dataset_id)
    if not ds:
        return False

    invalidate_dataset_cache(dataset_id)
    db.delete(ds)
    db.commit()
    return True
