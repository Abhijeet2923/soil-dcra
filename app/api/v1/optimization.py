"""
Optimization API routes.
POST /fields/{field_id}/optimize
GET  /optimization/{run_id}
GET  /fields/{field_id}/optimization-runs
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import (
    Crop, CropHistory, Field, OptimizationResult, OptimizationRun,
    RotationRule, SoilObservation,
)
from app.optimization.rotation_optimizer import run_optimization
from app.schemas.crop import ClimateInput
from app.schemas.optimization import OptimizeRequest
from app.services import soil_service, suitability_service

router = APIRouter(tags=["optimization"])


def _latest_soil(field_id: int, db: Session):
    return (
        db.query(SoilObservation)
        .filter(SoilObservation.field_id == field_id)
        .order_by(SoilObservation.id.desc())
        .first()
    )


@router.post("/fields/{field_id}/optimize")
def optimize_rotation(
    field_id: int,
    payload: OptimizeRequest = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run CP-SAT crop rotation optimizer for this field.

    Pipeline:
    load field → soil → crop history → suitability →
    economics → rotation rules → CP-SAT → explanation → persist → return
    """
    if payload is None:
        payload = OptimizeRequest()

    field = db.get(Field, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")

    # Soil assessment
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
    history_rows = (
        db.query(CropHistory)
        .filter(CropHistory.field_id == field_id)
        .order_by(CropHistory.season_order)
        .all()
    )

    # Rank all crops
    crops = db.query(Crop).all()
    ranked = suitability_service.rank_crops(
        crops=crops,
        soil=soil_assessment,
        mean_temp_c=payload.mean_temp_c,
        seasonal_rainfall_mm=payload.seasonal_rainfall_mm,
        irrigation_type=field.irrigation_type,
        crop_history=[r.crop.name for r in history_rows],
    )
    suitability_map = {s.crop_id: s for s in ranked}

    # Rotation rules
    rotation_rules = db.query(RotationRule).all()

    # Create optimization run record
    run = OptimizationRun(
        field_id=field_id,
        horizon=payload.horizon,
        objective=payload.objective,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Run optimizer
    result = run_optimization(
        field_id=field_id,
        crops=crops,
        suitability_scores=suitability_map,
        crop_history=history_rows,
        rotation_rules=rotation_rules,
        horizon=payload.horizon,
        area_ha=field.area_ha,
        irrigation_type=field.irrigation_type,
        rainfall_mm=payload.seasonal_rainfall_mm,
    )

    # Update run status
    run.status = result["status"]
    db.commit()

    # Persist results
    for season_data in result.get("rotation", []):
        db.add(OptimizationResult(
            run_id=run.id,
            season=season_data["season"],
            crop_id=season_data["crop_id"],
            suitability_score=season_data["suitability_score"],
            expected_margin=season_data["expected_margin_rs_ha"] * field.area_ha,
            explanation=season_data["explanation"],
        ))
    db.commit()

    return {
        "run_id": run.id,
        "field_id": field_id,
        "planning_horizon": payload.horizon,
        "status": result["status"],
        "rotation": result.get("rotation", []),
        "total_expected_margin_rs": result.get("total_expected_margin_rs", 0.0),
        "soil_impact": result.get("soil_impact"),
        "water_impact": result.get("water_impact"),
        "disease_risk": result.get("disease_risk"),
        "optimization_disclaimer": (
            "Demonstration estimates only. Not guaranteed farm-gate returns. "
            "Requires agronomist validation before operational use."
        ),
    }


@router.get("/optimization/{run_id}")
def get_optimization_result(run_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve a previously saved optimization run."""
    run = db.get(OptimizationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Optimization run not found")

    results = (
        db.query(OptimizationResult)
        .filter(OptimizationResult.run_id == run_id)
        .order_by(OptimizationResult.season)
        .all()
    )

    rotation = [
        {
            "season": r.season,
            "crop": r.crop.name,
            "crop_id": r.crop_id,
            "suitability_score": r.suitability_score,
            "expected_margin_rs_total": r.expected_margin,
            "explanation": r.explanation,
        }
        for r in results
    ]

    total_margin = sum(r.expected_margin or 0.0 for r in results)

    return {
        "run_id": run_id,
        "field_id": run.field_id,
        "planning_horizon": run.horizon,
        "status": run.status,
        "created_at": str(run.created_at),
        "rotation": rotation,
        "total_expected_margin_rs": round(total_margin, 2),
    }


@router.get("/fields/{field_id}/optimization-runs")
def list_optimization_runs(
    field_id: int,
    db: Session = Depends(get_db),
) -> list:
    """List all past optimization runs for a field (most recent first)."""
    field = db.get(Field, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")

    runs = (
        db.query(OptimizationRun)
        .filter(OptimizationRun.field_id == field_id)
        .order_by(OptimizationRun.id.desc())
        .all()
    )
    return [
        {
            "run_id": r.id,
            "field_id": r.field_id,
            "horizon": r.horizon,
            "objective": r.objective,
            "status": r.status,
            "created_at": str(r.created_at),
        }
        for r in runs
    ]
