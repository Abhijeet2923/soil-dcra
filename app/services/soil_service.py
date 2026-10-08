"""
Soil Health Service — rule-based MVP.

DISCLAIMER: All thresholds are configurable MVP defaults.
They require regional calibration and agricultural expert validation.
They are NOT universally validated soil health standards.
"""
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.schemas.soil import SoilAssessment, SoilIndicator


# ── Scoring helpers ──────────────────────────────────────────────────────────

def _score_ph(ph: Optional[float]) -> SoilIndicator:
    if ph is None:
        return SoilIndicator(value=None, status="Unknown", score=50.0)
    if ph < settings.PH_LOW_MAX or ph > settings.PH_HIGH_MIN:
        return SoilIndicator(value=ph, status="Low", score=25.0)
    # Optimal range 6.0-7.0 → Good; outside but within limits → Moderate
    if 6.0 <= ph <= 7.0:
        return SoilIndicator(value=ph, status="Good", score=100.0)
    return SoilIndicator(value=ph, status="Moderate", score=60.0)


def _score_soc(soc: Optional[float]) -> SoilIndicator:
    """SOC concentration (%)."""
    if soc is None:
        return SoilIndicator(value=None, status="Unknown", score=50.0)
    if soc < settings.SOC_LOW_MAX:
        return SoilIndicator(value=soc, status="Low", score=20.0)
    if soc < settings.SOC_MODERATE_MAX:
        return SoilIndicator(value=soc, status="Moderate", score=60.0)
    return SoilIndicator(value=soc, status="Good", score=100.0)


def _score_nitrogen(n: Optional[float]) -> SoilIndicator:
    if n is None:
        return SoilIndicator(value=None, status="Unknown", score=50.0)
    if n < settings.N_LOW_MAX:
        return SoilIndicator(value=n, status="Low", score=20.0)
    if n < settings.N_MODERATE_MAX:
        return SoilIndicator(value=n, status="Moderate", score=60.0)
    return SoilIndicator(value=n, status="Good", score=100.0)


def _score_phosphorus(p: Optional[float]) -> SoilIndicator:
    if p is None:
        return SoilIndicator(value=None, status="Unknown", score=50.0)
    if p < settings.P_LOW_MAX:
        return SoilIndicator(value=p, status="Low", score=20.0)
    if p < settings.P_MODERATE_MAX:
        return SoilIndicator(value=p, status="Moderate", score=60.0)
    return SoilIndicator(value=p, status="Good", score=100.0)


def _score_potassium(k: Optional[float]) -> SoilIndicator:
    if k is None:
        return SoilIndicator(value=None, status="Unknown", score=50.0)
    if k < settings.K_LOW_MAX:
        return SoilIndicator(value=k, status="Low", score=20.0)
    if k < settings.K_MODERATE_MAX:
        return SoilIndicator(value=k, status="Moderate", score=60.0)
    return SoilIndicator(value=k, status="Good", score=100.0)


def _score_ec(ec: Optional[float]) -> SoilIndicator:
    """EC: lower is better for most crops."""
    if ec is None:
        return SoilIndicator(value=None, status="Unknown", score=50.0)
    if ec >= settings.EC_HIGH_MIN:
        return SoilIndicator(value=ec, status="Low", score=10.0)   # high salinity
    if ec >= settings.EC_MODERATE_MIN:
        return SoilIndicator(value=ec, status="Moderate", score=50.0)
    return SoilIndicator(value=ec, status="Good", score=100.0)


def _texture_class(sand: Optional[float], silt: Optional[float], clay: Optional[float]) -> Optional[str]:
    """Very simplified USDA-like texture class."""
    if sand is None or silt is None or clay is None:
        return None
    if clay >= 40:
        return "Clay"
    if clay >= 27 and sand <= 45:
        return "Clay Loam"
    if silt >= 50:
        return "Silt Loam"
    if sand >= 70:
        return "Sandy Loam"
    return "Loam"


def _risk_level(score: float) -> str:
    if score >= 70:
        return "Low"
    if score >= 45:
        return "Moderate"
    if score >= 25:
        return "High"
    return "Critical"


# ── Public API ───────────────────────────────────────────────────────────────

def assess_soil(
    ph: Optional[float] = None,
    soc_pct: Optional[float] = None,
    nitrogen: Optional[float] = None,
    phosphorus: Optional[float] = None,
    potassium: Optional[float] = None,
    ec: Optional[float] = None,
    sand_pct: Optional[float] = None,
    silt_pct: Optional[float] = None,
    clay_pct: Optional[float] = None,
) -> SoilAssessment:
    """
    Compute rule-based soil health assessment.

    Returns SoilAssessment with per-parameter indicators and composite scores.
    """
    ph_ind = _score_ph(ph)
    soc_ind = _score_soc(soc_pct)
    n_ind = _score_nitrogen(nitrogen)
    p_ind = _score_phosphorus(phosphorus)
    k_ind = _score_potassium(potassium)
    ec_ind = _score_ec(ec)

    health_score = (
        settings.W_PH  * ph_ind.score
        + settings.W_SOC * soc_ind.score
        + settings.W_N   * n_ind.score
        + settings.W_P   * p_ind.score
        + settings.W_K   * k_ind.score
        + settings.W_EC  * ec_ind.score
    )
    degradation_score = 100.0 - health_score

    return SoilAssessment(
        ph=ph_ind,
        soc=soc_ind,
        nitrogen=n_ind,
        phosphorus=p_ind,
        potassium=k_ind,
        ec=ec_ind,
        soil_health_score=round(health_score, 2),
        degradation_risk_score=round(degradation_score, 2),
        risk_level=_risk_level(health_score),
        texture_class=_texture_class(sand_pct, silt_pct, clay_pct),
    )
