"""
Crop Suitability Service — rule-based MVP.

Scores every crop against current field state (soil + climate + water + rotation).

DISCLAIMER: Weights are configurable MVP defaults. They are NOT scientifically
optimal for any particular geography. Requires agronomist validation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.db.models import Crop
from app.schemas.crop import CropSuitabilityScore
from app.schemas.soil import SoilAssessment


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def _suitability_level(score: float) -> str:
    if score >= 75:
        return "Excellent"
    if score >= 55:
        return "Good"
    if score >= 35:
        return "Moderate"
    return "Low"


# ── Sub-scorers ──────────────────────────────────────────────────────────────

def _soil_score(crop: Crop, soil: SoilAssessment) -> float:
    """Score 0-100 based on pH fit and SOC."""
    if crop.requirements is None:
        return 50.0

    req = crop.requirements
    ph_val = soil.ph.value
    score = 100.0

    if ph_val is not None and req.ph_min is not None and req.ph_max is not None:
        if ph_val < req.ph_min or ph_val > req.ph_max:
            # Outside range — penalise proportionally
            deviation = min(abs(ph_val - req.ph_min), abs(ph_val - req.ph_max))
            score -= min(60.0, deviation * 20.0)

    # SOC contribution
    if soil.soc.status == "Low":
        score -= 15.0
    elif soil.soc.status == "Moderate":
        score -= 5.0

    # Nutrient contribution
    if soil.nitrogen.status == "Low":
        score -= 10.0
    if soil.potassium.status == "Low":
        score -= 8.0

    return _clamp(score)


def _climate_score(crop: Crop, mean_temp_c: float) -> float:
    """Score 0-100 based on temperature fit."""
    if crop.requirements is None:
        return 50.0

    req = crop.requirements
    if req.temp_min is None or req.temp_max is None:
        return 50.0

    if req.temp_min <= mean_temp_c <= req.temp_max:
        # Optimal range midpoint gives 100
        mid = (req.temp_min + req.temp_max) / 2
        distance = abs(mean_temp_c - mid) / ((req.temp_max - req.temp_min) / 2)
        return _clamp(100.0 - distance * 20.0)

    # Outside range
    if mean_temp_c < req.temp_min:
        deviation = req.temp_min - mean_temp_c
    else:
        deviation = mean_temp_c - req.temp_max
    return _clamp(100.0 - deviation * 15.0)


def _water_score(crop: Crop, rainfall_mm: float, irrigation_type: Optional[str]) -> float:
    """Score 0-100 based on water need vs availability."""
    if crop.requirements is None:
        return 50.0

    req = crop.requirements
    if req.water_min is None or req.water_max is None:
        return 50.0

    # Effective water ≈ rainfall + irrigation uplift
    irrigation_bonus = {
        "Irrigated": 400.0,
        "Partial": 200.0,
        "Rainfed": 0.0,
    }.get(irrigation_type or "Rainfed", 0.0)

    effective_water = rainfall_mm + irrigation_bonus

    if req.water_min <= effective_water <= req.water_max:
        return 100.0
    if effective_water < req.water_min:
        deficit = req.water_min - effective_water
        return _clamp(100.0 - (deficit / req.water_min) * 80.0)
    # Excess water
    excess = effective_water - req.water_max
    return _clamp(100.0 - (excess / req.water_max) * 40.0)


def _season_score(crop: Crop, target_season: Optional[str]) -> float:
    """Score based on season match."""
    if target_season is None or crop.season is None:
        return 60.0
    if crop.season.lower() == target_season.lower():
        return 100.0
    if crop.season.lower() == "both" or target_season.lower() == "both":
        return 80.0
    return 30.0


def _rotation_score(crop: Crop, crop_history: List[str]) -> float:
    """Score 0-100 — penalise repeated crops, reward legumes."""
    score = 70.0

    if not crop_history:
        if crop.family == "Fabaceae":
            score += settings.LEGUME_BONUS
        return _clamp(score)

    last_crop = crop_history[-1] if crop_history else None
    recent = crop_history[-3:] if len(crop_history) >= 3 else crop_history

    # Same crop penalty
    if last_crop and last_crop == crop.name:
        score -= settings.SAME_CROP_PENALTY

    # Same family penalty
    elif last_crop and crop.family:
        # We check by name match within recent history
        if any(h == crop.name for h in recent[:-1]):
            score -= settings.SAME_FAMILY_PENALTY

    # Legume bonus (nitrogen fixation benefit)
    if crop.family == "Fabaceae":
        score += settings.LEGUME_BONUS

    # Extra penalty for same crop appearing multiple times in recent history
    same_count = recent.count(crop.name)
    if same_count >= 2:
        score -= 20.0

    return _clamp(score)


def _economic_score(crop: Crop) -> float:
    """Normalised economic attractiveness 0-100."""
    if crop.economics is None:
        return 50.0
    econ = crop.economics
    cost = getattr(econ, "total_cost_rs_ha", None) or getattr(econ, "variable_cost_rs_per_ha", None)
    if econ.expected_yield_t_ha and econ.price_rs_per_t and cost:
        revenue = econ.expected_yield_t_ha * econ.price_rs_per_t
        margin = revenue - cost
        # Normalise: assume max reasonable margin ~₹100,000/ha
        return _clamp((margin / 100_000.0) * 100.0)
    return 50.0


# ── Public API ───────────────────────────────────────────────────────────────

def score_crop(
    crop: Crop,
    soil: SoilAssessment,
    mean_temp_c: float = 27.0,
    seasonal_rainfall_mm: float = 1050.0,
    irrigation_type: Optional[str] = None,
    target_season: Optional[str] = None,
    crop_history: Optional[List[str]] = None,
    problem_penalties: Optional[dict] = None,
) -> CropSuitabilityScore:
    """
    Compute a full suitability score for a single crop.
    problem_penalties: dict with keys water_penalty, rotation_penalty, soil_penalty
    """
    if crop_history is None:
        crop_history = []
    if problem_penalties is None:
        problem_penalties = {}

    ss = _clamp(_soil_score(crop, soil) - problem_penalties.get("soil_penalty", 0))
    cs = _climate_score(crop, mean_temp_c)
    ws = _clamp(_water_score(crop, seasonal_rainfall_mm, irrigation_type)
                - problem_penalties.get("water_penalty", 0))
    sns = _season_score(crop, target_season)
    rs = _clamp(_rotation_score(crop, crop_history)
                - problem_penalties.get("rotation_penalty", 0))
    es = _economic_score(crop)

    final = (
        settings.CS_W_SOIL     * ss
        + settings.CS_W_CLIMATE  * cs
        + settings.CS_W_WATER    * ws
        + settings.CS_W_SEASON   * sns
        + settings.CS_W_ROTATION * rs
        + settings.CS_W_ECONOMIC * es
    )

    return CropSuitabilityScore(
        crop_id=crop.id,
        crop_name=crop.name,
        soil_score=round(ss, 1),
        climate_score=round(cs, 1),
        water_score=round(ws, 1),
        season_score=round(sns, 1),
        rotation_score=round(rs, 1),
        economic_score=round(es, 1),
        final_score=round(final, 1),
        suitability_level=_suitability_level(final),
    )


def rank_crops(
    crops: List[Crop],
    soil: SoilAssessment,
    mean_temp_c: float = 27.0,
    seasonal_rainfall_mm: float = 1050.0,
    irrigation_type: Optional[str] = None,
    target_season: Optional[str] = None,
    crop_history: Optional[List[str]] = None,
    problem_penalties: Optional[dict] = None,
) -> List[CropSuitabilityScore]:
    """Score and rank all crops for the current field conditions."""
    scores = [
        score_crop(
            crop, soil, mean_temp_c, seasonal_rainfall_mm,
            irrigation_type, target_season, crop_history,
            problem_penalties,
        )
        for crop in crops
    ]
    return sorted(scores, key=lambda s: s.final_score, reverse=True)
