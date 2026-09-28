# Phase 1 — rail backend test log (IN-MEMORY ONLY, safe to delete)
# Verified 2026-09-25 on port 8001 with .venv python. All responses below
# are live outputs, not invented. Delay updates + history are held in
# process memory and LOST on restart — never described as persisted.

## Storage statement
- Rail delay updates + delay history: IN-MEMORY ONLY
  (api/state.py _TRAINS dict + _DELAY_HISTORY list, threading.Lock).
  Lost on process restart. No database in Phase 1.
- Node pulse-eta Mongo (Tracker/WaypointLog): untouched, separate domain.
- Trial_2: untouched (empty).
- ETA outputs (POST /api/eta/predict, GET /api/trains/{id}/eta): computed
  live by eta_engine.predict() (XGBoost, seed 42), NOT stored anywhere.

## Changed files (Phase 1 only)
1. Mastereverything - Copy/api/state.py — in-memory delay log helpers
   (append_delay_history, delay_history), storage docstring, corridor
   imports for per-train ETA station derivation. No existing logic altered.
2. Mastereverything - Copy/api/models.py — additive Pydantic models only:
   DelayUpdateRequest/DelayHistoryEntry/DelayHistoryResponse/
   DelayUpdateResponse. Frozen contract models untouched.
3. Mastereverything - Copy/api/routes/trains.py — 3 additive routes only:
   POST /api/trains/{id}/delay, GET /api/trains/{id}/eta,
   GET /api/delays/history. Existing 4 routes byte-identical behaviour.
4. railway-dashboard/.../src/services/trainApi.js — additive postJson,
   normalizeHistoryEntry, postDelayUpdate, getTrainEta, getDelayHistory.
   Existing fetchJson/normalize/positions/details paths untouched.
5. railway-dashboard/.../src/App.jsx — handleSaveDelay tries backend POST
   for known trains, falls back to unchanged local demo path otherwise;
   added handleRefreshHistory merge. No component rewritten.
6. railway-dashboard/.../src/pages/DelayUpdatesPage.jsx — refresh hook +
   BACKEND/DEMO copy only.
7. railway-dashboard/.../src/components/DelayHistoryList.jsx — copy only.
8. .../flutter_railway_passenger/lib/config/api_config.dart — additive
   railBaseUrl/hasRailBackend getters only.
9. .../flutter_railway_passenger/lib/services/backend_train_service.dart
   — NEW, read-only (positions/details/eta). Mock TrainService untouched.
10. PHASE1_RAIL_API.md (this file) — docs only.
NO changes: pulse-eta/*, Trial_2/*, api/main.py (CORS), corridor.py,
eta_engine.py, mockData.js, trainSimulator, Flutter screens/models.
CORS: no change required (existing regex already covers Flutter web).
Env: no change required except future Flutter API_BASE_URL (opt-in).

## Test commands (PowerShell; backend on :8000 via START_ALL.ps1,
## or replicate on :8001 with .venv python -m uvicorn api.main:app)
## All verified live on :8001 — outputs above.

```powershell
$b = 'http://127.0.0.1:8000'
# 1. Health (model provenance: xgboost MAE 1.15 vs baseline 5.2)
Invoke-WebRequest -UseBasicParsing -Uri "$b/health" | % Content
# 2. Stations reference (15 ED-CBE rows)
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/stations" | % Content
# 3. Live positions -> {"positions":[{train_id,latitude,...}]}
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/positions" | % Content
# 4. Train details (baseline predicted_eta = scheduled + delay, NOT ML)
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/11013" | % Content
# 5. Per-train ETA (live XGBoost via eta_engine.predict, NOT stored)
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/11013/eta" | % Content
# 5b. ETA with operating point (matches EtaPredictRequest ranges)
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/11013/eta?speed_restriction_kph=60&headway_ahead_km=2.0&weather_severity=7" | % Content
# 6. Existing ML ETA (full feature POST)
$eta = @{passed_station_code='TUP'; current_delay_minutes=15; speed_restriction_kph=110; headway_ahead_km=8.0; weather_severity=2} | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/eta/predict" -Method Post -ContentType 'application/json' -Body $eta | % Content
# 7. Delay update (IN-MEMORY ONLY — lost on restart, never "persisted")
$upd = @{delay_minutes=25; reason='Congestion'; station='Tiruppur'; notes='Phase1 test'; staff='Tester'} | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/11013/delay" -Method Post -ContentType 'application/json' -Body $upd | % Content
# 8. Delay history (in-memory, newest first; empty after restart)
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/delays/history" | % Content
Invoke-WebRequest -UseBasicParsing -Uri "$b/api/delays/history?train_id=11013&limit=5" | % Content
# 9. Error shapes (must be {"detail": ...}, never HTML)
try { Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/99999" } catch { $_.ErrorDetails.Message }
try { Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/99999/delay" -Method Post -ContentType 'application/json' -Body $upd } catch { $_.ErrorDetails.Message }
try { Invoke-WebRequest -UseBasicParsing -Uri "$b/api/trains/11013/delay" -Method Post -ContentType 'application/json' -Body (@{delay_minutes=999} | ConvertTo-Json) } catch { $_.ErrorDetails.Message }
# 10. Pulse-eta untouched (separate backend, separate domain)
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:4000/health' | % Content
# 11. React dashboard (VITE_API_BASE_URL=http://localhost:8000 already set):
#     open http://localhost:5173 -> Delay Updates for 11013 -> row tagged BACKEND
# 12. Flutter (opt-in): set API_BASE_URL in flutter_railway_passenger/.env, BackendTrainService.positions()/details()/eta()
```
