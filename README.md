# SoilDCRA — AI-Driven Soil Degradation &amp; Crop Rotation Advisor

> **Scientific Disclaimer:** All soil thresholds, yield estimates, and economic figures in this system are illustrative demonstration values. They require regional calibration and validation by qualified agronomists before operational use. No guaranteed yield or profit is implied.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Technology Stack](#technology-stack)
5. [Installation](#installation)
6. [Running the Application](#running-the-application)
7. [7-Step Guided Workflow](#7-step-guided-workflow)
8. [API Reference](#api-reference)
9. [Data Models](#data-models)
10. [Crop Catalogue](#crop-catalogue)
11. [Economics Engine](#economics-engine)
12. [Optimization Engine](#optimization-engine)
13. [Configuration](#configuration)
14. [Testing](#testing)
15. [Project Structure](#project-structure)
16. [Limitations &amp; Future Work](#limitations--future-work)

---

## Overview

SoilDCRA is a **decision-support system** for smallholder and commercial farmers that combines:

- **Rule-based soil health assessment** across six soil quality indicators
- **Crop-soil suitability scoring** with six weighted sub-scores
- **Multi-season crop rotation optimisation** using Google OR-Tools CP-SAT solver
- **Itemised financial analysis** with three-scenario sensitivity modelling
- **Map-based field selection** via an interactive Folium map
- **Field problem tracking** (waterlogging, salinity, erosion, pest pressure, etc.)
- A clean **7-step guided Streamlit workflow** from field registration through to downloadable recommendation reports

The system is designed as a **modular monolith** — all components run in a single process with clear service boundaries, making it straightforward to extend or deploy.

---

## Features

| Feature | Detail |
|---|---|
| **Map-based field registration** | Click on a map to register or find an existing field (within 500 m radius) |
| **7-step guided workflow** | Select Field → Farm Details → Crop History → Problems &amp; Inputs → Soil Data → Analysis → Recommendation |
| **Soil health assessment** | pH, SOC, N, P, K, EC — each rated Optimal/Moderate/Poor/Critical with weighted composite score |
| **Soil degradation scoring** | Computes a 0–100 degradation score with risk level (Low/Moderate/High/Critical) and main drivers |
| **Crop suitability ranking** | 6-factor scoring: soil fit, climate, water, rotation bonus/penalty, economics, problem penalties |
| **Realistic season labels** | "Kharif 2024 (June–October)", "Rabi 2024–25 (November–March)" — not generic "Season 1" |
| **11-crop catalogue** | Rice, Wheat, Maize, Chickpea, Groundnut, Soybean, Mustard, Pigeon Pea, Potato, Onion, Tomato |
| **9 fertilizer products** | Urea, DAP, MOP, NPK 10-26-26, SSP, Compost, Vermicompost, Neem Cake, Gypsum |
| **15 field problem types** | Waterlogging, salinity, drought stress, erosion, compaction, nutrient deficiencies, pest/disease pressure, weed pressure |
| **CP-SAT optimisation** | Selects the best crop rotation over a configurable horizon (default 4 seasons) maximising profit subject to agronomic constraints |
| **Itemised financial analysis** | Seed, fertilizer, pesticide, irrigation, labour, machinery, other costs; revenue, margin, ROI |
| **Sensitivity analysis** | Pessimistic / Base / Optimistic scenario table per recommended crop |
| **Downloadable JSON report** | Full recommendation package as a dated JSON file |
| **43-test pytest suite** | Unit tests for soil service, suitability service, and optimizer |
| **End-to-end smoke test** | 12-step HTTP smoke test covering the full new API workflow |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Streamlit UI  (streamlit_app.py)                        │
│  7-step guided workflow · Folium map · JSON download     │
└───────────────────┬─────────────────────────────────────┘
                    │  HTTP/REST
┌───────────────────▼─────────────────────────────────────┐
│  FastAPI Application  (app/main.py)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  /api/v1/    │  │  /api/v1/    │  │  /api/v1/     │  │
│  │  fields      │  │  soil        │  │  optimization │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                 │                  │           │
│  ┌──────▼─────────────────▼──────────────────▼────────┐  │
│  │  Services Layer                                    │  │
│  │  soil_service · suitability_service                │  │
│  │  degradation_service · economics_service           │  │
│  │  rotation_optimizer (CP-SAT)                       │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │  SQLAlchemy ORM + SQLite  (app/db/)                │  │
│  │  10 tables: fields, crops, soil_observations,      │  │
│  │  crop_history, crop_economics, crop_requirements,  │  │
│  │  rotation_rules, optimization_runs,                │  │
│  │  field_problems, fertilizer_products,              │  │
│  │  fertilizer_usage                                  │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Library / Version |
|---|---|
| Web framework | FastAPI ≥ 0.110 |
| Database ORM | SQLAlchemy ≥ 2.0 |
| Database | SQLite (file: `soildcra.db`) |
| Data validation | Pydantic v2 |
| Optimisation solver | Google OR-Tools CP-SAT ≥ 9.9 |
| UI framework | Streamlit ≥ 1.35 |
| Interactive map | Folium ≥ 0.14 + streamlit-folium ≥ 0.15 |
| ASGI server | Uvicorn ≥ 0.29 |
| Testing | pytest ≥ 8.0 |
| Python | ≥ 3.10 |

---

## Installation

### Prerequisites

- Python 3.10 or newer
- pip (comes with Python)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/SoilDCRA.git
cd SoilDCRA

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install all dependencies
pip install -r requirements.txt
```

---

## Running the Application

Open **two terminals** in the project root.

**Terminal 1 — Backend API server:**
```bash
python run.py
# Server starts at http://127.0.0.1:8000
# Interactive API docs at http://127.0.0.1:8000/docs
```

**Terminal 2 — Streamlit UI:**
```bash
python -m streamlit run streamlit_app.py
# UI opens at http://localhost:8501
```

> **Note (Windows):** If `streamlit` is not on your PATH, always use `python -m streamlit run ...`. Similarly use `python -m pytest` rather than `pytest` directly.

On first startup the backend automatically creates `soildcra.db` and seeds it with 11 crops, 9 fertilizer products, 15 problem types, 17 rotation rules, and a demo field.

---

## 7-Step Guided Workflow

The Streamlit UI guides the user through a structured workflow. Each step is a distinct screen; progress is tracked in a sidebar.

| Step | Screen | What happens |
|---|---|---|
| **1** | Select Field | Click on the interactive map to select a location. The system finds an existing field within 500 m or creates a new one. |
| **2** | Farm Details | Enter farm name, area (ha), irrigation type, farming system, and soil type. Saved via `PATCH /fields/{id}`. |
| **3** | Crop History | Add up to 5 seasons of previous crops with season type (Kharif/Rabi/Zaid/Annual), year, and optional yield. |
| **4** | Problems &amp; Inputs | Multiselect from 15 field problem types (waterlogging, salinity, erosion, etc.) and record fertilizer products used this season. |
| **5** | Soil Data | Enter the latest soil test values: pH, SOC (%), N, P, K, and EC. |
| **6** | Analysis | The system runs soil health assessment, degradation scoring, and crop suitability ranking (penalised by recorded field problems). A ranked table of all 11 crops is displayed. |
| **7** | Recommendation | Shows the CP-SAT optimised 4-season rotation plan with full financial analysis (itemised costs, revenue, margin, ROI) and 3-scenario sensitivity table. Download the full report as JSON. |

---

## API Reference

Base URL: `http://127.0.0.1:8000/api/v1`

Interactive Swagger UI: `http://127.0.0.1:8000/docs`

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System health check |

### Fields

| Method | Path | Description |
|---|---|---|
| `POST` | `/fields/find-or-create` | Find existing field within 500 m of lat/lng, or create new |
| `GET` | `/fields/{id}` | Get field details |
| `PATCH` | `/fields/{id}` | Update field metadata (farm name, soil type, farming type) |
| `GET` | `/fields/` | List all fields |
| `POST` | `/fields/` | Create field directly (legacy) |

### Soil

| Method | Path | Description |
|---|---|---|
| `GET` | `/fields/{id}/soil` | List soil observations for a field |
| `POST` | `/fields/{id}/soil` | Add a soil observation |

### Crop History

| Method | Path | Description |
|---|---|---|
| `GET` | `/fields/{id}/history` | List crop history seasons |
| `POST` | `/fields/{id}/history` | Add a crop history entry |
| `DELETE` | `/fields/{id}/history/{history_id}` | Remove a history entry |

### Field Problems

| Method | Path | Description |
|---|---|---|
| `GET` | `/fields/{id}/problems` | List recorded field problems |
| `POST` | `/fields/{id}/problems` | Add a field problem |
| `DELETE` | `/fields/{id}/problems/{problem_id}` | Remove a field problem |

### Fertilizers

| Method | Path | Description |
|---|---|---|
| `GET` | `/fertilizers` | List all fertilizer products |
| `GET` | `/fields/{id}/fertilizers` | List fertilizer usage for a field |
| `POST` | `/fields/{id}/fertilizers` | Record fertilizer usage |
| `DELETE` | `/fields/{id}/fertilizers/{usage_id}` | Remove fertilizer usage |

### Analysis &amp; Optimisation

| Method | Path | Description |
|---|---|---|
| `POST` | `/fields/{id}/analyze` | Full soil assessment + crop suitability ranking |
| `GET` | `/fields/{id}/crops` | Ranked crops for a field |
| `POST` | `/fields/{id}/optimize` | Run CP-SAT rotation optimiser |
| `GET` | `/optimization/{run_id}` | Retrieve a stored optimisation run |

### Catalogue

| Method | Path | Description |
|---|---|---|
| `GET` | `/crops` | Full crop catalogue with requirements &amp; economics |

---

## Data Models

### Field
```
id, name, lat, lng, area_ha, irrigation_type,
farm_name, farming_type, soil_type, boundary_geojson,
created_at
```

### CropHistory
```
id, field_id, crop_id, season_order, season_name, season_type,
year, sowing_date, harvest_date, duration_days,
cultivated_area_ha, production_qty, production_unit
```

### FieldProblem
```
id, field_id, problem_type, severity, notes, recorded_at,
water_penalty, rotation_penalty, soil_penalty
```

### FertilizerUsage
```
id, field_id, fertilizer_id, quantity_kg_ha, season_name, applied_at
```

### CropEconomics
```
id, crop_id, expected_yield_t_ha, price_rs_per_t,
seed_cost_rs_ha, fertilizer_cost_rs_ha, pesticide_cost_rs_ha,
irrigation_cost_rs_ha, labor_cost_rs_ha, machinery_cost_rs_ha,
other_cost_rs_ha, total_cost_rs_ha (computed property)
```

---

## Crop Catalogue

| # | Crop | Family | Season | Water Need |
|---|---|---|---|---|
| 1 | Rice | Poaceae | Kharif | High |
| 2 | Wheat | Poaceae | Rabi | Moderate |
| 3 | Maize | Poaceae | Kharif/Rabi | Moderate |
| 4 | Chickpea | Fabaceae | Rabi | Low |
| 5 | Groundnut | Fabaceae | Kharif | Moderate |
| 6 | Soybean | Fabaceae | Kharif | Moderate |
| 7 | Mustard | Brassicaceae | Rabi | Low |
| 8 | Pigeon Pea | Fabaceae | Kharif | Low |
| 9 | Potato | Solanaceae | Rabi | High |
| 10 | Onion | Amaryllidaceae | Rabi | Moderate |
| 11 | Tomato | Solanaceae | Kharif/Rabi | High |

All crops include: pH range, temperature range, rainfall range, full itemised cost breakdown, expected yield, and market price (demonstration estimates — require regional calibration).

---

## Economics Engine

`app/services/economics_service.py`

For each recommended crop the engine computes:

**Per-hectare figures:**
- Revenue = expected yield (t/ha) × market price (₹/t)
- Itemised costs: Seed · Fertilizer · Pesticide · Irrigation · Labour · Machinery · Other
- Net margin = Revenue − Total cost
- ROI (%) = Net margin / Total cost × 100

**Sensitivity analysis (3 scenarios):**

| Scenario | Yield adjustment | Price adjustment | Cost adjustment |
|---|---|---|---|
| Pessimistic | −20% | −15% | +10% |
| Base | 0% | 0% | 0% |
| Optimistic | +15% | +10% | −5% |

> All economic values are **demonstration estimates only** and are not guaranteed farm-gate returns. They require regional calibration and expert validation.

---

## Optimization Engine

`app/optimization/rotation_optimizer.py`

Uses **Google OR-Tools CP-SAT** (constraint programming with SAT) to select the optimal crop rotation over a configurable season horizon.

### Decision Variables
- Binary variable `x[c, s]` = 1 if crop `c` is grown in season `s`

### Constraints
1. **Exactly one crop per season** — sum over crops for each season = 1
2. **No same crop in consecutive seasons** — mandatory break enforced for all crops
3. **Rotation gap rules** — crop-pair specific minimum gap (e.g., Rice→Rice: gap 3)
4. **Historical continuity** — existing crop history is prepended and rotation gap constraints applied across the history/future boundary
5. **Legume bonus** — if the previous season was a legume (Fabaceae), a suitability bonus is applied for the next
6. **Suitability threshold** — crops scoring below 20 (unsuitable) are excluded from the eligible set

### Objective
Maximise a weighted combination of:
- Crop suitability score (agronomic fit)
- Normalised net margin per hectare (economic return)

### Bug fixed
The same-crop rotation gap rule previously had a guard `if ci == cj: continue` that inadvertently skipped self-referential gap enforcement (e.g., Rice→Rice gap 3). This has been corrected — same-crop pairs now correctly enforce their minimum gap.

---

## Configuration

`app/core/config.py` — all thresholds are defined as typed dataclass fields and can be overridden via environment variables.

Key configurable parameters:

| Parameter | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./soildcra.db` | SQLAlchemy connection string |
| `PH_OPTIMAL_MIN` | 6.0 | Lower bound of optimal pH range |
| `PH_OPTIMAL_MAX` | 7.5 | Upper bound of optimal pH range |
| `SOC_LOW_THRESHOLD` | 0.5 | SOC (%) below which soil is rated Low |
| `SOC_MODERATE_THRESHOLD` | 1.0 | SOC (%) below which soil is rated Moderate |
| `EC_SALINE_THRESHOLD` | 4.0 | EC (dS/m) above which salinity is rated High |
| `OPTIMIZER_TIME_LIMIT_S` | 10 | CP-SAT solver wall-clock time limit (seconds) |
| `FIELD_PROXIMITY_M` | 500 | Radius for find-or-create field deduplication |

---

## Testing

### Unit tests

```bash
# Run all unit tests
python -m pytest tests/test_soil.py tests/test_suitability.py tests/test_optimizer.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

**Test counts:**

| File | Tests | Coverage area |
|---|---|---|
| `tests/test_soil.py` | 22 | Soil health service, degradation service |
| `tests/test_suitability.py` | 14 | Suitability scoring, economic score, ranking |
| `tests/test_optimizer.py` | 7 | CP-SAT optimizer correctness |
| **Total** | **43** | |

### End-to-end smoke test

Requires the backend server to be running (`python run.py`):

```bash
python tests/smoke_test.py
```

The smoke test exercises the full 12-step new workflow:
1. Health check
2. Crop catalogue listing
3. Fertilizer catalogue listing
4. Find-or-create field (map click simulation)
5. PATCH field metadata
6. Add 3 crop history seasons
7. Add field problem
8. Add fertilizer usage
9. Add soil observation
10. Run full analysis
11. Run CP-SAT optimisation
12. Retrieve stored optimisation run

---

## Project Structure

```
SoilDCRA/
│
├── run.py                        # Entry point — starts Uvicorn
├── streamlit_app.py              # 7-step Streamlit UI
├── requirements.txt              # Python dependencies
├── soildcra.db                   # SQLite database (auto-created)
│
├── app/
│   ├── main.py                   # FastAPI app, router registration
│   │
│   ├── core/
│   │   └── config.py             # All thresholds and settings
│   │
│   ├── db/
│   │   ├── database.py           # SQLAlchemy engine + session
│   │   └── models.py             # 10 ORM models
│   │
│   ├── data/
│   │   ├── crop_data.py          # 11-crop catalogue with full economics
│   │   └── seed.py               # Database seeder
│   │
│   ├── api/v1/
│   │   ├── fields.py             # Field CRUD, history, problems, fertilizers
│   │   ├── soil.py               # Soil observations
│   │   ├── analysis.py           # Soil assessment + crop suitability
│   │   └── optimization.py       # Rotation optimizer endpoint
│   │
│   ├── services/
│   │   ├── soil_service.py       # Rule-based soil health assessment
│   │   ├── degradation_service.py# Soil degradation scoring
│   │   ├── suitability_service.py# 6-factor crop suitability ranking
│   │   └── economics_service.py  # Itemised costs, margin, sensitivity
│   │
│   ├── optimization/
│   │   └── rotation_optimizer.py # CP-SAT multi-season optimizer
│   │
│   └── schemas/
│       ├── field.py
│       ├── soil.py
│       ├── crop.py
│       └── optimization.py
│
└── tests/
    ├── test_soil.py              # 22 soil service unit tests
    ├── test_suitability.py       # 14 suitability service unit tests
    ├── test_optimizer.py         # 7 optimizer unit tests
    └── smoke_test.py             # 12-step end-to-end HTTP smoke test
```

---

## Limitations &amp; Future Work

### Current Limitations

- **SQLite** — suitable for single-user local use; PostgreSQL recommended for multi-user deployment
- **Demonstration economics** — all cost and price data are illustrative and must be replaced with verified regional market data before advisory use
- **No authentication** — the API has no user accounts or access control
- **No spatial CRS** — latitude/longitude proximity check uses a flat-earth approximation (adequate at farm scale)
- **Static climate inputs** — temperature and rainfall are entered manually; no weather API integration
- **No satellite imagery** — soil data is manually entered; no integration with remote sensing products
- **Point-only field geometry** — fields are registered as lat/lng points; polygon boundary drawing is not yet implemented

### Planned Enhancements

- [ ] PostgreSQL + Alembic migrations for production deployment
- [ ] User authentication (JWT or OAuth2)
- [ ] Weather API integration (IMD / Open-Meteo) for automatic climate parameter lookup
- [ ] Polygon field boundary drawing using `streamlit-folium` draw plugin
- [ ] Satellite-derived soil organic carbon and NDVI overlays
- [ ] SMS / WhatsApp advisory delivery for low-connectivity farmers
- [ ] Multi-language support (Hindi, Telugu, Kannada, Tamil)
- [ ] Integration with state government crop insurance APIs
- [ ] Progressive Web App (PWA) packaging for offline mobile use

---

## Licence

MIT — see `LICENSE` for details.

---

*SoilDCRA is a research and demonstration prototype. All recommendations require validation by qualified agronomists before operational farm use.*
