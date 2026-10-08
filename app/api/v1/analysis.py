"""
Analysis API — POST /fields/{field_id}/analyze
            — GET  /fields/{field_id}/crops
            — GET  /crops/{crop_id}/economics
            — GET  /crops/{crop_id}/sensitivity
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import (
    Crop, CropHistory, Field, FieldProblem, FertilizerUsage, SoilObservation
)
from app.schemas.crop import ClimateInput
from app.services import (
    degradation_service,
    economics_service,
    soil_service,
    suitability_service,
)
from app.data.crop_data import PROBLEM_TYPES

router = APIRouter(tags=["analysis"])


def _latest_soil(field_id: int, db: Session) -> Optional[SoilObservation]:
    return (
        db.query(SoilObservation)
        .filter(SoilObservation.field_id == field_id)
        .order_by(SoilObservation.id.desc())
        .first()
    )


def _crop_history_names(field_id: int, db: Session) -> List[str]:
    rows = (
        db.query(CropHistory)
        .filter(CropHistory.field_id == field_id)
        .order_by(CropHistory.season_order)
        .all()
    )
    return [r.crop.name for r in rows]


def _problem_penalties(field_id: int, db: Session) -> Dict[str, float]:
    """Aggregate problem penalties from farmer-reported problems."""
    problems = (
        db.query(FieldProblem)
        .filter(FieldProblem.field_id == field_id)
        .all()
    )
    problem_map = {p["code"]: p for p in PROBLEM_TYPES}
    total_water = 0.0
    total_rotation = 0.0
    total_soil = 0.0
    severity_mult = {"Low": 0.5, "Moderate": 1.0, "High": 1.5}

    for p in problems:
        info = problem_map.get(p.problem_code, {})
        mult = severity_mult.get(p.severity or "Moderate", 1.0)
        total_water    += info.get("water_penalty", 0) * mult
        total_rotation += info.get("rotation_penalty", 0) * mult
        total_soil     += info.get("soil_penalty", 0) * mult

    return {
        "water_penalty": min(total_water, 50.0),
        "rotation_penalty": min(total_rotation, 40.0),
        "soil_penalty": min(total_soil, 30.0),
        "has_water_shortage": any(
            p.problem_code == "water_shortage" for p in problems
        ),
        "has_disease": any(p.problem_code == "disease" for p in problems),
    }


@router.post("/fields/{field_id}/analyze")
def analyze_field(
    field_id: int,
    climate: ClimateInput = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    field = db.get(Field, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")

    if climate is None:
        climate = ClimateInput()

    # Soil
    obs = _latest_soil(field_id, db)
    if obs:
        soil_assessment = soil_service.assess_soil(
            ph=obs.ph, soc_pct=obs.soc_pct, nitrogen=obs.nitrogen,
            phosphorus=obs.phosphorus, potassium=obs.potassium,
            ec=obs.ec, sand_pct=obs.sand_pct, silt_pct=obs.silt_pct,
            clay_pct=obs.clay_pct,
        )
    else:
        soil_assessment = soil_service.assess_soil()

    # Crop history
    history_names = _crop_history_names(field_id, db)

    # Problem penalties
    penalties = _problem_penalties(field_id, db)

    # Degradation
    rs_data = degradation_service.get_demo_remote_sensing()
    degradation = degradation_service.assess_degradation(
        soil=soil_assessment,
        crop_history=history_names,
        rs_data=rs_data,
    )

    # Apply problem-driven adjustments to effective water
    effective_rainfall = climate.seasonal_rainfall_mm
    if penalties["has_water_shortage"]:
        effective_rainfall = max(effective_rainfall * 0.75, 100)

    # Crop suitability — pass problem penalties through to scores
    crops = db.query(Crop).all()
    suitability = suitability_service.rank_crops(
        crops=crops,
        soil=soil_assessment,
        mean_temp_c=climate.mean_temp_c,
        seasonal_rainfall_mm=effective_rainfall,
        irrigation_type=field.irrigation_type,
        crop_history=history_names,
        problem_penalties=penalties,
    )

    # Fertilizer summary
    fert_usages = (
        db.query(FertilizerUsage)
        .filter(FertilizerUsage.field_id == field_id)
        .all()
    )
    fert_summary = [
        {
            "fertilizer": u.product.name if u.product else "Unknown",
            "quantity_kg_ha": u.quantity_kg_ha,
            "season_name": u.season_name,
            "total_cost_rs": u.total_cost_rs,
        }
        for u in fert_usages
    ]

    # Problem summary
    all_problems = (
        db.query(FieldProblem)
        .filter(FieldProblem.field_id == field_id)
        .all()
    )
    problem_summary = [
        {"code": p.problem_code, "label": p.problem_label,
         "severity": p.severity, "season": p.season_name}
        for p in all_problems
    ]

    return {
        "field_id": field_id,
        "field_name": field.name,
        "soil_assessment": soil_assessment.model_dump(),
        "degradation": degradation,
        "remote_sensing": rs_data,
        "crop_suitability": [s.model_dump() for s in suitability],
        "history_summary": history_names,
        "problem_summary": problem_summary,
        "fertilizer_summary": fert_summary,
        "climate_used": climate.model_dump(),
        "analysis_disclaimer": (
            "Rule-based decision-support prototype. "
            "All outputs require regional calibration and expert validation."
        ),
    }


@router.get("/fields/{field_id}/crops")
def get_crop_suitability(
    field_id: int,
    mean_temp_c: float = Query(27.0),
    seasonal_rainfall_mm: float = Query(1050.0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    field = db.get(Field, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")

    obs = _latest_soil(field_id, db)
    if obs:
        soil_assessment = soil_service.assess_soil(
            ph=obs.ph, soc_pct=obs.soc_pct, nitrogen=obs.nitrogen,
            phosphorus=obs.phosphorus, potassium=obs.potassium,
            ec=obs.ec, sand_pct=obs.sand_pct, silt_pct=obs.silt_pct,
            clay_pct=obs.clay_pct,
        )
    else:
        soil_assessment = soil_service.assess_soil()

    history_names = _crop_history_names(field_id, db)
    penalties = _problem_penalties(field_id, db)
    crops = db.query(Crop).all()

    ranked = suitability_service.rank_crops(
        crops=crops,
        soil=soil_assessment,
        mean_temp_c=mean_temp_c,
        seasonal_rainfall_mm=seasonal_rainfall_mm,
        irrigation_type=field.irrigation_type,
        crop_history=history_names,
        problem_penalties=penalties,
    )

    return {
        "field_id": field_id,
        "ranked_crops": [s.model_dump() for s in ranked],
    }


# ── Crop economics ────────────────────────────────────────────────────────────

@router.get("/crops/{crop_id}/economics")
def get_crop_economics(
    crop_id: int,
    area_ha: float = Query(1.0, gt=0, description="Field area in hectares"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return itemised cost breakdown, revenue, net margin, and ROI
    for a single crop at the given field area.
    Delegates entirely to economics_service — no calculations in this layer.
    """
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    return economics_service.calculate_economics(crop, area_ha=area_ha)


@router.get("/crops/{crop_id}/sensitivity")
def get_crop_sensitivity(
    crop_id: int,
    area_ha: float = Query(1.0, gt=0, description="Field area in hectares"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return Conservative / Expected / Favorable scenario analysis for a crop.
    Delegates entirely to economics_service — no calculations in this layer.
    """
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    result = economics_service.calculate_sensitivity(crop, area_ha=area_ha)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No economic data available for this crop."
        )
    return result
