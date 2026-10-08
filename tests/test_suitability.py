"""Tests for crop suitability service."""
import pytest
from unittest.mock import MagicMock

from app.services import suitability_service
from app.services.soil_service import assess_soil
from app.schemas.crop import CropSuitabilityScore


def _make_crop(
    id=1, name="TestCrop", family="Poaceae", season="Kharif",
    water_need="Moderate", ph_min=6.0, ph_max=7.5,
    temp_min=18.0, temp_max=35.0, water_min=500, water_max=900,
    yield_t=3.0, price=15000.0, cost=20000.0,
):
    """Build a minimal mock Crop ORM object."""
    crop = MagicMock()
    crop.id = id
    crop.name = name
    crop.family = family
    crop.season = season
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

    return crop


DEMO_SOIL = assess_soil(
    ph=6.7, soc_pct=0.62, nitrogen=0.10,
    phosphorus=18.0, potassium=85.0, ec=0.8,
)


# ── Soil score ────────────────────────────────────────────────────────────────

def test_soil_score_in_range():
    crop = _make_crop(ph_min=6.0, ph_max=7.5)
    sc = suitability_service._soil_score(crop, DEMO_SOIL)
    assert 0 <= sc <= 100


def test_soil_score_good_ph():
    crop = _make_crop(ph_min=6.0, ph_max=7.5)
    sc = suitability_service._soil_score(crop, DEMO_SOIL)
    assert sc > 40   # pH 6.7 is in range


def test_soil_score_bad_ph():
    crop = _make_crop(ph_min=4.0, ph_max=4.5)   # way below demo soil pH 6.7
    sc = suitability_service._soil_score(crop, DEMO_SOIL)
    assert sc < 60


# ── Climate score ─────────────────────────────────────────────────────────────

def test_climate_score_in_range():
    crop = _make_crop(temp_min=20.0, temp_max=35.0)
    sc = suitability_service._climate_score(crop, 27.0)
    assert sc > 80   # 27°C is within 20-35


def test_climate_score_too_cold():
    crop = _make_crop(temp_min=30.0, temp_max=40.0)
    sc = suitability_service._climate_score(crop, 15.0)
    assert sc < 50


# ── Water score ───────────────────────────────────────────────────────────────

def test_water_score_sufficient():
    crop = _make_crop(water_min=500, water_max=900)
    sc = suitability_service._water_score(crop, 1050.0, "Partial")
    assert sc > 0   # effective water = 1050 + 200 = 1250 — slightly over max


def test_water_score_deficit():
    crop = _make_crop(water_min=1200, water_max=2000)
    sc = suitability_service._water_score(crop, 300.0, "Rainfed")
    assert sc < 70


# ── Rotation score ────────────────────────────────────────────────────────────

def test_rotation_penalty_same_crop():
    crop = _make_crop(name="Rice", family="Poaceae")
    history = ["Rice", "Rice", "Rice"]
    sc = suitability_service._rotation_score(crop, history)
    assert sc < 50   # should be heavily penalised


def test_rotation_legume_bonus():
    crop = _make_crop(name="Chickpea", family="Fabaceae")
    history = ["Rice", "Wheat"]
    sc = suitability_service._rotation_score(crop, history)
    # Base 70 + legume bonus 20 = 90 (no penalty)
    assert sc >= 85


def test_rotation_no_history():
    crop = _make_crop(name="Chickpea", family="Fabaceae")
    sc = suitability_service._rotation_score(crop, [])
    assert sc > 70


# ── Unsuitable crop handling ──────────────────────────────────────────────────

def test_unsuitable_crop_low_final_score():
    """A crop completely outside pH range should score low overall."""
    crop = _make_crop(name="AcidCrop", ph_min=3.0, ph_max=4.0,
                      temp_min=10.0, temp_max=15.0)
    result = suitability_service.score_crop(
        crop, DEMO_SOIL, mean_temp_c=27.0, seasonal_rainfall_mm=1050.0
    )
    assert result.final_score < 60
    assert isinstance(result, CropSuitabilityScore)


# ── Rank crops ────────────────────────────────────────────────────────────────

def test_rank_crops_descending():
    crops = [
        _make_crop(id=1, name="Rice",     ph_min=5.5, ph_max=7.0, temp_min=20, temp_max=38),
        _make_crop(id=2, name="Chickpea", family="Fabaceae", ph_min=6.0, ph_max=8.0,
                   temp_min=10, temp_max=30, water_min=250, water_max=500, water_need="Low"),
        _make_crop(id=3, name="Maize",    ph_min=5.8, ph_max=7.5, temp_min=18, temp_max=35),
    ]
    ranked = suitability_service.rank_crops(
        crops, DEMO_SOIL, mean_temp_c=27.0, seasonal_rainfall_mm=1050.0,
        crop_history=["Rice", "Rice", "Rice"]
    )
    scores = [r.final_score for r in ranked]
    assert scores == sorted(scores, reverse=True)


# ── Economic score ────────────────────────────────────────────────────────────

def test_economic_score_positive_margin():
    crop = _make_crop(yield_t=4.0, price=20000.0, cost=30000.0)
    sc = suitability_service._economic_score(crop)
    assert sc > 0


def test_economic_score_negative_margin():
    crop = _make_crop(yield_t=1.0, price=5000.0, cost=100000.0)
    sc = suitability_service._economic_score(crop)
    assert sc == 0.0   # clamped to 0
