"""Pydantic schemas for Soil observations."""
from typing import Optional

from pydantic import BaseModel, Field


class SoilObservationCreate(BaseModel):
    sample_date: Optional[str] = None
    ph: Optional[float] = Field(None, ge=0, le=14)
    soc_pct: Optional[float] = Field(None, ge=0, le=100,
        description="SOC concentration in % — NOT SOC stock")
    nitrogen: Optional[float] = Field(None, ge=0, description="g/kg")
    phosphorus: Optional[float] = Field(None, ge=0, description="mg/kg")
    potassium: Optional[float] = Field(None, ge=0, description="mg/kg")
    ec: Optional[float] = Field(None, ge=0, description="dS/m")
    sand_pct: Optional[float] = Field(None, ge=0, le=100)
    silt_pct: Optional[float] = Field(None, ge=0, le=100)
    clay_pct: Optional[float] = Field(None, ge=0, le=100)


class SoilObservationRead(SoilObservationCreate):
    id: int
    field_id: int

    model_config = {"from_attributes": True}


class SoilIndicator(BaseModel):
    """Single soil parameter status result."""
    value: Optional[float]
    status: str   # Low | Moderate | Good
    score: float  # 0-100


class SoilAssessment(BaseModel):
    """Full soil health assessment result."""
    ph: SoilIndicator
    soc: SoilIndicator
    nitrogen: SoilIndicator
    phosphorus: SoilIndicator
    potassium: SoilIndicator
    ec: SoilIndicator
    soil_health_score: float      # 0-100
    degradation_risk_score: float # 0-100
    risk_level: str               # Low | Moderate | High | Critical
    texture_class: Optional[str]  # USDA texture triangle approximation
    disclaimer: str = (
        "Rule-based MVP thresholds. Requires regional calibration "
        "and agricultural expert validation."
    )
