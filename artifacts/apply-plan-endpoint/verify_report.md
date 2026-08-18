# Verify Report — apply-plan-endpoint (Saga #309)

## Backend
`.venv/Scripts/python.exe -m pytest backend/tests/ -q`
```
209 passed, 3 warnings in 5.88s
```
(warnings are pre-existing deprecation notices unrelated to this change:
httpx/starlette TestClient deprecation, `HTTP_422_UNPROCESSABLE_ENTITY`
naming deprecation — not introduced by this task, not blocking.)

## Frontend
`npx vitest run`
```
Test Files  8 passed (8)
     Tests  138 passed (138)
```

## Gates
| Gate | Result |
|---|---|
| Backend unit/integration tests | PASS (209/209) |
| Frontend unit tests | PASS (138/138) |
| Build/typecheck | Not run separately — `npx vitest run` transpiles via Vite/esbuild; no TS errors surfaced. `tsc --noEmit` not run standalone in this pass (pre-existing project convention: `npm run build` combines both) |
| Security scan (secrets/deps) | Not run — no new dependencies added, no secrets touched |
| Manual scope check | `backend/orchestrator.py`, `backend/security.py`, `backend/db_models.py` confirmed untouched (`git diff --stat`) |

## Files changed
- `backend/models.py` — `ApplyPlanRequest`, `AppliedFileOperation`, `TransactionApplyResponse`
- `backend/main.py` — `get_session_for_apply` dependency, `POST /api/transactions/apply` endpoint
- `backend/tests/test_main_integration.py` — 5 new tests (happy path/move-on-disk, zero-op 422 x2, whitelist 403, unknown session 404, missing folder 410)
- `ui/src/components/chat/ChatScreen.tsx` — `ChatMessage.rawPlan` optional field
- `ui/src/App.tsx` — stores `rawPlan`, `handleApprovePlan` now calls the real endpoint and renders `ResultCard`
- `ui/src/App.test.tsx` — 3 new tests for approve-plan wiring; 1 obsolete no-op-assertion test removed with an explanatory comment (superseded by Saga #309's actual wiring requirement)

## Notable design deviation from plan.md (recorded, not a defect)
`plan.md` anticipated whitelist violations raising `PathWhitelistError` inside
`apply_plan`. In practice, a `fileNames` entry missing from the discovered
`pdf_files` list is caught earlier, inside `orchestrator._distribute_files_to_steps`,
which raises `PlanApplicationError` — and does so *before* any `Transaction`
row is created. The implementation distinguishes this case from a genuine
post-transaction rollback by comparing the transaction count before/after
calling `apply_plan`: no new row → treat as a 403 whitelist-style rejection;
a new row exists (and is `rolled_back`) → return 200 with that transaction's
real state. `orchestrator.py` itself was not modified.
