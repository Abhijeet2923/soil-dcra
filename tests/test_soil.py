"""Tests for soil health service."""
import pytest

from app.services.soil_service import (
    assess_soil,
    _score_ph,
    _score_soc,
    _score_nitrogen,
    _score_potassium,
    _score_ec,
)


# ── pH classification ─────────────────────────────────────────────────────────

def test_ph_optimal():
    ind = _score_ph(6.5)
    assert ind.status == "Good"
    assert ind.score == 100.0


def test_ph_low():
    ind = _score_ph(4.5)
    assert ind.status == "Low"
    assert ind.score < 50


def test_ph_high():
    ind = _score_ph(8.5)
    assert ind.status == "Low"


def test_ph_moderate():
    ind = _score_ph(5.8)
    assert ind.status == "Moderate"


def test_ph_none():
    ind = _score_ph(None)
    assert ind.status == "Unknown"
    assert ind.score == 50.0


# ── SOC classification ────────────────────────────────────────────────────────

def test_soc_low():
    ind = _score_soc(0.3)
    assert ind.status == "Low"
    assert ind.score < 50


def test_soc_moderate():
    ind = _score_soc(0.7)
    assert ind.status == "Moderate"


def test_soc_good():
    ind = _score_soc(1.5)
    assert ind.status == "Good"
    assert ind.score == 100.0


# ── Nitrogen classification ───────────────────────────────────────────────────

def test_nitrogen_low():
    ind = _score_nitrogen(0.02)
    assert ind.status == "Low"


def test_nitrogen_moderate():
    ind = _score_nitrogen(0.10)
    assert ind.status == "Moderate"


def test_nitrogen_good():
    ind = _score_nitrogen(0.20)
    assert ind.status == "Good"


# ── Potassium classification ──────────────────────────────────────────────────

def test_potassium_low():
    ind = _score_potassium(80.0)
    assert ind.status == "Low"


def test_potassium_moderate():
    ind = _score_potassium(150.0)
    assert ind.status == "Moderate"


def test_potassium_good():
    ind = _score_potassium(250.0)
    assert ind.status == "Good"


# ── EC / salinity ─────────────────────────────────────────────────────────────

def test_ec_good():
    ind = _score_ec(0.5)
    assert ind.status == "Good"
    assert ind.score == 100.0


def test_ec_moderate():
    ind = _score_ec(2.5)
    assert ind.status == "Moderate"


def test_ec_high_salinity():
    ind = _score_ec(5.0)
    assert ind.status == "Low"   # Low status = high salinity


# ── Composite soil assessment ─────────────────────────────────────────────────

def test_assess_soil_healthy():
    a = assess_soil(ph=6.5, soc_pct=1.2, nitrogen=0.20, phosphorus=30.0,
                    potassium=250.0, ec=0.5)
    assert a.soil_health_score > 85
    assert a.degradation_risk_score < 20
    assert a.risk_level == "Low"


def test_assess_soil_degraded():
    a = assess_soil(ph=4.5, soc_pct=0.3, nitrogen=0.02, phosphorus=5.0,
                    potassium=60.0, ec=5.0)
    assert a.soil_health_score < 40
    assert a.degradation_risk_score > 60
    assert a.risk_level in ("High", "Critical")


def test_assess_soil_demo_field():
    """Verify demo field scenario produces expected moderate result."""
    a = assess_soil(ph=6.7, soc_pct=0.62, nitrogen=0.10, phosphorus=18.0,
                    potassium=85.0, ec=0.8)
    # pH is Good, SOC moderate, N moderate, P moderate, K Low, EC Good
    assert a.ph.status == "Good"
    assert a.soc.status == "Moderate"
    assert a.potassium.status == "Low"
    assert 30 <= a.soil_health_score <= 80


def test_degradation_score_complement():
    a = assess_soil(ph=6.5, soc_pct=1.0, nitrogen=0.15, phosphorus=25.0,
                    potassium=200.0, ec=1.0)
    assert abs(a.soil_health_score + a.degradation_risk_score - 100.0) < 0.01


def test_texture_class_loam():
    a = assess_soil(sand_pct=40.0, silt_pct=35.0, clay_pct=25.0)
    assert a.texture_class is not None
