"""
Economics Service — demonstration estimates only.

DISCLAIMER: All values are illustrative.
They are NOT guaranteed farm-gate returns.
They require regional calibration before any operational use.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.db.models import Crop


def calculate_economics(crop: Crop, area_ha: float = 1.0) -> Dict[str, Any]:
    """
    Compute itemised revenue, costs, and net margin for one crop
    on `area_ha` hectares.  Returns per-hectare AND total figures.
    """
    if crop.economics is None:
        return {
            "crop": crop.name,
            "area_ha": area_ha,
            "expected_yield_t_ha": None,
            "revenue_rs_ha": None,
            "cost_breakdown": [],
            "total_cost_rs_ha": None,
            "net_margin_rs_ha": None,
            "total_revenue_rs": None,
            "total_cost_rs": None,
            "total_margin_rs": None,
            "roi_pct": None,
            "disclaimer": "No economic data available for this crop.",
        }

    econ = crop.economics
    yield_t_ha = econ.expected_yield_t_ha or 0.0
    price      = econ.price_rs_per_t or 0.0
    revenue_ha = yield_t_ha * price

    # Itemised cost breakdown
    cost_items: List[Dict[str, Any]] = []

    def _add(label, value):
        if value:
            cost_items.append({"item": label, "cost_rs_ha": round(value, 0)})

    _add("Seed",          econ.seed_cost_rs_ha)
    _add("Fertilizer",    econ.fertilizer_cost_rs_ha)
    _add("Crop protection / pesticide", econ.pesticide_cost_rs_ha)
    _add("Irrigation",    econ.irrigation_cost_rs_ha)
    _add("Labor",         econ.labor_cost_rs_ha)
    _add("Machinery",     econ.machinery_cost_rs_ha)
    _add("Other",         econ.other_cost_rs_ha)

    total_cost_ha = econ.total_cost_rs_ha   # uses property
    margin_ha     = revenue_ha - total_cost_ha
    roi_pct       = (margin_ha / total_cost_ha * 100) if total_cost_ha > 0 else None

    return {
        "crop": crop.name,
        "area_ha": area_ha,
        "expected_yield_t_ha": yield_t_ha,
        "price_rs_per_t": price,
        "revenue_rs_ha": round(revenue_ha, 0),
        "cost_breakdown": cost_items,
        "total_cost_rs_ha": round(total_cost_ha, 0),
        "net_margin_rs_ha": round(margin_ha, 0),
        "total_revenue_rs": round(revenue_ha * area_ha, 0),
        "total_cost_rs": round(total_cost_ha * area_ha, 0),
        "total_margin_rs": round(margin_ha * area_ha, 0),
        "roi_pct": round(roi_pct, 1) if roi_pct is not None else None,
        "disclaimer": (
            "Demonstration estimates — not live farm-gate prices. "
            "Requires regional calibration."
        ),
    }


def calculate_sensitivity(crop: Crop, area_ha: float = 1.0) -> Dict[str, Any]:
    """
    Conservative / Expected / Favorable scenario analysis.
    Demonstration estimates only.
    """
    if crop.economics is None:
        return {}

    econ = crop.economics
    yield_t = econ.expected_yield_t_ha or 0.0
    price   = econ.price_rs_per_t or 0.0
    cost_ha = econ.total_cost_rs_ha

    scenarios = {
        "Conservative": {"yield_mult": 0.75, "price_mult": 0.85},
        "Expected":     {"yield_mult": 1.00, "price_mult": 1.00},
        "Favorable":    {"yield_mult": 1.20, "price_mult": 1.10},
    }

    results = {}
    for name, mults in scenarios.items():
        rev_ha  = yield_t * mults["yield_mult"] * price * mults["price_mult"]
        prof_ha = rev_ha - cost_ha
        results[name] = {
            "revenue_rs_ha":    round(rev_ha * area_ha, 0),
            "profit_rs_ha":     round(prof_ha * area_ha, 0),
            "roi_pct":          round(prof_ha / cost_ha * 100, 1) if cost_ha > 0 else None,
        }
    return results
