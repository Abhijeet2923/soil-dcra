"""Soil observation API routes."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Field, SoilObservation
from app.schemas.soil import SoilObservationCreate, SoilObservationRead

router = APIRouter(tags=["soil"])


@router.post("/fields/{field_id}/soil", response_model=SoilObservationRead, status_code=201)
def add_soil_observation(
    field_id: int,
    payload: SoilObservationCreate,
    db: Session = Depends(get_db),
):
    if db.get(Field, field_id) is None:
        raise HTTPException(status_code=404, detail="Field not found")
    obs = SoilObservation(field_id=field_id, **payload.model_dump())
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


@router.get("/fields/{field_id}/soil", response_model=List[SoilObservationRead])
def get_soil_observations(field_id: int, db: Session = Depends(get_db)):
    if db.get(Field, field_id) is None:
        raise HTTPException(status_code=404, detail="Field not found")
    return (
        db.query(SoilObservation)
        .filter(SoilObservation.field_id == field_id)
        .order_by(SoilObservation.id.desc())
        .all()
    )
