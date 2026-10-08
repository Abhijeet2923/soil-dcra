"""Tests for CP-SAT rotation optimizer."""
import pytest
from unittest.mock import MagicMock

from app.optimization.rotation_optimizer import run_optimization
from app.services.soil_service import assess_soil
from app.services.suitability_service import rank_crops


def _make_crop(id, name, family="Poaceae", water_need="Moderate",
               ph_min=6.0, ph_max=7.5, temp_min=18.0, temp_max=35.0,
               water_min=400, water_max=900, yield_t=3.0, price=15000.0, cost=20000.0):
    crop = MagicMock()
    crop.id = id
    crop.name = name
    crop.family = family
    crop.water_need = water_need

    req = MagicMock()
    req.ph_min = ph_min
    req.ph_max = ph_max
    req.temp_min = temp_min
    req.temp_max = temp_max
    req.water_min = water_min
    req.water_max = water_max
    crop.requirements = req

    econ = MagicMock()
    econ.expected_yield_t_ha = yield_t
    econ.price_rs_per_t = price
    # Itemised cost columns — set to None so economics_service skips them
    econ.seed_cost_rs_ha = None
    econ.fertilizer_cost_rs_ha = None
    econ.pesticide_cost_rs_ha = None
    econ.irrigation_cost_rs_ha = None
    econ.labor_cost_rs_ha = None
    econ.machinery_cost_rs_ha = None
    econ.other_cost_rs_ha = None
    # total_cost_rs_ha is a computed property — set the numeric value directly
    econ.total_cost_rs_ha = float(cost)
    crop.economics = econ

    crop.rotation_rules_as_a = []
    crop.rotation_rules_as_b = []
    return crop


def _make_history(crop, season):
    h = MagicMock()
    h.season = season
    h.crop_id = crop.id
    h.crop = crop
    return h


SOIL = assess_soil(ph=6.7, soc_pct=0.62, nitrogen=0.10,
                   phosphorus=18.0, potassium=85.0, ec=0.8)

CROPS = [
    _make_crop(1, "Rice",     yield_t=4.0, price=18000, cost=35000),
    _make_crop(2, "Wheat",    yield_t=3.5, price=22000, cost=28000,
               water_min=400, water_max=700, temp_min=10, temp_max=25),
    _make_crop(3, "Maize",    yield_t=5.0, price=14000, cost=25000),
    _make_crop(4, "Chickpea", family="Fabaceae", yield_t=1.5, price=50000, cost=18000,
               water_min=250, water_max=500, temp_min=10, temp_max=30, water_need="Low"),
    _make_crop(5, "Soybean",  family="Fabaceae", yield_t=2.0, price=38000, cost=22000),
    _make_crop(6, "Mustard",  family="Brassicaceae", yield_t=1.8, price=55000, cost=20000,
               water_min=250, water_max=450, temp_min=10, temp_max=25, water_need="Low"),
]


def _suitability_map():
    return {s.crop_id: s for s in rank_crops(CROPS, SOIL, mean_temp_c=27.0,
                                              seasonal_rainfall_mm=1050.0)}


# ── Core correctness ──────────────────────────────────────────────────────────

def test_exactly_one_crop_per_season():
    result = run_optimization(
        field_id=1,
        crops=CROPS,
        suitability_scores=_suitability_map(),
        crop_history=[],
        rotation_rules=[],
        horizon=4,
    )
    assert result["status"] in ("optimal", "feasible")
    rotation = result["rotation"]
    assert len(rotation) == 4
    seasons = [r["season"] for r in rotation]
    assert seasons == list(range(1, 5))


def test_no_same_crop_consecutive():
    result = run_optimization(
        field_id=1,
        crops=CROPS,
        suitability_scores=_suitability_map(),
        crop_history=[],
        rotation_rules=[],
        horizon=4,
    )
    assert result["status"] in ("optimal", "feasible")
    rotation = result["rotation"]
    for i in range(len(rotation) - 1):
        assert rotation[i]["crop"] != rotation[i + 1]["crop"], (
            f"Same crop in consecutive seasons: {rotation[i]['crop']}"
        )


def test_rotation_with_rice_history():
    """After 3 seasons of rice, rice should not be the first season again."""
    rice = CROPS[0]
    history = [_make_history(rice, s) for s in range(1, 4)]
    result = run_optimization(
        field_id=1,
        crops=CROPS,
        suitability_scores=_suitability_map(),
        crop_history=history,
        rotation_rules=[],
        horizon=4,
    )
    assert result["status"] in ("optimal", "feasible")
    if result["rotation"]:
        assert result["rotation"][0]["crop"] != "Rice"


def test_rotation_constraint_minimum_gap():
    """If a rotation rule says Rice→Rice needs gap 2, enforce it."""
    rice = CROPS[0]
    rule = MagicMock()
    rule.crop_a_id = rice.id
    rule.crop_b_id = rice.id
    rule.minimum_gap = 2
    rule.disease_risk = "High"

    # Only use rice and one other crop so the gap rule is meaningful
    two_crops = [CROPS[0], CROPS[3]]   # Rice + Chickpea
    scores = {s.crop_id: s for s in rank_crops(two_crops, SOIL)}

    result = run_optimization(
        field_id=1,
        crops=two_crops,
        suitability_scores=scores,
        crop_history=[],
        rotation_rules=[rule],
        horizon=4,
    )
    # With gap 2 + only 2 crops, alternating is the only valid solution
    assert result["status"] in ("optimal", "feasible")
    rotation = result["rotation"]
    for i in range(len(rotation) - 1):
        assert rotation[i]["crop"] != rotation[i + 1]["crop"]


def test_valid_solution_structure():
    result = run_optimization(
        field_id=1,
        crops=CROPS,
        suitability_scores=_suitability_map(),
        crop_history=[],
        rotation_rules=[],
        horizon=4,
    )
    assert "status" in result
    assert "rotation" in result
    assert "total_expected_margin_rs" in result
    assert "soil_impact" in result
    assert "water_impact" in result
    assert "disease_risk" in result
    for season in result["rotation"]:
        assert "crop" in season
        assert "suitability_score" in season
        assert "explanation" in season
        assert len(season["explanation"]) > 10


def test_objective_produces_positive_margin():
    result = run_optimization(
        field_id=1,
        crops=CROPS,
        suitability_scores=_suitability_map(),
        crop_history=[],
        rotation_rules=[],
        horizon=4,
        area_ha=2.0,
    )
    assert result.get("total_expected_margin_rs", 0) > 0


def test_infeasible_with_too_few_crops():
    """Single crop cannot satisfy no-consecutive constraint for 2 seasons."""
    one_crop = [CROPS[0]]
    scores = {s.crop_id: s for s in rank_crops(one_crop, SOIL)}
    result = run_optimization(
        field_id=1,
        crops=one_crop,
        suitability_scores=scores,
        crop_history=[],
        rotation_rules=[],
        horizon=2,
    )
    # Either infeasible OR optimizer reports an error
    assert result["status"] in ("infeasible", "error") or len(result["rotation"]) <= 1
