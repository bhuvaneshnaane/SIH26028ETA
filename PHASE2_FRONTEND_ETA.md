# Phase 2 — frontend ETA integration (verified 2026-09-25)
# Additive only: no backend file was touched in Phase 2, no existing UI flow
# was rewritten. Backend contract/in-memory behaviour is unchanged from
# PHASE1_RAIL_API.md (delay updates + history are still IN-MEMORY ONLY).

## What Phase 2 does
Surfaces the live XGBoost ETA (GET /api/trains/{id}/eta) that Phase 1 added but
nobody called: the React staff dashboard and the Flutter passenger app now show
dynamic_eta + confidence band + model provenance, and fall back to the existing
baseline/mock display whenever the backend is absent or does not know the train.

## Changed files (Phase 2 only)
React staff dashboard (railway-dashboard-staff-ui/railway-dashboard):
1. src/hooks/useTrainEta.js — NEW. Polls getTrainEta every 15 s, statuses
   idle/loading/ready/error, keeps last good payload on failure (mirrors
   useTrainDetails). idle when no VITE_API_BASE_URL.
2. src/components/TrainDetailsModal.jsx — two extra rows (ML ETA (dynamic),
   ETA model) + status-dependent hint. Baseline "Predicted ETA" untouched.
3. src/components/TrainInfoPanel.jsx — same two rows for the selected train on
   the Live Map side panel.
4. src/services/trainApi.js — lint-only: `let body = null` -> `let body` in
   postJson (eslint no-useless-assignment). Behaviour identical, no API change.

Flutter passenger app (railway-dashboard-staff-ui/railway_passenger_app_flutter/flutter_railway_passenger):
5. lib/screens/train_details_screen.dart — reads BackendTrainService
   (details + eta) when ApiConfig.hasRailBackend; badge MOCK -> BACKEND,
   scheduled/predicted/delay/status/reason come from the backend, new
   "ML ETA (dynamic)" row, notice line switches between backend/mock/unreachable.
   Any BackendException (e.g. 404 for a train the backend does not hold) keeps
   the previous mock rendering — no crash, badge stays MOCK.
6. lib/models/train.dart — added train 11013 (Coimbatore Express) with the
   ED-CBE corridor halts from GET /api/stations. The backend only holds 11013,
   so this is the one mock train that can demonstrate the live integration.
7. lib/l10n/app_en.arb + app_hi.arb (+ regenerated app_localizations*.dart) —
   new keys: commonBackend, detailsMlEta, detailsBackendNotice,
   detailsBackendUnavailable(error).
8. .env + .env.example — API_BASE_URL=http://localhost:8000 (opt-in; empty
   default keeps mock-only mode). Android emulator: http://10.0.2.2:8000.
9. test/widget_test.dart — replaced the broken Flutter template counter test
   (referenced a nonexistent `MyApp`, so analyze/test could never pass) with
   5 hermetic tests for BackendTrainService parsing + the mock train list.

## Verification (all green)
- React: `npm run lint` (0 problems), `npm run build` (✓ ~320 ms).
  Dev server :5173 picks the files up by HMR; /src/hooks/useTrainEta.js transforms 200.
- Flutter: `flutter analyze --no-pub` -> No issues found;
  `flutter test` -> All tests passed (8: 3 pre-existing + 5 new).
- Backend untouched and still healthy: GET /health, /api/trains/positions,
  /api/trains/11013, /api/trains/11013/eta, /api/delays/history all 200.

## Limits to remember
- Backend holds ONE train (11013). Any other train number -> 404 -> both UIs
  keep MOCK/DEMO data by design.
- Delay updates/history are in-memory: restarting uvicorn empties
  GET /api/delays/history. Never described as persisted.
- "Predicted ETA" (baseline = scheduled + delay) and "ML ETA (dynamic)"
  (XGBoost, computed on demand, never stored) are shown side by side on purpose.
- Live Map / train search in Flutter still use simulated positions; wiring
  GET /api/trains/positions there is intentionally NOT part of Phase 2.
