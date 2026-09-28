# Phase 3 — Flutter live map positions integration (verified 2026-09-25)
# Additive only: no backend file touched, existing mock/simulation paths kept
# intact as the fallback. Read PHASE1_RAIL_API.md first (contract + in-memory
# storage rules), then PHASE2_FRONTEND_ETA.md (details screen + ML ETA).

## What Phase 3 does
1. Details screen wiring (GET /api/trains/11013 + GET /api/trains/11013/eta)
   for train 11013 ONLY, with mock fallback for every other train id —
   this landed in Phase 2 and was re-verified in Phase 3, not rewritten.
2. Live map: polls GET /api/trains/positions every 8 s and, when the backend
   returns a position for the open train, moves the marker from SIM (orange)
   to LIVE (teal), shows speed + location label, and replaces the "backend is
   not connected" notice. Otherwise nothing changes: no API_BASE_URL -> zero
   backend calls; unknown train id -> simulated marker with an explanatory
   notice; backend outage -> last good position kept + outage notice.

## API contract used (verified live on :8000)
GET /api/trains/positions -> 200 {"positions":[
  {"train_id":"11013","latitude":11.1119,"longitude":77.2506,
   "speed_kph":130.0,"location_label":"Between Vanjipalayam and Somanur",
   "progress":0.604,"updated_at":"2026-09-25T02:51:27Z"}]}
- There is NO per-train position route; clients filter the list by train_id.
- lat/lng come from the server clock, so polling shows real corridor movement.
- The list held only train 11013 (api/state.py _TRAINS).
- CORS: allow_origin_regex ^http://(localhost|127\.0\.0\.1)(:\d+)?$ covers
  Flutter web's ephemeral port; native builds send no Origin header.
- API_BASE_URL verified in flutter_railway_passenger/.env -> http://localhost:8000
  (Android emulator: http://10.0.2.2:8000).

## Changed files (Phase 3 only)
1. lib/screens/live_map_screen.dart — polling timer (8 s, only when
   ApiConfig.hasRailBackend), ValueNotifier<LatLng?> _backendPosition,
   _loadBackendPosition() with in-flight guard, _activeTrainPosition
   (backend ?? simulator), parameterised notice text, speed/location line,
   _centerOnTrain() now centres on the active position, dispose cancels the
   timer/notifier/client. The marker builder prefers the backend position and
   falls back to TrainPositionSimulator untouched.
2. lib/services/backend_train_service.dart — ADDITIVE ONLY: positionFor(trainId)
   -> Future<BackendPosition?> (null = backend does not hold that train, which
   is the expected non-error answer). positions()/details()/eta() unchanged.
3. lib/l10n/app_en.arb + app_hi.arb (+ flutter gen-l10n output) — 4 new keys:
   mapMarkerBackend ("LIVE"), mapBackendNotice, mapBackendNoPosition,
   mapBackendUnavailable(error).
4. test/widget_test.dart — +2 tests: positions() parsing, and
   positionFor() -> found for 11013 / null for 99999 and blank ids.
5. PHASE3_MAP_POSITIONS.md (this file).

## NOT changed
api/* (backend), train_simulation_service.dart (kept as the mock fallback),
train_details_screen.dart (Phase 2 work), models/*, React dashboard.

## Verification (all green)
- flutter analyze --no-pub -> No issues found.
- flutter test -> All tests passed (10: 3 simulation + 5 Phase 2 + 2 Phase 3).
- Backend re-checked live: /health, /api/trains/positions,
  /api/trains/11013, /api/trains/11013/eta all 200; no backend file modified.

## Limits to remember
- Backend holds ONE train (11013); every other train keeps SIM/mock data.
- Delay updates + history remain IN-MEMORY ONLY (lost on uvicorn restart).
- Positions are polled, not streamed; 8 s interval, single in-flight request.
- Marker label 'SIM' stays hardcoded English (pre-existing); 'LIVE' is
  localised through mapMarkerBackend.
