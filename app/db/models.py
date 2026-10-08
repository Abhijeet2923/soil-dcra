"""SQLAlchemy ORM models for SoilDCRA MVP v2."""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ── Core field & soil ─────────────────────────────────────────────────────────

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    area_ha = Column(Float, nullable=False, default=1.0)
    irrigation_type = Column(String(60), nullable=True)
    current_crop = Column(String(60), nullable=True)
    farm_name = Column(String(120), nullable=True)
    farming_type = Column(String(60), nullable=True)   # e.g. Conventional, Organic
    soil_type = Column(String(60), nullable=True)      # e.g. Loam, Clay, Sandy
    boundary_geojson = Column(Text, nullable=True)     # GeoJSON polygon string
    created_at = Column(DateTime, default=_utcnow)

    soil_observations = relationship("SoilObservation", back_populates="field")
    crop_histories = relationship("CropHistory", back_populates="field",
                                  order_by="CropHistory.season_order")
    optimization_runs = relationship("OptimizationRun", back_populates="field")
    problems = relationship("FieldProblem", back_populates="field")
    fertilizer_usages = relationship("FertilizerUsage", back_populates="field")


class SoilObservation(Base):
    __tablename__ = "soil_observations"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    sample_date = Column(String(20), nullable=True)
    ph = Column(Float, nullable=True)
    soc_pct = Column(Float, nullable=True)   # SOC concentration % — NOT SOC stock
    nitrogen = Column(Float, nullable=True)  # g/kg
    phosphorus = Column(Float, nullable=True)# mg/kg
    potassium = Column(Float, nullable=True) # mg/kg
    ec = Column(Float, nullable=True)        # dS/m
    sand_pct = Column(Float, nullable=True)
    silt_pct = Column(Float, nullable=True)
    clay_pct = Column(Float, nullable=True)

    field = relationship("Field", back_populates="soil_observations")


# ── Crop catalogue ────────────────────────────────────────────────────────────

class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)
    family = Column(String(80), nullable=True)
    season = Column(String(40), nullable=True)         # Kharif, Rabi, Zaid
    water_need = Column(String(20), nullable=True)     # Low, Moderate, High
    duration_days = Column(Integer, nullable=True)
    sowing_window = Column(String(60), nullable=True)  # e.g. "June–July"
    harvest_window = Column(String(60), nullable=True)
    crop_protection_level = Column(String(20), nullable=True)  # Low/Moderate/High
    labor_level = Column(String(20), nullable=True)

    requirements = relationship("CropRequirement", back_populates="crop", uselist=False)
    economics = relationship("CropEconomics", back_populates="crop", uselist=False)
    rotation_rules_as_a = relationship(
        "RotationRule", foreign_keys="RotationRule.crop_a_id", back_populates="crop_a"
    )
    rotation_rules_as_b = relationship(
        "RotationRule", foreign_keys="RotationRule.crop_b_id", back_populates="crop_b"
    )


class CropRequirement(Base):
    __tablename__ = "crop_requirements"

    crop_id = Column(Integer, ForeignKey("crops.id"), primary_key=True)
    ph_min = Column(Float, nullable=True)
    ph_max = Column(Float, nullable=True)
    temp_min = Column(Float, nullable=True)
    temp_max = Column(Float, nullable=True)
    water_min = Column(Float, nullable=True)   # mm/season
    water_max = Column(Float, nullable=True)

    crop = relationship("Crop", back_populates="requirements")


class CropEconomics(Base):
    """
    Per-crop economic parameters.
    All values are DEMONSTRATION ESTIMATES — not guaranteed prices.
    Requires regional calibration.
    """
    __tablename__ = "crop_economics"

    crop_id = Column(Integer, ForeignKey("crops.id"), primary_key=True)
    expected_yield_t_ha = Column(Float, nullable=True)
    price_rs_per_t = Column(Float, nullable=True)
    # Itemised input costs (Rs/ha, demo estimates)
    seed_cost_rs_ha = Column(Float, nullable=True)
    fertilizer_cost_rs_ha = Column(Float, nullable=True)
    pesticide_cost_rs_ha = Column(Float, nullable=True)
    irrigation_cost_rs_ha = Column(Float, nullable=True)
    labor_cost_rs_ha = Column(Float, nullable=True)
    machinery_cost_rs_ha = Column(Float, nullable=True)
    other_cost_rs_ha = Column(Float, nullable=True)
    # Keep backward-compat derived column (sum of all costs)
    variable_cost_rs_per_ha = Column(Float, nullable=True)

    crop = relationship("Crop", back_populates="economics")

    @property
    def total_cost_rs_ha(self):
        costs = [
            self.seed_cost_rs_ha or 0,
            self.fertilizer_cost_rs_ha or 0,
            self.pesticide_cost_rs_ha or 0,
            self.irrigation_cost_rs_ha or 0,
            self.labor_cost_rs_ha or 0,
            self.machinery_cost_rs_ha or 0,
            self.other_cost_rs_ha or 0,
        ]
        return sum(costs) or self.variable_cost_rs_per_ha or 0


# ── Crop history ──────────────────────────────────────────────────────────────

class CropHistory(Base):
    __tablename__ = "crop_history"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    season_order = Column(Integer, nullable=False)      # sequential ordering
    season_name = Column(String(40), nullable=True)     # e.g. "Kharif 2024"
    season_type = Column(String(20), nullable=True)     # Kharif / Rabi / Zaid
    year = Column(Integer, nullable=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    sowing_date = Column(String(20), nullable=True)     # ISO date
    harvest_date = Column(String(20), nullable=True)
    duration_days = Column(Integer, nullable=True)      # actual or estimated
    cultivated_area_ha = Column(Float, nullable=True)
    production_qty = Column(Float, nullable=True)       # original quantity
    production_unit = Column(String(20), nullable=True) # tonnes, kg, quintal
    yield_t_ha = Column(Float, nullable=True)           # normalised t/ha
    notes = Column(Text, nullable=True)

    field = relationship("Field", back_populates="crop_histories")
    crop = relationship("Crop")

    @property
    def season(self):
        """Backward-compatible alias for season_order."""
        return self.season_order


# ── Problems ──────────────────────────────────────────────────────────────────

class FieldProblem(Base):
    """Structured problems reported by farmer for a previous crop season."""
    __tablename__ = "field_problems"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    season_name = Column(String(40), nullable=True)  # e.g. "Kharif 2024"
    problem_code = Column(String(50), nullable=False)  # code from PROBLEM_TYPES
    problem_label = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=True)  # Low, Moderate, High
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    field = relationship("Field", back_populates="problems")


# ── Fertilizers ───────────────────────────────────────────────────────────────

class FertilizerProduct(Base):
    __tablename__ = "fertilizer_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)
    n_pct = Column(Float, nullable=True)   # N%
    p_pct = Column(Float, nullable=True)   # P%
    k_pct = Column(Float, nullable=True)   # K%
    cost_rs_per_50kg = Column(Float, nullable=True)
    unit = Column(String(30), nullable=True)

    usages = relationship("FertilizerUsage", back_populates="product")


class FertilizerUsage(Base):
    __tablename__ = "fertilizer_usage"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    fertilizer_id = Column(Integer, ForeignKey("fertilizer_products.id"), nullable=False)
    season_name = Column(String(40), nullable=True)
    quantity_kg_ha = Column(Float, nullable=True)
    total_cost_rs = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    field = relationship("Field", back_populates="fertilizer_usages")
    product = relationship("FertilizerProduct", back_populates="usages")


# ── Rotation rules ────────────────────────────────────────────────────────────

class RotationRule(Base):
    __tablename__ = "rotation_rules"

    id = Column(Integer, primary_key=True, index=True)
    crop_a_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    crop_b_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    minimum_gap = Column(Integer, default=1)
    disease_risk = Column(String(20), default="Low")

    crop_a = relationship("Crop", foreign_keys=[crop_a_id], back_populates="rotation_rules_as_a")
    crop_b = relationship("Crop", foreign_keys=[crop_b_id], back_populates="rotation_rules_as_b")


# ── Optimization ──────────────────────────────────────────────────────────────

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    horizon = Column(Integer, nullable=False)
    objective = Column(String(40), default="maximize_margin")
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=_utcnow)

    field = relationship("Field", back_populates="optimization_runs")
    results = relationship("OptimizationResult", back_populates="run")


class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False, index=True)
    season = Column(Integer, nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    suitability_score = Column(Float, nullable=True)
    expected_margin = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)

    run = relationship("OptimizationRun", back_populates="results")
    crop = relationship("Crop")
