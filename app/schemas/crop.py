"""Pydantic schemas for Crops and Suitability."""
from typing import Optional
from pydantic import BaseModel


class CropRead(BaseModel):
    id: int
    name: str
    family: Optional[str]
    season: Optional[str]
    water_need: Optional[str]
    duration_days: Optional[int]

    model_config = {"from_attributes": True}


class CropSuitabilityScore(BaseModel):
    """Suitability breakdown for a single crop against the current field state."""
    crop_id: int
    crop_name: str
    soil_score: float
    climate_score: float
    water_score: float
    season_score: float
    rotation_score: float
    economic_score: float
    final_score: float   # weighted composite
    suitability_level: str  # Low | Moderate | Good | Excellent
    disclaimer: str = (
        "Demonstration suitability estimate. Weights are configurable and "
        "require agronomist validation."
    )


class ClimateInput(BaseModel):
    """Simple manual climate input for MVP."""
    mean_temp_c: float = 27.0
    seasonal_rainfall_mm: float = 1050.0
    dry_season_risk: str = "Moderate"   # Low | Moderate | High
    heavy_rainfall_risk: str = "Low"
