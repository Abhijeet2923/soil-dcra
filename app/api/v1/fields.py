"""Field API routes."""
import json
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import (
    Crop, CropHistory, Field as FieldModel,
    FieldProblem, FertilizerProduct, FertilizerUsage,
)

router = APIRouter(tags=["fields"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class FieldCreate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_ha: float = Field(1.0, gt=0)
    irrigation_type: Optional[str] = None
    current_crop: Optional[str] = None
    farm_name: Optional[str] = None
    farming_type: Optional[str] = None
    soil_type: Optional[str] = None
    boundary_geojson: Optional[str] = None


class FieldRead(BaseModel):
    id: int
    name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    area_ha: float
    irrigation_type: Optional[str]
    current_crop: Optional[str]
    farm_name: Optional[str]
    farming_type: Optional[str]
    soil_type: Optional[str]
    boundary_geojson: Optional[str]
    model_config = {"from_attributes": True}


class CropHistoryCreate(BaseModel):
    season_order: int
    season_name: Optional[str] = None
    season_type: Optional[str] = None
    year: Optional[int] = None
    crop_id: int
    sowing_date: Optional[str] = None
    harvest_date: Optional[str] = None
    duration_days: Optional[int] = None
    cultivated_area_ha: Optional[float] = None
    production_qty: Optional[float] = None
    production_unit: Optional[str] = "tonnes"
    yield_t_ha: Optional[float] = None
    notes: Optional[str] = None


class CropHistoryRead(CropHistoryCreate):
    id: int
    field_id: int
    crop_name: Optional[str] = None
    model_config = {"from_attributes": True}


class ProblemCreate(BaseModel):
    season_name: Optional[str] = None
    problem_code: str
    problem_label: Optional[str] = None
    severity: Optional[str] = "Moderate"
    notes: Optional[str] = None


class ProblemRead(ProblemCreate):
    id: int
    field_id: int
    model_config = {"from_attributes": True}


class FertilizerUsageCreate(BaseModel):
    fertilizer_id: int
    season_name: Optional[str] = None
    quantity_kg_ha: Optional[float] = None
    total_cost_rs: Optional[float] = None
    notes: Optional[str] = None


class FertilizerUsageRead(FertilizerUsageCreate):
    id: int
    field_id: int
    fertilizer_name: Optional[str] = None
    model_config = {"from_attributes": True}


class FertilizerProductRead(BaseModel):
    id: int
    name: str
    n_pct: Optional[float]
    p_pct: Optional[float]
    k_pct: Optional[float]
    cost_rs_per_50kg: Optional[float]
    unit: Optional[str]
    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Approximate distance in km between two coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _field_to_read(f: FieldModel) -> dict:
    return {
        "id": f.id, "name": f.name, "latitude": f.latitude,
        "longitude": f.longitude, "area_ha": f.area_ha,
        "irrigation_type": f.irrigation_type, "current_crop": f.current_crop,
        "farm_name": f.farm_name, "farming_type": f.farming_type,
        "soil_type": f.soil_type, "boundary_geojson": f.boundary_geojson,
    }


# ── Field CRUD ────────────────────────────────────────────────────────────────

@router.post("/fields/", response_model=FieldRead, status_code=201)
def create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    field = FieldModel(**payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/fields/{field_id}", response_model=FieldRead)
def get_field(field_id: int, db: Session = Depends(get_db)):
    field = db.get(FieldModel, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.patch("/fields/{field_id}", response_model=FieldRead)
def update_field(field_id: int, payload: FieldCreate, db: Session = Depends(get_db)):
    """Update mutable field properties (area, irrigation, name, etc.)."""
    field = db.get(FieldModel, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(field, k, v)
    db.commit()
    db.refresh(field)
    return field


@router.post("/fields/find-or-create")
def find_or_create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    """
    Find an existing field within ~500m of the given coordinates,
    or create a new one. Returns field with created=True/False flag.
    """
    if payload.latitude and payload.longitude:
        # Check existing fields within ~500m
        all_fields = db.query(FieldModel).filter(
            FieldModel.latitude.isnot(None)
        ).all()
        for f in all_fields:
            dist = _haversine_km(payload.latitude, payload.longitude,
                                  f.latitude, f.longitude)
            if dist < 0.5:  # within 500m
                return {**_field_to_read(f), "created": False}

    # Create new
    field = FieldModel(**payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return {**_field_to_read(field), "created": True}


# ── Crop history ──────────────────────────────────────────────────────────────

@router.post("/fields/{field_id}/history", status_code=201)
def add_crop_history(field_id: int, payload: CropHistoryCreate,
                     db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    # Auto-calculate yield if qty and area both given
    if (payload.production_qty and payload.cultivated_area_ha
            and payload.cultivated_area_ha > 0 and not payload.yield_t_ha):
        qty_t = payload.production_qty
        if payload.production_unit == "kg":
            qty_t = payload.production_qty / 1000.0
        elif payload.production_unit == "quintal":
            qty_t = payload.production_qty / 10.0
        payload = payload.model_copy(
            update={"yield_t_ha": round(qty_t / payload.cultivated_area_ha, 3)}
        )
    row = CropHistory(field_id=field_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    result = payload.model_dump()
    result["id"] = row.id
    result["field_id"] = field_id
    result["crop_name"] = row.crop.name if row.crop else None
    return result


@router.get("/fields/{field_id}/history")
def get_crop_history(field_id: int, db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    rows = (db.query(CropHistory)
            .filter(CropHistory.field_id == field_id)
            .order_by(CropHistory.season_order)
            .all())
    return [
        {
            "id": r.id, "field_id": r.field_id,
            "season_order": r.season_order, "season_name": r.season_name,
            "season_type": r.season_type, "year": r.year,
            "crop_id": r.crop_id, "crop_name": r.crop.name if r.crop else None,
            "sowing_date": r.sowing_date, "harvest_date": r.harvest_date,
            "duration_days": r.duration_days,
            "cultivated_area_ha": r.cultivated_area_ha,
            "production_qty": r.production_qty,
            "production_unit": r.production_unit,
            "yield_t_ha": r.yield_t_ha, "notes": r.notes,
        }
        for r in rows
    ]


@router.delete("/fields/{field_id}/history", status_code=204)
def clear_crop_history(field_id: int, db: Session = Depends(get_db)):
    """Clear all crop history for a field (for re-entry)."""
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    db.query(CropHistory).filter(CropHistory.field_id == field_id).delete()
    db.commit()


# ── Problems ──────────────────────────────────────────────────────────────────

@router.post("/fields/{field_id}/problems", status_code=201)
def add_problem(field_id: int, payload: ProblemCreate,
                db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    row = FieldProblem(field_id=field_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "field_id": row.field_id, **payload.model_dump()}


@router.get("/fields/{field_id}/problems")
def get_problems(field_id: int, db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    rows = (db.query(FieldProblem)
            .filter(FieldProblem.field_id == field_id)
            .order_by(FieldProblem.id)
            .all())
    return [
        {"id": r.id, "field_id": r.field_id, "season_name": r.season_name,
         "problem_code": r.problem_code, "problem_label": r.problem_label,
         "severity": r.severity, "notes": r.notes}
        for r in rows
    ]


@router.delete("/fields/{field_id}/problems", status_code=204)
def clear_problems(field_id: int, db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    db.query(FieldProblem).filter(FieldProblem.field_id == field_id).delete()
    db.commit()


# ── Fertilizers ───────────────────────────────────────────────────────────────

@router.get("/fertilizers")
def list_fertilizers(db: Session = Depends(get_db)):
    """List all available fertilizer products."""
    rows = db.query(FertilizerProduct).order_by(FertilizerProduct.name).all()
    return [
        {"id": r.id, "name": r.name, "n_pct": r.n_pct, "p_pct": r.p_pct,
         "k_pct": r.k_pct, "cost_rs_per_50kg": r.cost_rs_per_50kg, "unit": r.unit}
        for r in rows
    ]


@router.post("/fields/{field_id}/fertilizers", status_code=201)
def add_fertilizer_usage(field_id: int, payload: FertilizerUsageCreate,
                          db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    row = FertilizerUsage(field_id=field_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    name = row.product.name if row.product else None
    return {"id": row.id, "field_id": field_id,
            "fertilizer_name": name, **payload.model_dump()}


@router.get("/fields/{field_id}/fertilizers")
def get_fertilizer_usage(field_id: int, db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    rows = (db.query(FertilizerUsage)
            .filter(FertilizerUsage.field_id == field_id)
            .order_by(FertilizerUsage.id)
            .all())
    return [
        {"id": r.id, "field_id": r.field_id,
         "fertilizer_id": r.fertilizer_id,
         "fertilizer_name": r.product.name if r.product else None,
         "season_name": r.season_name, "quantity_kg_ha": r.quantity_kg_ha,
         "total_cost_rs": r.total_cost_rs, "notes": r.notes}
        for r in rows
    ]


@router.delete("/fields/{field_id}/fertilizers", status_code=204)
def clear_fertilizer_usage(field_id: int, db: Session = Depends(get_db)):
    if db.get(FieldModel, field_id) is None:
        raise HTTPException(404, "Field not found")
    db.query(FertilizerUsage).filter(FertilizerUsage.field_id == field_id).delete()
    db.commit()


# ── Crop list ─────────────────────────────────────────────────────────────────

@router.get("/crops")
def list_all_crops(db: Session = Depends(get_db)):
    """Return all available crops for dropdown population."""
    rows = db.query(Crop).order_by(Crop.name).all()
    return [
        {"id": r.id, "name": r.name, "family": r.family, "season": r.season,
         "water_need": r.water_need, "duration_days": r.duration_days,
         "sowing_window": r.sowing_window, "harvest_window": r.harvest_window}
        for r in rows
    ]


# ── Fields list ───────────────────────────────────────────────────────────────

@router.get("/fields")
def list_all_fields(db: Session = Depends(get_db)):
    """Return all registered fields (for returning-user field selector)."""
    rows = db.query(FieldModel).order_by(FieldModel.id.desc()).all()
    return [_field_to_read(f) for f in rows]


# ── Problem types catalogue ───────────────────────────────────────────────────

@router.get("/problem-types")
def list_problem_types():
    """Return the full problem type catalogue for the React multiselect."""
    from app.data.crop_data import PROBLEM_TYPES
    return PROBLEM_TYPES
