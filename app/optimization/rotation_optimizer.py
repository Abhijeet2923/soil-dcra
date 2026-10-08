"""
CP-SAT Rotation Optimizer — SoilDCRA MVP.

Uses Google OR-Tools CP-SAT to find an optimal multi-season crop rotation.

Decision variable:
    x[c, s] ∈ {0, 1}  — crop c selected in season s

Constraints enforced:
    1. Exactly one crop per season.
    2. No same crop in consecutive seasons.
    3. Rotation gap rules (minimum_gap from rotation_rules table).
    4. Crop family diversity (same-family gap).
    5. Water availability constraint (exclude high-water crops on low-water fields).
    6. Exclude crops below a minimum suitability threshold.

Objective (maximise weighted sum):
    economic_weight  × normalised margin
    + soil_weight    × soil benefit (legume bonus)
    + diversity_weight × rotation diversity
    - disease_weight × disease risk penalty
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ortools.sat.python import cp_model

from app.core.config import settings
from app.db.models import Crop, CropHistory, RotationRule
from app.schemas.crop import CropSuitabilityScore
from app.services.economics_service import calculate_economics


# ── Constants ────────────────────────────────────────────────────────────────

SCALE = settings.CPSAT_SCALE       # float → int scale factor
MIN_SUITABILITY = 20.0             # crops below this score are excluded


# ── Helper: disease risk score ────────────────────────────────────────────────

def _disease_penalty(risk: str) -> int:
    return {"Low": 0, "Moderate": 15, "High": 40}.get(risk, 0)


def _water_need_int(need: Optional[str]) -> int:
    return {"Low": 1, "Moderate": 2, "High": 3}.get(need or "Moderate", 2)


def _effective_water_level(rainfall_mm: float, irrigation_type: Optional[str]) -> str:
    bonus = {"Irrigated": 400, "Partial": 200, "Rainfed": 0}.get(irrigation_type or "Rainfed", 0)
    total = rainfall_mm + bonus
    if total >= 900:
        return "High"
    if total >= 500:
        return "Moderate"
    return "Low"


# ── Explanation builder ───────────────────────────────────────────────────────

def _build_explanation(
    crop: Crop,
    season: int,
    suitability: CropSuitabilityScore,
    history_names: List[str],
    margin_rs_ha: float,
) -> str:
    parts: List[str] = []

    parts.append(f"{crop.name} was selected for Season {season}.")

    # Soil
    if suitability.soil_score >= 75:
        parts.append("Soil conditions are well-suited (pH and nutrient compatibility).")
    elif suitability.soil_score >= 50:
        parts.append("Soil conditions are moderately suitable.")
    else:
        parts.append("Soil conditions are sub-optimal; remediation recommended.")

    # Climate
    if suitability.climate_score >= 75:
        parts.append("Climate temperature is within the optimal range.")
    elif suitability.climate_score < 50:
        parts.append("Temperature is outside the preferred range — yield may be affected.")

    # Water
    if suitability.water_score >= 75:
        parts.append("Water availability matches crop requirements.")
    elif suitability.water_score < 50:
        parts.append("Water availability may be limiting for this crop.")

    # Rotation
    if crop.family == "Fabaceae":
        parts.append(
            "As a legume, it improves rotation diversity and provides potential "
            "nitrogen fixation benefit for subsequent crops."
        )
    if history_names and history_names[-1] != crop.name:
        parts.append(
            f"Follows {history_names[-1]} — rotation break reduces disease carryover risk."
        )

    # Economics
    parts.append(
        f"Estimated net margin: ₹{margin_rs_ha:,.0f}/ha "
        f"(demonstration estimate — not a guaranteed return)."
    )

    return " ".join(parts)


# ── Soil-benefit score (for objective) ───────────────────────────────────────

def _soil_benefit_score(crop: Crop) -> float:
    """Return 0-100 representing soil improvement benefit of this crop."""
    score = 50.0
    if crop.family == "Fabaceae":
        score += 35.0   # legumes fix nitrogen
    if crop.water_need == "Low":
        score += 10.0   # less waterlogging risk
    return min(100.0, score)


# ── Main optimizer ────────────────────────────────────────────────────────────

def run_optimization(
    field_id: int,
    crops: List[Crop],
    suitability_scores: Dict[int, CropSuitabilityScore],
    crop_history: List[CropHistory],
    rotation_rules: List[RotationRule],
    horizon: int = 4,
    area_ha: float = 1.0,
    irrigation_type: Optional[str] = None,
    rainfall_mm: float = 1050.0,
    economic_weight: float = None,
    soil_weight: float = None,
    diversity_weight: float = None,
    disease_weight: float = None,
) -> Dict[str, Any]:
    """
    Build and solve the CP-SAT crop rotation model.

    Returns a dict with status, rotation list, and aggregate metrics.
    """
    # Use configured weights if not supplied
    ew = economic_weight if economic_weight is not None else settings.OPT_W_ECONOMIC
    sw = soil_weight if soil_weight is not None else settings.OPT_W_SOIL
    dv = diversity_weight if diversity_weight is not None else settings.OPT_W_DIVERSITY
    dw = disease_weight if disease_weight is not None else settings.OPT_W_DISEASE

    # ── Filter out unsuitable crops ───────────────────────────────────────────
    water_level = _effective_water_level(rainfall_mm, irrigation_type)
    eligible: List[Crop] = []
    for crop in crops:
        sc = suitability_scores.get(crop.id)
        if sc is None or sc.final_score < MIN_SUITABILITY:
            continue
        # Exclude high-water crops if water level is Low
        if water_level == "Low" and _water_need_int(crop.water_need) == 3:
            continue
        eligible.append(crop)

    if len(eligible) < 2:
        return {
            "status": "infeasible",
            "error": "Fewer than 2 eligible crops after suitability filtering.",
            "rotation": [],
            "total_expected_margin_rs": 0.0,
            "soil_impact": "Unknown",
            "water_impact": "Unknown",
            "disease_risk": "Unknown",
        }

    C = len(eligible)
    S = horizon
    crop_index = {crop.id: i for i, crop in enumerate(eligible)}

    # History (prior season crop names ordered oldest → most recent)
    def _hist_key(h):
        so = getattr(h, "season_order", None)
        if isinstance(so, (int, float)):
            return so
        s = getattr(h, "season", None)
        if isinstance(s, (int, float)):
            return s
        return 0

    history_names: List[str] = [ch.crop.name for ch in
                                  sorted(crop_history, key=_hist_key)]
    history_crop_ids: List[int] = [ch.crop_id for ch in
                                    sorted(crop_history, key=_hist_key)]

    # ── Build rotation rule lookup: (a_id, b_id) → min_gap ───────────────────
    gap_rules: Dict[tuple, int] = {}
    disease_map: Dict[tuple, str] = {}
    for rr in rotation_rules:
        gap_rules[(rr.crop_a_id, rr.crop_b_id)] = rr.minimum_gap
        disease_map[(rr.crop_a_id, rr.crop_b_id)] = rr.disease_risk

    # ── Economics lookup (per-ha margin) ─────────────────────────────────────
    margins: Dict[int, float] = {}
    for crop in eligible:
        econ = calculate_economics(crop, area_ha=1.0)
        margins[crop.id] = econ.get("net_margin_rs_ha") or 0.0

    # Normalise margins to 0-100 for objective
    max_margin = max(margins.values()) if margins else 1.0
    max_margin = max(max_margin, 1.0)

    # ── CP-SAT model ──────────────────────────────────────────────────────────
    model = cp_model.CpModel()

    # x[c, s] = 1 if eligible[c] is grown in season s
    x = [[model.NewBoolVar(f"x_{c}_{s}") for s in range(S)] for c in range(C)]

    # Constraint 1: exactly one crop per season
    for s in range(S):
        model.Add(sum(x[c][s] for c in range(C)) == 1)

    # Constraint 2: no same crop in consecutive seasons
    for c in range(C):
        for s in range(S - 1):
            model.Add(x[c][s] + x[c][s + 1] <= 1)

    # Constraint 3 & 4: rotation gap rules
    # NOTE: when crop_a == crop_b the rule enforces a minimum rest period for that crop.
    for ci, crop_a in enumerate(eligible):
        for cj, crop_b in enumerate(eligible):
            gap = gap_rules.get((crop_a.id, crop_b.id), 0)
            if ci == cj:
                # Same crop: gap > 1 means it can't appear within `gap` seasons of itself
                # (Constraint 2 already blocks consecutive; here we enforce wider gaps)
                if gap <= 1:
                    continue
                for s in range(S):
                    for g in range(1, min(gap, S - s)):
                        model.Add(x[ci][s] + x[ci][s + g] <= 1)
            else:
                if gap <= 1:
                    continue
                # crop_b cannot be planted within `gap` seasons after crop_a
                for s in range(S):
                    for g in range(1, min(gap, S - s)):
                        model.Add(x[ci][s] + x[cj][s + g] <= 1)

    # Constraint 5: family diversity — same family not in consecutive seasons
    families: Dict[str, List[int]] = {}
    for ci, crop in enumerate(eligible):
        fam = crop.family or "Unknown"
        families.setdefault(fam, []).append(ci)

    for fam, indices in families.items():
        if len(indices) < 2:
            continue
        for s in range(S - 1):
            for ci in indices:
                for cj in indices:
                    if ci < cj:
                        model.Add(x[ci][s] + x[cj][s + 1] <= 1)

    # Constraint 6: History-based gap
    # If the last k crops in history are the same, block that crop in season 0
    for ci, crop in enumerate(eligible):
        if history_crop_ids:
            last_id = history_crop_ids[-1]
            if crop.id == last_id:
                model.Add(x[ci][0] == 0)   # don't repeat same crop immediately

    # ── Objective ────────────────────────────────────────────────────────────
    # All terms scaled to integers
    obj_terms = []
    for c in range(C):
        crop = eligible[c]
        suit = suitability_scores.get(crop.id)
        suit_val = suit.final_score if suit else 50.0

        margin_norm = (margins[crop.id] / max_margin) * 100.0
        soil_ben = _soil_benefit_score(crop)

        # Diversity bonus: reward Fabaceae
        diversity_val = 30.0 if crop.family == "Fabaceae" else 0.0

        composite = (
            ew * margin_norm
            + sw * soil_ben
            + dv * diversity_val
        )
        composite_int = int(composite * SCALE)

        # Disease penalty applied for each pair (history[-1] → this crop)
        disease_pen = 0
        if history_crop_ids:
            key = (history_crop_ids[-1], crop.id)
            risk = disease_map.get(key, "Low")
            disease_pen = int(dw * _disease_penalty(risk) * SCALE)

        for s in range(S):
            obj_terms.append(x[c][s] * (composite_int - disease_pen))

    model.Maximize(sum(obj_terms))

    # ── Solve ─────────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": "infeasible",
            "error": "CP-SAT could not find a feasible rotation.",
            "rotation": [],
            "total_expected_margin_rs": 0.0,
            "soil_impact": "Unknown",
            "water_impact": "Unknown",
            "disease_risk": "Unknown",
        }

    # ── Extract solution ──────────────────────────────────────────────────────
    rotation: List[Dict[str, Any]] = []
    selected_ids: List[int] = []
    total_margin = 0.0
    legume_count = 0
    high_water_count = 0
    disease_flags: List[str] = []

    running_history = list(history_names)

    for s in range(S):
        for c in range(C):
            if solver.Value(x[c][s]) == 1:
                crop = eligible[c]
                suit = suitability_scores.get(crop.id)
                margin_ha = margins[crop.id]
                total_margin_season = margin_ha * area_ha

                explanation = _build_explanation(
                    crop=crop,
                    season=s + 1,
                    suitability=suit,
                    history_names=running_history,
                    margin_rs_ha=margin_ha,
                )

                rotation.append({
                    "season": s + 1,
                    "crop": crop.name,
                    "crop_id": crop.id,
                    "suitability_score": suit.final_score if suit else 0.0,
                    "expected_margin_rs_ha": round(margin_ha, 2),
                    "explanation": explanation,
                })

                selected_ids.append(crop.id)
                total_margin += total_margin_season
                running_history.append(crop.name)

                if crop.family == "Fabaceae":
                    legume_count += 1
                if _water_need_int(crop.water_need) == 3:
                    high_water_count += 1

                # Disease check between consecutive seasons
                if len(selected_ids) >= 2:
                    key = (selected_ids[-2], selected_ids[-1])
                    risk = disease_map.get(key, "Low")
                    if risk == "High":
                        disease_flags.append("High")
                    elif risk == "Moderate":
                        disease_flags.append("Moderate")
                break

    # ── Aggregate impact metrics ──────────────────────────────────────────────
    # Soil impact
    if legume_count >= 2:
        soil_impact = "Positive"
    elif legume_count == 1:
        soil_impact = "Moderate"
    else:
        soil_impact = "Neutral"

    # Water impact
    if high_water_count >= horizon / 2:
        water_impact = "High"
    elif high_water_count >= 1:
        water_impact = "Moderate"
    else:
        water_impact = "Low"

    # Disease risk
    if "High" in disease_flags:
        disease_risk = "High"
    elif "Moderate" in disease_flags:
        disease_risk = "Moderate"
    else:
        disease_risk = "Low"

    return {
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "rotation": rotation,
        "total_expected_margin_rs": round(total_margin, 2),
        "soil_impact": soil_impact,
        "water_impact": water_impact,
        "disease_risk": disease_risk,
    }
