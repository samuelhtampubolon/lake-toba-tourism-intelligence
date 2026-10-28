"""Deterministic synthetic demo data generator for Lake Toba Tourism Intelligence."""
import random
from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.entities import (
    Dataset, DataSource, Destination, TourismObservation, SeasonalityCalendar, CustomerSegment
)

DESTINATIONS_DATA = [
    {
        "code": "PARAPAT",
        "name": "Parapat Lakeside Resort",
        "regency": "Simalungun",
        "category": "Lakeside / Port Hub",
        "description": "Historic gateway harbor connecting mainland North Sumatra to Samosir Island with lakeside hotels and ferry terminals."
    },
    {
        "code": "TUKTUK",
        "name": "Tuktuk Siadong Peninsula",
        "regency": "Samosir",
        "category": "Cultural Heritage / Island",
        "description": "Batak cultural center, traditional homestays, lakeside art workshops, and scenic peninsular walking paths."
    },
    {
        "code": "BALIGE",
        "name": "Balige Waterfront & Harbor",
        "regency": "Toba",
        "category": "Waterfront / Sports Arena",
        "description": "Southern shores venue hosting the international F1H2O UIM Powerboat World Championship and TB Silalahi Batak Center."
    },
    {
        "code": "TONGGING",
        "name": "Tongging & Sipiso-piso",
        "regency": "Karo",
        "category": "Highland / Ecotourism",
        "description": "Northern rim panoramic vistas overlooking the caldera and Indonesia's highest plunge waterfall (120m)."
    },
    {
        "code": "PANGURURAN",
        "name": "Pangururan Hot Springs & Canal",
        "regency": "Samosir",
        "category": "Geothermal / Island Gateway",
        "description": "Capital of Samosir Regency featuring natural geothermal springs, Samosir Canal Bridge, and local culinary culture."
    },
    {
        "code": "SILANGIT",
        "name": "Silangit Airport Gateway",
        "regency": "North Tapanuli",
        "category": "Aviation / Transit District",
        "description": "Air transit hub providing direct jet flight connections from Jakarta and international hubs to Lake Toba."
    }
]

CUSTOMER_SEGMENTS_DATA = [
    {
        "code": "DOM_WEEKEND",
        "name": "Domestic Weekend Getaway",
        "description": "Urban families and young professionals from Medan, Pekanbaru, and Greater Jakarta seeking lakeside relaxation.",
        "travel_party_size": 3.6,
        "avg_stay_days": 2.2,
        "avg_spend_per_day_idr": 850000.0,
        "preference_tags": "Scenic Lake Views, Culinary, Water Sports, Relaxation"
    },
    {
        "code": "CULT_HERITAGE",
        "name": "Cultural Heritage & Ecotourists",
        "description": "Scholars, educators, and cultural travelers focused on Batak architecture, Ulos weaving, and UNESCO Global Geopark sites.",
        "travel_party_size": 2.2,
        "avg_stay_days": 4.5,
        "avg_spend_per_day_idr": 1150000.0,
        "preference_tags": "UNESCO Geopark, Ulos Weaving, Tomok Heritage, Museums"
    },
    {
        "code": "INTL_ADVENTURE",
        "name": "International Nature & Active Explorers",
        "description": "Backpackers and foreign adventure tourists engaged in island cycling, kayaking, hiking Mount Pusuk Buhit.",
        "travel_party_size": 1.8,
        "avg_stay_days": 5.8,
        "avg_spend_per_day_idr": 720000.0,
        "preference_tags": "Trekking, Kayaking, Cycling Samosir, Local Homestays"
    },
    {
        "code": "MICE_EVENTS",
        "name": "MICE & International Sports Delegates",
        "description": "Corporate conference attendees, government delegations, and spectators for international sporting events like F1H2O.",
        "travel_party_size": 4.2,
        "avg_stay_days": 3.2,
        "avg_spend_per_day_idr": 2450000.0,
        "preference_tags": "Luxury Resorts, VIP Hospitality, Gala Dinners, Regattas"
    }
]

def seed_destinations_and_segments(db: Session) -> Dict[str, Any]:
    """Ensure baseline destinations and customer segments exist."""
    dest_map = {}
    for item in DESTINATIONS_DATA:
        dest = db.query(Destination).filter(Destination.code == item["code"]).first()
        if not dest:
            dest = Destination(**item)
            db.add(dest)
            db.commit()
            db.refresh(dest)
        dest_map[item["code"]] = dest

    seg_map = {}
    for item in CUSTOMER_SEGMENTS_DATA:
        seg = db.query(CustomerSegment).filter(CustomerSegment.code == item["code"]).first()
        if not seg:
            seg = CustomerSegment(**item)
            db.add(seg)
            db.commit()
            db.refresh(seg)
        seg_map[item["code"]] = seg

    return {"destinations": dest_map, "segments": seg_map}

def seed_calendar_events(db: Session, start_year: int = 2024, end_year: int = 2025):
    """Seed calendar days with season tiers and multipliers."""
    cur_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)
    
    while cur_date <= end_date:
        existing = db.query(SeasonalityCalendar).filter(SeasonalityCalendar.date == cur_date).first()
        if not existing:
            month = cur_date.month
            day = cur_date.day
            weekday = cur_date.weekday()
            is_weekend = weekday in (4, 5, 6) # Fri, Sat, Sun

            event_name = None
            tier = "regular"
            mult = 1.0

            # Annual events
            if month == 2 and 22 <= day <= 26:
                event_name = "F1H2O UIM World Championship Balige"
                tier = "peak"
                mult = 2.2
            elif month == 7 and 10 <= day <= 15:
                event_name = "Lake Toba Cultural Festival"
                tier = "peak"
                mult = 1.8
            elif month == 12 and day >= 20:
                event_name = "Christmas & Year-End Holidays"
                tier = "peak"
                mult = 1.9
            elif month == 1 and day <= 5:
                event_name = "New Year Celebrations"
                tier = "high"
                mult = 1.6
            elif month in (6, 7): # Mid-year school holidays
                tier = "high"
                mult = 1.4
            elif month in (10, 11): # Rainy season
                tier = "low"
                mult = 0.85

            if is_weekend and mult < 1.5:
                mult *= 1.25

            cal_entry = SeasonalityCalendar(
                date=cur_date,
                year=cur_date.year,
                month=month,
                day_of_week=weekday,
                is_weekend=is_weekend,
                event_name=event_name,
                season_tier=tier,
                multiplier=round(mult, 2)
            )
            db.add(cal_entry)
        cur_date += timedelta(days=1)
    db.commit()

def generate_lake_toba_demo_dataset(db: Session, seed: int = 42) -> Dataset:
    """Generate reproducible 2-year synthetic dataset for Lake Toba tourism intelligence."""
    rng = random.Random(seed)
    meta = seed_destinations_and_segments(db)
    seed_calendar_events(db, 2024, 2025)
    destinations = list(meta["destinations"].values())

    # Create dataset record
    dataset = Dataset(
        name="Lake Toba Official Tourism Intelligence Baseline (2024-2025)",
        description="Comprehensive synthetic benchmark dataset covering visitor footfall, hotel occupancy, average daily rate (ADR), and regional tourism revenue across 6 key Lake Toba destinations.",
        provenance_source="North Sumatra Provincial Tourism Office & Lake Toba Authority Board (Synthetic Benchmark)",
        source_url="https://bpodt.id/open-data/lake-toba-tourism-2024-2025",
        license="CC-BY-4.0",
        collection_date=date(2026, 1, 15),
        geography="Lake Toba Region (Simalungun, Samosir, Toba, Karo, North Tapanuli)",
        unit="Visitors (Pax) / IDR (Rupiah)",
        row_count=0,
        is_synthetic=True,
        version=1
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Base destination visitor parameters
    dest_base_weights = {
        "PARAPAT": {"base_vis": 1400, "hotel_rooms": 2200, "base_adr": 650000.0},
        "TUKTUK": {"base_vis": 950, "hotel_rooms": 1400, "base_adr": 480000.0},
        "BALIGE": {"base_vis": 800, "hotel_rooms": 1100, "base_adr": 520000.0},
        "TONGGING": {"base_vis": 600, "hotel_rooms": 450, "base_adr": 380000.0},
        "PANGURURAN": {"base_vis": 550, "hotel_rooms": 600, "base_adr": 420000.0},
        "SILANGIT": {"base_vis": 1100, "hotel_rooms": 850, "base_adr": 580000.0},
    }

    start_date = date(2024, 1, 1)
    end_date = date(2025, 12, 31)
    delta_days = (end_date - start_date).days + 1

    total_rows = 0
    obs_batch = []

    for day_idx in range(delta_days):
        current_date = start_date + timedelta(days=day_idx)
        # Fetch multiplier from calendar
        cal_item = db.query(SeasonalityCalendar).filter(SeasonalityCalendar.date == current_date).first()
        season_mult = cal_item.multiplier if cal_item else 1.0

        for dest in destinations:
            cfg = dest_base_weights.get(dest.code, {"base_vis": 600, "hotel_rooms": 800, "base_adr": 500000.0})
            
            # Fluctuation with random noise
            noise = rng.uniform(0.85, 1.15)
            # F1H2O boost specifically in Balige
            dest_special_mult = 1.0
            if dest.code == "BALIGE" and cal_item and cal_item.event_name and "F1H2O" in cal_item.event_name:
                dest_special_mult = 2.8
            elif dest.code in ("PARAPAT", "TUKTUK") and cal_item and cal_item.event_name and "Festival" in cal_item.event_name:
                dest_special_mult = 1.9

            eff_mult = season_mult * dest_special_mult * noise
            total_vis = int(cfg["base_vis"] * eff_mult)
            intl_pct = rng.uniform(0.12, 0.28) if dest.code in ("TUKTUK", "SILANGIT") else rng.uniform(0.04, 0.12)
            intl_vis = int(total_vis * intl_pct)
            dom_vis = total_vis - intl_vis

            # Occupancy & ADR
            rooms_cap = cfg["hotel_rooms"]
            rooms_occ = min(rooms_cap, int(total_vis * rng.uniform(0.35, 0.52)))
            occ_rate = round((rooms_occ / rooms_cap) * 100.0, 2)
            
            # ADR increases in peak seasons
            adr = cfg["base_adr"] * (1.0 + (occ_rate / 100.0) * 0.4) * rng.uniform(0.95, 1.05)
            # Tourism revenue: hotel revenue + visitor expenditure (food, transit, culture)
            local_spend_per_pax = rng.uniform(250000.0, 450000.0)
            total_rev = (rooms_occ * adr) + (total_vis * local_spend_per_pax)

            obs = TourismObservation(
                dataset_id=dataset.id,
                destination_id=dest.id,
                date=current_date,
                grain="daily",
                visitors_domestic=dom_vis,
                visitors_international=intl_vis,
                total_visitors=total_vis,
                hotel_rooms_occupied=rooms_occ,
                hotel_occupancy_rate=occ_rate,
                avg_daily_rate_idr=round(adr, 2),
                total_revenue_idr=round(total_rev, 2)
            )
            obs_batch.append(obs)
            total_rows += 1

            if len(obs_batch) >= 500:
                db.bulk_save_objects(obs_batch)
                db.commit()
                obs_batch = []

    if obs_batch:
        db.bulk_save_objects(obs_batch)
        db.commit()

    dataset.row_count = total_rows
    db.commit()
    return dataset
