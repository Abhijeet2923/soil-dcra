# SoilDCRA — Streamlit → React Migration Plan

## Overview

Controlled frontend migration from Streamlit to React + TypeScript + Vite.
The existing FastAPI backend, SQLite database, agricultural algorithms, and all
business logic are frozen. React is a new presentation layer only.

**Agreed scope additions (pure read-only, no existing logic changed):**
- Add 3 missing API endpoints (problem-types, crop economics, crop sensitivity)
- Add 2 missing list/history endpoints (GET /fields, GET /fields/{id}/optimization-runs)
- Fix 2 pre-existing bugs (find-or-create naming, dead schema file)

---

## Architecture Boundary

```
                USER
                 │
                 ▼
          ┌─────────────┐
          │    REACT    │  frontend/
          │ TypeScript  │
          └──────┬──────┘
                 │ HTTP/JSON
                 ▼
          ┌─────────────┐
          │   FASTAPI   │  app/  ← FROZEN (except agreed additions)
          │   BACKEND   │
          └──────┬──────┘
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
    SQLite    Agronomy  CP-SAT
              Services  Optimizer
                 │
                 ▼
            Economics
```

**React must NOT:**
- Connect directly to SQLite
- Import Python modules
- Duplicate any calculation (soil scores, suitability, rotation, economics, ROI)
- Hard-code crop prices, yields, or agricultural thresholds

---

## Repository Layout (Target)

```
SoilDCRA/                    ← existing root, untouched
├── app/                     ← FROZEN backend
├── tests/                   ← FROZEN backend tests
├── streamlit_app.py         ← kept, still runnable
├── run.py                   ← kept
├── requirements.txt         ← kept (add 2 deps for new endpoints)
├── soildcra.db              ← kept
│
├── frontend/                ← NEW React application
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── endpoints.ts
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── map/
│   │   │   ├── forms/
│   │   │   ├── charts/
│   │   │   └── common/
│   │   ├── pages/
│   │   │   ├── FieldSelectPage.tsx
│   │   │   ├── FarmDetailsPage.tsx
│   │   │   ├── CropHistoryPage.tsx
│   │   │   ├── ProblemsInputsPage.tsx
│   │   │   ├── SoilDataPage.tsx
│   │   │   ├── AnalysisPage.tsx
│   │   │   └── RecommendationPage.tsx
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env
│   └── .env.example
│
└── README.md                ← updated with both frontend docs
```

---

## Backend Additions (Agreed — All Read-Only)

These are the ONLY backend changes permitted. None alter existing logic.

### New endpoints to add to existing routers:

| # | Method | Path | Purpose | File |
|---|---|---|---|---|
| 1 | `GET` | `/api/v1/problem-types` | Returns PROBLEM_TYPES list | new route in `fields.py` |
| 2 | `GET` | `/api/v1/fields` | Returns all fields (list) | new route in `fields.py` |
| 3 | `GET` | `/api/v1/crops/{crop_id}/economics` | Itemised economics for one crop | new route in `analysis.py` |
| 4 | `GET` | `/api/v1/crops/{crop_id}/sensitivity` | 3-scenario sensitivity table | new route in `analysis.py` |
| 5 | `GET` | `/api/v1/fields/{field_id}/optimization-runs` | List past optimization runs | new route in `optimization.py` |

### Bug fixes:

| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `app/api/v1/fields.py` | `find-or-create` accepts `lat`/`lng` in smoke test but schema uses `latitude`/`longitude` | Accept both key names (alias `lat`→`latitude`, `lng`→`longitude`) OR fix smoke test — **fix the smoke test**, keep schema canonical |
| 2 | `app/schemas/field.py` | Dead file duplicating inline schemas | Delete the file; update any imports if found |

---

## Complete API Inventory (React Will Consume All Of These)

| Method | Path | React Usage |
|---|---|---|
| `GET` | `/api/v1/health` | Connection status banner |
| `GET` | `/api/v1/crops` | Crop dropdowns (Step 2, history form) |
| `GET` | `/api/v1/fertilizers` | Fertilizer dropdown (Step 3) |
| `GET` | `/api/v1/problem-types` | Problems multiselect (Step 3) — **NEW** |
| `GET` | `/api/v1/fields` | Returning-user field selector — **NEW** |
| `POST` | `/api/v1/fields/` | Create new field |
| `GET` | `/api/v1/fields/{id}` | Load field details |
| `PATCH` | `/api/v1/fields/{id}` | Save farm details (Step 1) |
| `POST` | `/api/v1/fields/find-or-create` | Map click → field registration (Step 0) |
| `POST` | `/api/v1/fields/{id}/history` | Save one crop season |
| `GET` | `/api/v1/fields/{id}/history` | Load history |
| `DELETE` | `/api/v1/fields/{id}/history` | Clear before re-save |
| `POST` | `/api/v1/fields/{id}/problems` | Save problem entry |
| `GET` | `/api/v1/fields/{id}/problems` | Load problems |
| `DELETE` | `/api/v1/fields/{id}/problems` | Clear before re-save |
| `POST` | `/api/v1/fields/{id}/fertilizers` | Save fertilizer usage |
| `GET` | `/api/v1/fields/{id}/fertilizers` | Load fertilizer usage |
| `DELETE` | `/api/v1/fields/{id}/fertilizers` | Clear before re-save |
| `POST` | `/api/v1/fields/{id}/soil` | Save soil observation |
| `GET` | `/api/v1/fields/{id}/soil` | Load soil observation |
| `POST` | `/api/v1/fields/{id}/analyze` | Run full analysis |
| `GET` | `/api/v1/fields/{id}/crops` | Quick suitability ranking |
| `POST` | `/api/v1/fields/{id}/optimize` | Run rotation optimizer |
| `GET` | `/api/v1/optimization/{run_id}` | Load stored run |
| `GET` | `/api/v1/fields/{id}/optimization-runs` | List past runs — **NEW** |
| `GET` | `/api/v1/crops/{crop_id}/economics` | Crop cost/revenue breakdown — **NEW** |
| `GET` | `/api/v1/crops/{crop_id}/sensitivity` | Scenario analysis — **NEW** |

---

## TypeScript Types (Derived From Actual Backend Schemas)

Types live in `frontend/src/types/`. Created from actual FastAPI response shapes.

Key types: `Field`, `SoilObservation`, `SoilAssessment`, `SoilIndicator`,
`Crop`, `CropHistory`, `CropSuitabilityScore`, `AnalysisResponse`,
`OptimizeRequest`, `OptimizationResult`, `FertilizerProduct`, `FertilizerUsage`,
`FieldProblem`, `ProblemType`, `CropEconomics`, `SensitivityResult`.

---

## UI Design System

- **Palette:** Deep green `#315C3A` primary, neutral `#F5F3ED` background, `#26332A` text, amber `#B9822B` warning, red `#A84A42` critical
- **Typography:** System sans-serif stack (Source Sans 3 where available)
- **Style:** Professional agricultural software — no gradients, no glassmorphism, no animations beyond simple transitions
- **Layout:** Sidebar navigation + main content area (replaces Streamlit step-nav bar)
- **Status pills:** Good/Moderate/Low with green/amber/red fills — matches existing Streamlit pill logic exactly
- **Score bars:** Horizontal fill bars for soil indicators — same semantic as Streamlit

---

## Sub-Tasks

---

### Sub-Task 1 — Backend Additions & Bug Fixes

**Intent:** Add the 5 agreed read-only endpoints and fix 2 pre-existing bugs before any React code is written. Ensures the full API surface is stable before frontend integration starts.

**Expected Outcomes:**
- `GET /api/v1/problem-types` returns the 15 PROBLEM_TYPES
- `GET /api/v1/fields` returns a list of all fields
- `GET /api/v1/crops/{crop_id}/economics` returns itemised breakdown
- `GET /api/v1/crops/{crop_id}/sensitivity` returns 3-scenario table
- `GET /api/v1/fields/{field_id}/optimization-runs` returns past runs list
- `tests/smoke_test.py` `find-or-create` call uses correct `latitude`/`longitude` keys and passes
- `app/schemas/field.py` is deleted; no import errors remain
- All existing backend tests still pass

**Todo List:**
- [ ] Add `GET /api/v1/problem-types` route to `app/api/v1/fields.py`
- [ ] Add `GET /api/v1/fields` route to `app/api/v1/fields.py`
- [ ] Add `GET /api/v1/crops/{crop_id}/economics` route to `app/api/v1/analysis.py`
- [ ] Add `GET /api/v1/crops/{crop_id}/sensitivity` route to `app/api/v1/analysis.py`
- [ ] Add `GET /api/v1/fields/{field_id}/optimization-runs` route to `app/api/v1/optimization.py`
- [ ] Fix `tests/smoke_test.py` to use `latitude`/`longitude` (not `lat`/`lng`)
- [ ] Delete `app/schemas/field.py`; verify no imports remain
- [ ] Run `pytest tests/test_soil.py tests/test_suitability.py tests/test_optimizer.py -v` — all must pass
- [ ] Run `python tests/smoke_test.py` (with server running) — all checks must pass

**Relevant Context:**
- New endpoints call existing service functions: `calculate_economics(crop)` and `calculate_sensitivity(crop)` from `app/services/economics_service.py`; `PROBLEM_TYPES` from `app/data/crop_data.py`
- `economics_service` is already imported in `app/optimization/rotation_optimizer.py` — no circular import risk
- The `Crop` model is loaded from DB by `crop_id`; pattern matches existing `analysis.py` structure
- `app/schemas/field.py` — grep confirms it is not imported anywhere in the codebase

**Status:** `[ ] pending`

---

### Sub-Task 2 — React Project Scaffold

**Intent:** Initialize the React + TypeScript + Vite project inside `frontend/`. Establish the folder structure, install dependencies, configure environment variables, and verify that `npm run dev` starts and the browser loads a blank page. No API calls yet.

**Expected Outcomes:**
- `frontend/` directory exists with working Vite+React+TS scaffold
- `npm install` and `npm run dev` succeed without errors
- Browser opens at `http://localhost:5173` and shows a minimal page
- `VITE_API_BASE_URL=http://localhost:8000` is configured via `.env`
- `.env.example` is committed (`.env` is gitignored)
- Tailwind CSS is configured and a sample class renders correctly
- `frontend/src/api/client.ts` exists (Axios instance, base URL from env, error normalisation)
- `frontend/src/api/endpoints.ts` exists (all API path constants)
- `frontend/src/types/index.ts` exists (all TypeScript interfaces matching actual backend schemas)
- React Router is configured with placeholder routes for each page

**Todo List:**
- [ ] `npm create vite@latest frontend -- --template react-ts` from project root
- [ ] `cd frontend && npm install`
- [ ] Install dependencies: `axios`, `react-router-dom`, `@tanstack/react-query`, `react-leaflet`, `leaflet`, `recharts`, `tailwindcss`, `postcss`, `autoprefixer`
- [ ] `npx tailwindcss init -p` and configure `tailwind.config.js` with content paths
- [ ] Create `frontend/.env` with `VITE_API_BASE_URL=http://localhost:8000`
- [ ] Create `frontend/.env.example` with same key, empty value
- [ ] Create `frontend/src/api/client.ts` — Axios instance + error normalisation wrapper
- [ ] Create `frontend/src/api/endpoints.ts` — all API path constants (no raw strings in components)
- [ ] Create `frontend/src/types/index.ts` — all interfaces derived from backend schemas
- [ ] Configure React Router in `App.tsx` with placeholder routes for all 7 pages
- [ ] Create `frontend/src/components/layout/AppShell.tsx` — sidebar nav + main area
- [ ] Create `frontend/src/components/common/BackendStatus.tsx` — polls `GET /health`, shows connected/offline banner
- [ ] Verify `npm run dev` starts, browser loads, BackendStatus shows "Backend connected" when `python run.py` is running

**Relevant Context:**
- Backend CORS is `allow_origins=["*"]` — no CORS change needed for localhost dev
- Vite default dev port is `5173`
- `VITE_` prefix exposes env vars to browser — API base URL only, never secrets
- Tailwind palette tokens should match the Streamlit CSS: `green-800` → `#315C3A`, `amber-600` → `#B9822B`, etc.

**Status:** `[ ] pending`

---

### Sub-Task 3 — Field Selection Page (Step 0 + Step 1)

**Intent:** Migrate the map-based field selection and farm details form. This is the entry point of the entire workflow. React Leaflet replaces the Streamlit `folium` map. The `find-or-create` API call is the first real backend integration.

**Expected Outcomes:**
- Leaflet map renders at `http://localhost:5173/`
- Clicking the map sets a green marker and updates lat/lng display
- Area (ha) number input is present
- "Use This Location" button calls `POST /api/v1/fields/find-or-create`
- Backend returns `field_id`; it is stored in React Query cache / app state (never shown raw to user)
- Returning users see a "Select existing field" panel populated from `GET /api/v1/fields`
- After field registration, workflow advances to Farm Details form (Step 1)
- Farm Details form PATCHes `/api/v1/fields/{id}` with name, area, irrigation, farming type, soil type, current crop
- Breadcrumb/step indicator shows current position

**Todo List:**
- [ ] Create `frontend/src/pages/FieldSelectPage.tsx` with React Leaflet map
- [ ] Implement map click handler → lat/lng state → marker update
- [ ] Implement area input and "Use This Location" button calling `POST /fields/find-or-create`
- [ ] Create `frontend/src/hooks/useWorkflow.ts` — holds `fieldId`, `fieldData`, `step`; persisted to `sessionStorage` for page-refresh safety
- [ ] Create `frontend/src/pages/FarmDetailsPage.tsx` with controlled form
- [ ] Implement PATCH call on form submit
- [ ] Create `frontend/src/components/common/StepIndicator.tsx` — 7-step progress bar
- [ ] Add "Select existing field" panel using `GET /api/v1/fields` with field name + area display
- [ ] Write integration smoke: navigate to `/`, click map, submit, verify `fieldId` is set in state

**Relevant Context:**
- `POST /fields/find-or-create` response includes `created: bool` — show brief toast "New field created" vs "Existing field found"
- `fieldId` must be stored in `useWorkflow` hook and never shown to user in main UI
- Farm Details fields: `farm_name`, `name`, `area_ha`, `irrigation_type` (Rainfed/Partial/Irrigated), `farming_type` (Conventional/Organic/Mixed), `soil_type` (dropdown), `current_crop`
- `react-leaflet` requires `leaflet/dist/leaflet.css` import in `main.tsx`

**Status:** `[ ] pending`

---

### Sub-Task 4 — Crop History Page (Step 2)

**Intent:** Migrate the dynamic crop season entry table. Each row is a season with crop, dates, yield, and area. Entries are held in local state and batch-saved to the API when the user advances.

**Expected Outcomes:**
- Crop dropdown populated from `GET /api/v1/crops`
- Season type (Kharif/Rabi/Zaid), year, production qty/unit, area, sowing/harvest dates
- "Add season" button appends a row to local state; rows render in a clean table
- "Clear all" button clears local state
- Advancing to next step calls `DELETE /fields/{id}/history` then `POST` for each entry
- Table shows crop name, season label, yield (t/ha), area (ha)
- Season label helper (`Kharif 2024 (June–October 2024)`) implemented in `frontend/src/utils/season.ts`

**Todo List:**
- [ ] Create `frontend/src/pages/CropHistoryPage.tsx`
- [ ] Create `frontend/src/hooks/useCrops.ts` — TanStack Query wrapper for `GET /api/v1/crops`
- [ ] Create `frontend/src/utils/season.ts` — `seasonLabel(type, year)` utility
- [ ] Implement add-row form with all fields matching `CropHistoryCreate` schema
- [ ] Implement auto yield calculation (qty / area) in UI only — no backend call needed for this derived display
- [ ] Implement save-on-advance: DELETE then POST loop
- [ ] Create `frontend/src/components/forms/HistoryTable.tsx` — reusable table component

**Relevant Context:**
- `CropHistoryCreate` fields: `season_order`, `season_name`, `season_type`, `year`, `crop_id`, `sowing_date`, `harvest_date`, `duration_days`, `cultivated_area_ha`, `production_qty`, `production_unit`, `yield_t_ha`, `notes`
- Auto yield display (`qty_t / area`) is only for user convenience — the backend also computes it and stores `yield_t_ha`; this is acceptable duplication of a display helper (not business logic)
- `GET /api/v1/crops` is cached by TanStack Query — no repeated requests

**Status:** `[ ] pending`

---

### Sub-Task 5 — Problems & Fertilizer Inputs Page (Step 3)

**Intent:** Migrate the two-tab problems/fertilizer page. Problems are selected from the catalogue returned by the new `GET /problem-types` endpoint. Fertilizers come from `GET /fertilizers`.

**Expected Outcomes:**
- Two-tab layout: "Problems faced" and "Fertilizer used"
- Problems tab: multiselect from `GET /api/v1/problem-types` (15 items)
- Severity defaults to "Moderate" (editable)
- Fertilizer tab: dropdown from `GET /api/v1/fertilizers`, qty input, season text input, estimated cost display (calculated from fertilizer `cost_rs_per_50kg` — display only)
- Entries held in local state; saved on advance (DELETE then POST loop, same pattern as history)

**Todo List:**
- [ ] Create `frontend/src/pages/ProblemsInputsPage.tsx` with Tabs component
- [ ] Create `frontend/src/hooks/useProblemTypes.ts` — TanStack Query for `GET /api/v1/problem-types`
- [ ] Create `frontend/src/hooks/useFertilizers.ts` — TanStack Query for `GET /api/v1/fertilizers`
- [ ] Implement problems multiselect with severity selector per problem
- [ ] Implement fertilizer add form with estimated cost display
- [ ] Implement save-on-advance for both problems and fertilizers
- [ ] Create `frontend/src/components/forms/ProblemSelector.tsx`
- [ ] Create `frontend/src/components/forms/FertilizerEntry.tsx`

**Relevant Context:**
- Cost estimate formula: `(qty_kg_ha / 50) × cost_rs_per_50kg × area_ha` — this is a display helper matching Streamlit behaviour; it mirrors what the backend stores as `total_cost_rs` when we POST. No business logic concern
- `ProblemCreate` fields: `problem_code`, `problem_label`, `severity`, `season_name`, `notes`
- Severity options: Low / Moderate / High

**Status:** `[ ] pending`

---

### Sub-Task 6 — Soil Data Page (Step 4)

**Intent:** Migrate the soil observation form and climate input. On submit, saves soil data to the API and immediately runs the full analysis. This is the heaviest API interaction step.

**Expected Outcomes:**
- Form pre-fills from `GET /api/v1/fields/{id}/soil` (most recent observation) if one exists
- Fields: pH, SOC%, EC, N, P, K, sand%, silt%, clay%
- Client-side validation: all values in reasonable ranges; sand+silt+clay sum warning if > 100
- Climate section: mean temp °C, seasonal rainfall mm, dry-season risk
- "Save & Run Analysis" button: saves soil → `POST /fields/{id}/soil`, then triggers analysis → `POST /fields/{id}/analyze`
- Loading state: "Analyzing soil…" spinner during analysis call (can take 1–3 seconds)
- On success: stores analysis result in `useWorkflow` state and navigates to Analysis page

**Todo List:**
- [ ] Create `frontend/src/pages/SoilDataPage.tsx`
- [ ] Implement `GET /fields/{id}/soil` prefill via TanStack Query
- [ ] Implement controlled form with range validation
- [ ] Add texture sum warning (sand + silt + clay > 100)
- [ ] Implement sequential save: POST soil → POST analyze on success
- [ ] Store `analysisResult` and `climateUsed` in workflow state
- [ ] Create `frontend/src/components/forms/SoilForm.tsx`
- [ ] Create loading state component `frontend/src/components/common/AnalysisSpinner.tsx`

**Relevant Context:**
- `SoilObservationCreate` fields: `sample_date`, `ph` (0–14), `soc_pct` (0–100), `nitrogen` (g/kg), `phosphorus` (mg/kg), `potassium` (mg/kg), `ec` (dS/m), `sand_pct`, `silt_pct`, `clay_pct`
- `ClimateInput` body for `/analyze`: `mean_temp_c`, `seasonal_rainfall_mm`, `dry_season_risk`, `heavy_rainfall_risk`
- Analysis response shape: `{ field_id, field_name, soil_assessment, degradation, remote_sensing, crop_suitability[], history_summary[], problem_summary[], fertilizer_summary[], climate_used, analysis_disclaimer }`

**Status:** `[ ] pending`

---

### Sub-Task 7 — Analysis Results Page (Step 5)

**Intent:** Display the full analysis result from the backend. Score bars, degradation risk, crop history timeline, problem pills. No calculations in React — everything is rendered from the analysis response already in workflow state.

**Expected Outcomes:**
- Soil health score (0–100) displayed as large number + filled bar
- Six parameter score bars: pH, SOC, N, P, K, EC — each with value, status pill, score bar
- Degradation section: overall score + 5 component risk labels (soc_risk, nutrient_risk, water_risk, vegetation_risk, history_risk)
- Main drivers list
- Crop history timeline (season chips)
- Reported problems pills
- "Demo remote sensing data" notice (since NDVI/BSI values are always demo)
- "View Recommendations" button → triggers optimize call → navigates to Recommendation page

**Todo List:**
- [ ] Create `frontend/src/pages/AnalysisPage.tsx`
- [ ] Create `frontend/src/components/common/ScoreBar.tsx` — reusable bar with label, value, status, fill colour
- [ ] Create `frontend/src/components/common/StatusPill.tsx` — Good/Moderate/Low/Excellent/High pill
- [ ] Create `frontend/src/components/common/RiskLabel.tsx` — colour-coded risk text
- [ ] Implement soil health section using `ScoreBar` and `StatusPill`
- [ ] Implement degradation section
- [ ] Implement history timeline
- [ ] Implement problems pills
- [ ] Add remote sensing demo notice
- [ ] Implement "View Recommendations" → `POST /fields/{id}/optimize` → store `optResult` → navigate

**Relevant Context:**
- `soil_assessment` shape: `{ ph: SoilIndicator, soc: SoilIndicator, nitrogen: SoilIndicator, phosphorus: SoilIndicator, potassium: SoilIndicator, ec: SoilIndicator, soil_health_score, degradation_risk_score, risk_level, texture_class }`
- `SoilIndicator`: `{ value, status: "Low"|"Moderate"|"Good"|"Unknown", score }`
- Score bar colour: `score >= 70` → green, `>= 45` → amber, else red (for soil params; reversed for degradation)
- `degradation`: `{ overall_degradation_score, risk_level, soc_risk, nutrient_risk, water_risk, vegetation_risk, bare_soil_risk, history_risk, main_drivers[], remote_sensing, disclaimer }`

**Status:** `[ ] pending`

---

### Sub-Task 8 — Recommendation & Rotation Page (Step 6 — Tabs 1 & 2)

**Intent:** Migrate the main recommendation experience. Top-3 crop cards with fit/limit points, full suitability table, and the CP-SAT rotation plan timeline. All scores come from the `optResult` already in workflow state.

**Expected Outcomes:**
- Primary recommendation card: crop name, suitability level pill, score/100, fit points (green bullets), limit points (amber bullets), sowing/harvest window, duration
- Two alternative crop cards below in "alt" style
- Expandable full suitability table: all crops, all 6 sub-scores, overall score, level pill
- Rotation Plan tab: season timeline cards (1 per season, alternating bg), table with score + margin/ha, "Why this rotation?" explanations, summary impacts (soil/water/disease)
- Solver status displayed ("optimal" / "feasible")

**Todo List:**
- [ ] Create `frontend/src/pages/RecommendationPage.tsx` with Tabs
- [ ] Create `frontend/src/components/recommendations/CropCard.tsx`
- [ ] Create `frontend/src/components/recommendations/SuitabilityTable.tsx`
- [ ] Create `frontend/src/components/recommendations/RotationTimeline.tsx`
- [ ] Create `frontend/src/components/recommendations/RotationTable.tsx`
- [ ] Create `frontend/src/components/recommendations/ImpactSummary.tsx`
- [ ] Implement fit/limit point derivation from sub-scores (this is pure display logic: `soil_score >= 70` → "Good soil compatibility" etc. — NOT a business calculation, just a label rule for the UI)
- [ ] Fetch crop detail (sowing_window, harvest_window, duration_days) from `/crops` cached data for display in cards

**Relevant Context:**
- `CropSuitabilityScore` fields: `crop_id`, `crop_name`, `soil_score`, `climate_score`, `water_score`, `season_score`, `rotation_score`, `economic_score`, `final_score`, `suitability_level`
- Rotation item fields: `season`, `crop`, `crop_id`, `suitability_score`, `expected_margin_rs_ha`, `explanation`
- `optResult` fields: `run_id`, `field_id`, `planning_horizon`, `status`, `rotation[]`, `total_expected_margin_rs`, `soil_impact`, `water_impact`, `disease_risk`
- Fit/limit label rules (UI-only display: "If soil_score >= 70 → show 'Good soil compatibility'") mirror the exact Streamlit logic but produce only label strings — they do not recompute scores

**Status:** `[ ] pending`

---

### Sub-Task 9 — Financial Analysis Page (Step 6 — Tab 3)

**Intent:** Migrate the financial analysis tab. Call the new `GET /crops/{id}/economics` and `GET /crops/{id}/sensitivity` endpoints. React displays the results — no calculations in the frontend.

**Expected Outcomes:**
- 4 key metric cards: Investment, Revenue, Profit, ROI — values from backend
- Investment breakdown table (seed, fertilizer, pesticide, irrigation, labor, machinery, other) — from backend
- Sensitivity analysis table (Conservative / Expected / Favorable) — from new endpoint
- Resource requirements: duration, sowing/harvest window, protection level, labor level
- Cautions section (water shortage warning if applicable, high water-need warning)
- All financial values shown per-hectare AND total (total = per-ha × field area_ha from `fieldData`)
- Disclaimer notice on all economic values

**Todo List:**
- [ ] Create `frontend/src/components/economics/FinancialCards.tsx`
- [ ] Create `frontend/src/components/economics/CostBreakdown.tsx`
- [ ] Create `frontend/src/components/economics/SensitivityTable.tsx`
- [ ] Create `frontend/src/hooks/useCropEconomics.ts` — TanStack Query for `GET /crops/{id}/economics`
- [ ] Create `frontend/src/hooks/useCropSensitivity.ts` — TanStack Query for `GET /crops/{id}/sensitivity`
- [ ] Wire financial tab in `RecommendationPage.tsx` using top crop's `crop_id`
- [ ] Total = per-ha value × `fieldData.area_ha` — this is a display multiplication only, not business logic

**Relevant Context:**
- New endpoint `GET /crops/{id}/economics` returns: `{ crop, area_ha, expected_yield_t_ha, price_rs_per_t, revenue_rs_ha, cost_breakdown[], total_cost_rs_ha, net_margin_rs_ha, total_revenue_rs, total_cost_rs, total_margin_rs, roi_pct, disclaimer }`
- New endpoint `GET /crops/{id}/sensitivity` returns: `{ Conservative: {revenue_rs_ha, profit_rs_ha, roi_pct}, Expected: {...}, Favorable: {...} }`
- The economics endpoint uses `area_ha=1.0` by default; React passes `?area_ha={fieldData.area_ha}` as query param
- Caution rules (water shortage, high water need) are derived from `problem_summary` and `crop.water_need` already in response data — no new backend call

**Status:** `[ ] pending`

---

### Sub-Task 10 — Final Report Page (Step 6 — Tab 4)

**Intent:** Migrate the summary report view and JSON download. The report is assembled entirely from data already in workflow state — no new API calls needed.

**Expected Outcomes:**
- Summary data rows: field name, location, area, irrigation, soil score/risk, degradation score/risk
- Recommended crop and rotation sequence display
- Total estimated margin
- Key observations section (derived from degradation drivers and top crop)
- "Download report (JSON)" button — same JSON structure as Streamlit
- Disclaimer notice
- "New Field" button → clears all workflow state → navigates to Step 0

**Todo List:**
- [ ] Create `frontend/src/pages/ReportPage.tsx` (or 4th tab in `RecommendationPage.tsx`)
- [ ] Implement report data assembly from workflow state
- [ ] Implement JSON download using Blob + object URL
- [ ] Implement "New Field" workflow reset
- [ ] Create `frontend/src/components/common/DataRow.tsx` — label/value pair component (reusable across pages)

**Relevant Context:**
- Report JSON structure: `{ field, location, soil_assessment, degradation, crop_history, top_recommendations[], rotation[], total_margin_rs, disclaimer }`
- Key observation rules (potassium mention, repeated-cereal mention, legume mention) are display-layer label rules derived from `degradation.main_drivers` — acceptable UI logic
- "New Field" must clear: `fieldId`, `fieldData`, `analysisResult`, `optResult`, `historyEntries`, `problemsEntries`, `fertEntries`, `climate` from workflow state

**Status:** `[ ] pending`

---

### Sub-Task 11 — README Update & Final Cleanup

**Intent:** Update README with both frontend instructions, document the migration, and verify backend integrity is untouched.

**Expected Outcomes:**
- README documents: backend start, React start, Streamlit start (legacy), test commands, production build
- Migration section explains: what changed, what is frozen, rollback procedure
- Backend integrity confirmed: `pytest` all passes, smoke test all passes
- `app/schemas/field.py` deleted (Sub-Task 1 work confirmed)
- `frontend/` present and buildable with `npm run build`
- No new warnings in `npm run build` output
- `.env` gitignored, `.env.example` committed

**Todo List:**
- [ ] Run full backend test suite: `pytest tests/ -v` — record PASS
- [ ] Run smoke test (with server running): `python tests/smoke_test.py` — record PASS
- [ ] Run `npm run build` in `frontend/` — verify no errors
- [ ] Write README backend section (uvicorn command, venv setup)
- [ ] Write README React section (npm install, npm run dev, npm run build)
- [ ] Write README Streamlit section (legacy, still runnable)
- [ ] Write README migration section (what changed, what is frozen, rollback)
- [ ] Final checklist: no hard-coded crop values in React, no duplicate calculations, no direct DB access

**Relevant Context:**
- `run.py` starts uvicorn on `0.0.0.0:8000`
- Streamlit: `python -m streamlit run streamlit_app.py`
- React dev: `cd frontend && npm run dev` → `http://localhost:5173`
- React prod build: `cd frontend && npm run build` → `frontend/dist/`

**Status:** `[ ] pending`

---

## Backend Integrity Checklist (Verified Before Implementation)

```
FastAPI application:           UNCHANGED (additions only)
Database schema:               UNCHANGED
SQLite models:                 UNCHANGED
Soil service algorithms:       UNCHANGED
Suitability service:           UNCHANGED
Degradation service:           UNCHANGED
Economics service:             UNCHANGED (called by new endpoints, not modified)
Rotation optimizer (CP-SAT):   UNCHANGED
Existing API endpoints:        UNCHANGED (no renames, no response format changes)
Existing datasets:             UNCHANGED
Streamlit app:                 UNCHANGED (still runnable)
```

## Rollback Plan

```
Stop React dev server
↓
python -m streamlit run streamlit_app.py
↓
Existing workflow restored, backend unchanged
```

React lives entirely in `frontend/` — deleting that directory restores the pre-migration state exactly.

---

## Stop Conditions

Stop and report (do NOT silently change) if:

1. An existing endpoint cannot support the React workflow without altering business logic
2. Database schema modification appears necessary
3. An existing calculation needs to change
4. Existing endpoint behaviour needs to change
5. An existing dataset needs replacement
6. Streamlit functionality depends on undocumented backend behaviour not surfaced by the audit
7. A proposed React feature requires significant backend redesign
