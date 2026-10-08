"""
Seed the database with crop catalogue, fertilizer products, and a demonstration field.

Run via:  python -m app.data.seed

DEMO DATA NOTICE: All values are illustrative for MVP demonstration.
Economic values require regional calibration before any operational use.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.db.database import SessionLocal, init_db
from app.db.models import (
    Crop, CropEconomics, CropHistory, CropRequirement,
    Field, FertilizerProduct, RotationRule, SoilObservation,
)
from app.data.crop_data import (
    CROP_CATALOGUE, FERTILIZER_PRODUCTS, ROTATION_RULES
)


def seed_crops(db: Session) -> dict[str, int]:
    """Insert crops and return name->id mapping."""
    crop_ids: dict[str, int] = {}
    for cd in CROP_CATALOGUE:
        existing = db.query(Crop).filter(Crop.name == cd["name"]).first()
        if existing:
            # Update new fields if they exist on the record
            if not existing.sowing_window and cd.get("sowing_window"):
                existing.sowing_window = cd["sowing_window"]
                existing.harvest_window = cd.get("harvest_window")
                existing.crop_protection_level = cd.get("crop_protection_level")
                existing.labor_level = cd.get("labor_level")
            crop_ids[cd["name"]] = existing.id
            continue

        crop = Crop(
            name=cd["name"],
            family=cd["family"],
            season=cd["season"],
            water_need=cd["water_need"],
            duration_days=cd["duration_days"],
            sowing_window=cd.get("sowing_window"),
            harvest_window=cd.get("harvest_window"),
            crop_protection_level=cd.get("crop_protection_level"),
            labor_level=cd.get("labor_level"),
        )
        db.add(crop)
        db.flush()

        req = CropRequirement(
            crop_id=crop.id,
            ph_min=cd["ph_min"],
            ph_max=cd["ph_max"],
            temp_min=cd["temp_min"],
            temp_max=cd["temp_max"],
            water_min=cd["water_min"],
            water_max=cd["water_max"],
        )
        db.add(req)

        # Compute total variable cost from itemised costs
        total_cost = sum([
            cd.get("seed_cost_rs_ha", 0) or 0,
            cd.get("fertilizer_cost_rs_ha", 0) or 0,
            cd.get("pesticide_cost_rs_ha", 0) or 0,
            cd.get("irrigation_cost_rs_ha", 0) or 0,
            cd.get("labor_cost_rs_ha", 0) or 0,
            cd.get("machinery_cost_rs_ha", 0) or 0,
            cd.get("other_cost_rs_ha", 0) or 0,
        ])

        econ = CropEconomics(
            crop_id=crop.id,
            expected_yield_t_ha=cd["expected_yield_t_ha"],
            price_rs_per_t=cd["price_rs_per_t"],
            seed_cost_rs_ha=cd.get("seed_cost_rs_ha"),
            fertilizer_cost_rs_ha=cd.get("fertilizer_cost_rs_ha"),
            pesticide_cost_rs_ha=cd.get("pesticide_cost_rs_ha"),
            irrigation_cost_rs_ha=cd.get("irrigation_cost_rs_ha"),
            labor_cost_rs_ha=cd.get("labor_cost_rs_ha"),
            machinery_cost_rs_ha=cd.get("machinery_cost_rs_ha"),
            other_cost_rs_ha=cd.get("other_cost_rs_ha"),
            variable_cost_rs_per_ha=total_cost or cd.get("variable_cost_rs_per_ha"),
        )
        db.add(econ)
        crop_ids[cd["name"]] = crop.id

    db.flush()
    return crop_ids


def seed_fertilizer_products(db: Session) -> None:
    """Insert fertilizer product catalogue."""
    for fp in FERTILIZER_PRODUCTS:
        exists = db.query(FertilizerProduct).filter(
            FertilizerProduct.name == fp["name"]
        ).first()
        if not exists:
            db.add(FertilizerProduct(
                name=fp["name"],
                n_pct=fp.get("n_pct"),
                p_pct=fp.get("p_pct"),
                k_pct=fp.get("k_pct"),
                cost_rs_per_50kg=fp.get("cost_rs_per_50kg"),
                unit=fp.get("unit"),
            ))
    db.flush()


def seed_rotation_rules(db: Session, crop_ids: dict[str, int]) -> None:
    """Insert rotation rules."""
    for rule in ROTATION_RULES:
        a_name, b_name, gap, risk = rule
        a_id = crop_ids.get(a_name)
        b_id = crop_ids.get(b_name)
        if a_id is None or b_id is None:
            continue
        exists = (
            db.query(RotationRule)
            .filter(RotationRule.crop_a_id == a_id, RotationRule.crop_b_id == b_id)
            .first()
        )
        if not exists:
            db.add(RotationRule(
                crop_a_id=a_id, crop_b_id=b_id,
                minimum_gap=gap, disease_risk=risk
            ))
    db.flush()


def seed_demo_field(db: Session, crop_ids: dict[str, int]) -> Field:
    """Create a reproducible demonstration field."""
    existing = db.query(Field).filter(
        Field.name == "Demo Field - Sundarpur Plot 1"
    ).first()
    if existing:
        return existing

    field = Field(
        name="Demo Field - Sundarpur Plot 1",
        latitude=20.5937,
        longitude=78.9629,
        area_ha=2.0,
        irrigation_type="Partial",
        current_crop="Rice",
        farm_name="Sundarpur Farm",
        farming_type="Conventional",
        soil_type="Loam",
    )
    db.add(field)
    db.flush()

    # Demonstration soil observation
    obs = SoilObservation(
        field_id=field.id,
        sample_date=str(date.today()),
        ph=6.7,
        soc_pct=0.62,
        nitrogen=0.10,
        phosphorus=18.0,
        potassium=85.0,
        ec=0.8,
        sand_pct=40.0,
        silt_pct=35.0,
        clay_pct=25.0,
    )
    db.add(obs)

    # Three seasons of rice with realistic season metadata
    rice_id = crop_ids.get("Rice")
    if rice_id:
        seasons = [
            (1, "Kharif 2023", "Kharif", 2023, "2023-06-15", "2023-10-20", 3.8),
            (2, "Kharif 2024", "Kharif", 2024, "2024-06-18", "2024-10-22", 3.65),
            (3, "Kharif 2025", "Kharif", 2025, "2025-06-20", "2025-10-25", 3.5),
        ]
        for order, sname, stype, yr, sow, harv, yld in seasons:
            db.add(CropHistory(
                field_id=field.id,
                season_order=order,
                season_name=sname,
                season_type=stype,
                year=yr,
                crop_id=rice_id,
                sowing_date=sow,
                harvest_date=harv,
                duration_days=127,
                cultivated_area_ha=2.0,
                production_qty=yld * 2.0,
                production_unit="tonnes",
                yield_t_ha=yld,
            ))
    db.flush()
    return field


def run_seed():
    init_db()
    db = SessionLocal()
    try:
        crop_ids = seed_crops(db)
        seed_fertilizer_products(db)
        seed_rotation_rules(db, crop_ids)
        demo_field = seed_demo_field(db, crop_ids)
        db.commit()
        print(f"[OK] Seeded {len(CROP_CATALOGUE)} crops")
        print(f"[OK] Seeded fertilizer products")
        print(f"[OK] Seeded {len(ROTATION_RULES)} rotation rules")
        print(f"[OK] Demo field id={demo_field.id}: {demo_field.name}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
