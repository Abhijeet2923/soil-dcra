"""Pydantic schemas for Optimization."""
from typing import List, Optional
from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    horizon: int = Field(4, ge=1, le=12, description="Number of seasons to plan")
    objective: str = "maximize_margin"
    mean_temp_c: float = 27.0
    seasonal_rainfall_mm: float = 1050.0
    dry_season_risk: str = "Moderate"
    heavy_rainfall_risk: str = "Low"


class SeasonResult(BaseModel):
    season: int
    crop: str
    crop_id: int
    suitability_score: float
    expected_margin_rs_ha: float
    explanation: str


class OptimizationRunResult(BaseModel):
    run_id: int
    field_id: int
    planning_horizon: int
    status: str
    rotation: List[SeasonResult]
    total_expected_margin_rs: float
    soil_impact: str
    water_impact: str
    disease_risk: str
    optimization_disclaimer: str = (
        "Demonstration estimates only. Not guaranteed farm-gate returns. "
        "Requires agronomist validation before operational use."
    )


class AnalysisResponse(BaseModel):
    """Full field analysis response from POST /analyze."""
    field_id: int
    field_name: str
    soil_assessment: Optional[object] = None
    degradation: Optional[object] = None
    remote_sensing: Optional[object] = None
    crop_suitability: List[object] = []
    history_summary: List[str] = []
    climate_used: Optional[object] = None
    analysis_disclaimer: str = (
        "This analysis is a rule-based decision-support prototype. "
        "All outputs require regional calibration and expert validation."
    )
