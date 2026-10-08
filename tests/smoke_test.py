"""
End-to-end smoke test via live HTTP against the running server.

Usage:
    python run.py                          # start server first (Terminal 1)
    python tests/smoke_test.py             # run this script (Terminal 2)
"""
import urllib.request
import urllib.error
import json
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = "http://127.0.0.1:8000/api/v1"

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.loads(r.read())


def post(path, data=None):
    body = json.dumps(data).encode() if data else b"{}"
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def patch(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def delete(path):
    req = urllib.request.Request(BASE + path, method="DELETE")
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else {}


def main():
    errors = []

    # ── 1. Health check ───────────────────────────────────────────────────────────
    try:
        h = get("/health")
    except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
        print(f"\n[ERROR] Connection Error: Unable to connect to backend server at {BASE}")
        print(f"        Reason: {e}")
        print("\n        The smoke test runs against a live server.")
        print("        Please start the server first in another terminal:")
        print("            python run.py\n")
        return 1

    assert h["status"] == "ok", f"Health check failed: {h}"
    print(f"[1] Health: {h['status']}")

    # ── 2. List crops catalogue ───────────────────────────────────────────────────
    crops_list = get("/crops")
    assert len(crops_list) >= 7, f"Expected >= 7 crops, got {len(crops_list)}"
    print(f"[2] Crop catalogue: {len(crops_list)} crops")
    for c in crops_list[:4]:
        print(f"    {c['id']:2d}. {c['name']}")

    # ── 3. List fertilizer products ───────────────────────────────────────────────
    ferts = get("/fertilizers")
    assert len(ferts) >= 5, f"Expected >= 5 fertilizers, got {len(ferts)}"
    print(f"[3] Fertilizer catalogue: {len(ferts)} products")

    # ── 3b. Problem types catalogue (new endpoint) ───────────────────────────────
    prob_types = get("/problem-types")
    assert len(prob_types) >= 10, f"Expected >= 10 problem types, got {len(prob_types)}"
    print(f"[3b] Problem types: {len(prob_types)} entries")

    # ── 3c. Fields list (new endpoint) ───────────────────────────────────────────
    fields_list = get("/fields")
    print(f"[3c] Fields list: {len(fields_list)} fields currently in DB")

    # ── 4. Find-or-create field via map click (new workflow) ─────────────────────
    # Uses canonical schema keys: latitude / longitude (not lat / lng)
    field = post("/fields/find-or-create", {
        "latitude": 17.385,
        "longitude": 78.487,
        "name": "Smoke-Test Field",
        "area_ha": 2.5,
        "irrigation_type": "Irrigated",
    })
    fid = field["id"]
    print(f"[4] Field id={fid}: '{field['name']}' | area={field['area_ha']} ha")

    # ── 5. Update field metadata (PATCH) ─────────────────────────────────────────
    updated = patch(f"/fields/{fid}", {
        "farm_name": "Reddy Farms",
        "farming_type": "Conventional",
        "soil_type": "Black Cotton",
    })
    assert updated["farm_name"] == "Reddy Farms", f"PATCH failed: {updated}"
    print(f"[5] Updated farm_name='{updated['farm_name']}' soil_type='{updated.get('soil_type')}'")

    # Clear prior child records for this test field so re-runs remain idempotent
    delete(f"/fields/{fid}/history")
    delete(f"/fields/{fid}/problems")
    delete(f"/fields/{fid}/fertilizers")

    # ── 6. Add crop history entries ───────────────────────────────────────────────
    # Use crop_id=1 (Rice) from the seeded catalogue
    h1 = post(f"/fields/{fid}/history", {
        "crop_id": 1,
        "season_order": 1,
        "season_name": "Kharif 2022 (June–October)",
        "season_type": "Kharif",
        "year": 2022,
    })
    h2 = post(f"/fields/{fid}/history", {
        "crop_id": 2,
        "season_order": 2,
        "season_name": "Rabi 2022–23 (November–March)",
        "season_type": "Rabi",
        "year": 2022,
    })
    h3 = post(f"/fields/{fid}/history", {
        "crop_id": 3,
        "season_order": 3,
        "season_name": "Kharif 2023 (June–October)",
        "season_type": "Kharif",
        "year": 2023,
    })
    history_list = get(f"/fields/{fid}/history")
    assert len(history_list) == 3, f"Expected 3 history records, got {len(history_list)}"
    print(f"[6] Crop history: {len(history_list)} seasons recorded")
    for hs in history_list:
        print(f"    Season {hs['season_order']}: crop_id={hs['crop_id']} | {hs.get('season_name', '')}")

    # ── 7. Add field problems ─────────────────────────────────────────────────────
    # Uses canonical schema key: problem_code (not problem_type)
    p1 = post(f"/fields/{fid}/problems", {
        "problem_code": "excess_water",
        "problem_label": "Excess water / waterlogging",
        "severity": "Moderate",
        "notes": "Low-lying patch floods after heavy rain",
    })
    problems_list = get(f"/fields/{fid}/problems")
    assert len(problems_list) >= 1, f"Expected ≥1 problem, got {len(problems_list)}"
    print(f"[7] Field problems: {len(problems_list)} recorded")
    for p in problems_list:
        print(f"    {p['problem_code']} | severity={p['severity']}")

    # ── 8. Add fertilizer usage ───────────────────────────────────────────────────
    fu = post(f"/fields/{fid}/fertilizers", {
        "fertilizer_id": 1,
        "quantity_kg_ha": 100.0,
        "season_name": "Kharif 2023",
    })
    fert_usage = get(f"/fields/{fid}/fertilizers")
    assert len(fert_usage) >= 1, f"Expected ≥1 fertilizer usage, got {len(fert_usage)}"
    print(f"[8] Fertilizer usage: {len(fert_usage)} records")

    # ── 9. Add soil observation ───────────────────────────────────────────────────
    soil_obs = post(f"/fields/{fid}/soil", {
        "ph": 6.8,
        "soc_pct": 0.58,
        "nitrogen": 0.12,
        "phosphorus": 22.0,
        "potassium": 190.0,
        "ec": 0.55,
    })
    assert soil_obs.get("id"), f"Soil observation missing id: {soil_obs}"
    print(f"[9] Soil observation id={soil_obs['id']} | pH={soil_obs['ph']} | SOC={soil_obs['soc_pct']}%")

    # ── 10. Full analysis (with problem penalties) ────────────────────────────────
    analysis = post(f"/fields/{fid}/analyze", {
        "mean_temp_c": 27.0,
        "seasonal_rainfall_mm": 1050.0,
        "dry_season_risk": "Moderate",
        "heavy_rainfall_risk": "Low",
    })
    soil_a = analysis["soil_assessment"]
    deg    = analysis["degradation"]
    print(f"[10] Analysis:")
    print(f"    Soil health score : {soil_a['soil_health_score']}")
    print(f"    pH status         : {soil_a['ph']['status']}")
    print(f"    Degradation score : {deg['overall_degradation_score']} | risk={deg['risk_level']}")
    top3 = analysis["crop_suitability"][:3]
    print(f"    Top 3 crops       : {[(c['crop_name'], c['final_score']) for c in top3]}")
    assert len(analysis["crop_suitability"]) >= 5, "Expected ≥5 ranked crops"

    # ── 11. Crop optimization ─────────────────────────────────────────────────────
    opt = post(f"/fields/{fid}/optimize", {
        "horizon": 4,
        "mean_temp_c": 27.0,
        "seasonal_rainfall_mm": 1050.0,
        "dry_season_risk": "Moderate",
        "heavy_rainfall_risk": "Low",
    })
    print(f"[11] Optimization:")
    print(f"    Status            : {opt['status']}")
    print(f"    Total margin      : Rs. {opt['total_expected_margin_rs']:,.0f}")
    print(f"    Soil impact       : {opt['soil_impact']}")
    assert opt["status"] in ("optimal", "feasible"), f"Optimizer status: {opt['status']}"
    assert len(opt["rotation"]) == 4, f"Expected 4 seasons, got {len(opt['rotation'])}"
    rotation = opt["rotation"]
    for s in rotation:
        print(f"    Season {s['season']}: {s['crop']:12s}  score={s['suitability_score']:5.1f}"
              f"  margin_ha=Rs. {s['expected_margin_rs_ha']:>10,.0f}")
    # Verify no consecutive same crop
    for i in range(len(rotation) - 1):
        if rotation[i]["crop"] == rotation[i + 1]["crop"]:
            errors.append(
                f"Same crop in consecutive seasons: {rotation[i]['crop']} at seasons {i+1},{i+2}"
            )

    # ── 12. Retrieve stored optimization run ─────────────────────────────────────
    run_id = opt["run_id"]
    stored = get(f"/optimization/{run_id}")
    assert stored["run_id"] == run_id, f"Run id mismatch: {stored}"
    assert len(stored["rotation"]) == 4
    print(f"[12] Stored run id={stored['run_id']} | status={stored['status']} | seasons={len(stored['rotation'])}")

    # ── 13. List optimization runs for field (new endpoint) ──────────────────────
    runs_list = get(f"/fields/{fid}/optimization-runs")
    assert len(runs_list) >= 1, f"Expected >= 1 run in list, got {len(runs_list)}"
    print(f"[13] Optimization runs for field: {len(runs_list)} run(s)")

    # ── 14. Crop economics endpoint (new endpoint) ────────────────────────────────
    rice_id = crops_list[0]["id"]
    econ = get(f"/crops/{rice_id}/economics?area_ha=2.5")
    assert econ.get("net_margin_rs_ha") is not None, f"Economics missing net_margin_rs_ha: {econ}"
    print(f"[14] Crop economics for '{econ['crop']}': "
          f"margin/ha=Rs. {econ['net_margin_rs_ha']:,.0f} | ROI={econ.get('roi_pct')}%")

    # ── 15. Crop sensitivity endpoint (new endpoint) ──────────────────────────────
    sens = get(f"/crops/{rice_id}/sensitivity?area_ha=2.5")
    assert "Conservative" in sens and "Expected" in sens and "Favorable" in sens, \
        f"Sensitivity missing scenarios: {list(sens.keys())}"
    print(f"[15] Sensitivity for crop {rice_id}: "
          f"Conservative profit=Rs. {sens['Conservative']['profit_rs_ha']:,.0f} | "
          f"Favorable profit=Rs. {sens['Favorable']['profit_rs_ha']:,.0f}")

    # ── Summary ───────────────────────────────────────────────────────────────────
    if errors:
        print(f"\n[FAIL] FAILURES ({len(errors)}):")
        for e in errors:
            print(f"   * {e}")
        return 1
    else:
        print("\n[PASS] ALL CHECKS PASSED - End-to-end pipeline (find-or-create -> history -> "
              "problems -> fertilizers -> soil -> analyze -> optimize -> new endpoints) "
              "works correctly.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
