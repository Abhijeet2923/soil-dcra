"""
Degradation Assessment Service — rule-based MVP.

Combines soil chemistry, remote sensing proxies, and crop history
to produce a degradation risk assessment with named drivers.

DISCLAIMER: All weights and thresholds are configurable MVP defaults
requiring regional calibration and expert validation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.schemas.soil import SoilAssessment


# Remote sensing demo provider ──────────────────────────────────────────────

def get_demo_remote_sensing() -> Dict[str, Any]:
    """
    Demo/pre-computed remote sensing indices.
    In production replace with a real SentinelProvider.
    """
    return {
        "ndvi_mean": 0.62,
        "ndmi_mean": 0.31,
        "bsi_mean": 0.18,
        "source": "demo_precomputed",
        "disclaimer": (
            "Pre-computed demonstration values. "
            "Live Sentinel-2 integration required for operational use."
        ),
    }


def _ndvi_risk(ndvi: float) -> str:
    if ndvi >= 0.6:
        return "Low"
    if ndvi >= 0.4:
        return "Moderate"
    return "High"


def _bsi_risk(bsi: float) -> str:
    if bsi <= 0.10:
        return "Low"
    if bsi <= 0.25:
        return "Moderate"
    return "High"


# History analysis ────────────────────────────────────────────────────────────

def _history_risk(history: List[str]) -> tuple[str, List[str]]:
    """
    Assess degradation risk from crop history.
    Returns (risk_level, driver_notes).
    """
    if not history:
        return "Low", []

    drivers: List[str] = []
    # Count consecutive same crop
    same_run = 1
    for i in range(1, len(history)):
        if history[i] == history[i - 1]:
            same_run += 1
        else:
            same_run = 1

    if same_run >= 3:
        drivers.append(f"Repeated {history[-1]} cultivation ({same_run} consecutive seasons)")
        return "High", drivers
    if same_run == 2:
        drivers.append(f"Two consecutive {history[-1]} seasons")
        return "Moderate", drivers

    # Count distinct crops
    unique = len(set(history))
    if unique == 1:
        drivers.append("No crop rotation detected")
        return "High", drivers
    if unique < len(history) / 2:
        drivers.append("Low rotation diversity")
        return "Moderate", drivers

    return "Low", drivers


# Main function ───────────────────────────────────────────────────────────────

def assess_degradation(
    soil: SoilAssessment,
    crop_history: Optional[List[str]] = None,
    rs_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Produce a multi-factor degradation assessment.

    Parameters
    ----------
    soil:          SoilAssessment from soil_service.assess_soil()
    crop_history:  list of crop names in chronological order (oldest first)
    rs_data:       remote sensing dict (use get_demo_remote_sensing() if None)
    """
    if crop_history is None:
        crop_history = []
    if rs_data is None:
        rs_data = get_demo_remote_sensing()

    drivers: List[str] = []

    # SOC risk
    soc_risk = soil.soc.status
    if soc_risk == "Low":
        drivers.append("Low SOC (organic matter depletion)")

    # Nutrient risk — aggregate N, P, K
    nutrient_scores = [soil.nitrogen.score, soil.phosphorus.score, soil.potassium.score]
    avg_nutrient = sum(nutrient_scores) / len(nutrient_scores)
    if avg_nutrient < 30:
        nutrient_risk = "High"
        drivers.append("Low macronutrient levels (N/P/K)")
    elif avg_nutrient < 65:
        nutrient_risk = "Moderate"
    else:
        nutrient_risk = "Low"

    if soil.potassium.status == "Low":
        drivers.append("Low potassium")

    # EC / salinity risk
    water_risk = "Low"
    if soil.ec.status == "Low":   # Low EC status means high salinity
        water_risk = "High"
        drivers.append("High soil salinity (EC)")
    elif soil.ec.status == "Moderate":
        water_risk = "Moderate"

    # Remote sensing vegetation risk
    ndvi = rs_data.get("ndvi_mean", 0.62)
    bsi = rs_data.get("bsi_mean", 0.18)
    vegetation_risk = _ndvi_risk(ndvi)
    bare_soil_risk = _bsi_risk(bsi)
    if vegetation_risk in ("Moderate", "High"):
        drivers.append(f"Reduced vegetation cover (NDVI={ndvi:.2f})")

    # Crop history risk
    history_risk, history_drivers = _history_risk(crop_history)
    drivers.extend(history_drivers)

    # Combine into overall score
    risk_map = {"Low": 10, "Moderate": 40, "High": 70, "Critical": 90}
    component_risks = [
        risk_map.get(soc_risk, 40),
        risk_map.get(nutrient_risk, 40),
        risk_map.get(water_risk, 10),
        risk_map.get(vegetation_risk, 10),
        risk_map.get(history_risk, 10),
    ]
    # Weighted: SOC and nutrients matter most
    weights = [0.25, 0.25, 0.15, 0.15, 0.20]
    overall_score = sum(w * v for w, v in zip(weights, component_risks))

    if overall_score >= 60:
        overall_risk = "High"
    elif overall_score >= 35:
        overall_risk = "Moderate"
    else:
        overall_risk = "Low"

    return {
        "overall_degradation_score": round(overall_score, 1),
        "risk_level": overall_risk,
        "soc_risk": soc_risk,
        "nutrient_risk": nutrient_risk,
        "water_risk": water_risk,
        "vegetation_risk": vegetation_risk,
        "bare_soil_risk": bare_soil_risk,
        "history_risk": history_risk,
        "main_drivers": drivers if drivers else ["No significant degradation drivers identified"],
        "remote_sensing": rs_data,
        "disclaimer": (
            "Rule-based degradation prototype. Score does NOT represent a "
            "scientifically validated universal soil degradation index."
        ),
    }
