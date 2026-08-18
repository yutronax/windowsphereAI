# Verify Report — purge-lock (Saga #302)

## Test run (post red-team fixes)
Command: `python -m pytest backend/tests/ -q` (venv:
`C:\Users\YUSUF ÇİNAR\AppData\Local\Programs\Python\Python311\python.exe`)

Result: **203 passed, 0 failed** — full backend test suite, run directly
by the orchestrating agent.

## Coverage of this change
- Race regression test:
  `test_revert_transaction_and_purge_expired_delete_backups_do_not_lose_the_race`
  in `backend/tests/test_orchestrator.py` — confirmed RED before the
  implementation and GREEN after; updated once (Senaryo 2's monkeypatch
  target moved from `shutil.rmtree` to `_claim_transaction_status`) after
  the red-team fix changed *when* purge's claim happens.
- New endpoint-level regression test:
  `test_revert_endpoint_reports_the_real_db_status_after_losing_the_claim_race`
  in `backend/tests/test_main_integration.py` — proves the red-team-found
  stale-status bug (endpoint returning a pre-claim in-memory `status` after
  `revert_transaction` loses its race) is fixed by `db.refresh(transaction)`
  in `backend/main.py`.
- All pre-existing tests still pass — no regressions to `revert_transaction`,
  `purge_expired_delete_backups`, or any other orchestrator/endpoint
  behavior (MOVE/COPY/DELETE/RENAME/MERGE/SPLIT/OCR, allowed_root
  enforcement from Saga #301, 404/409/200 revert endpoint contract, etc).
- Full suite (`backend/tests/`): **203 passed**.

## Files changed
- `backend/orchestrator.py` — added `_claim_transaction_status` helper
  (compare-and-swap UPDATE via `session.execute(update(...))`, `rowcount`
  check); wired into `revert_transaction` (claim at the end, right before
  writing the final status) and `purge_expired_delete_backups` (three-state
  claim chain `"committed"`→`"purging"`→`"backup_purged"`, each step
  immediately committed, so no write lock is held across `shutil.rmtree`).
- `backend/main.py` — `revert_transaction_endpoint` now calls
  `db.refresh(transaction)` after catching `TransactionRevertError`, so the
  response always reflects the DB's actual current status instead of a
  stale pre-claim in-memory value.
- `backend/tests/test_orchestrator.py` — race regression test (both
  interleavings).
- `backend/tests/test_main_integration.py` — endpoint stale-status
  regression test.

## Independent red-team review (obss-red-team subagent, against the diff before these fixes)
Findings and disposition:
1. **Medium — fixed in-scope**: `purge_expired_delete_backups` held an
   uncommitted claim UPDATE open across `shutil.rmtree`, holding SQLite's
   whole-database write lock for the duration of a potentially slow
   filesystem call, blocking every other DB writer in the app. Fixed by
   switching to a three-state claim chain where every claim step commits
   immediately and `rmtree` runs with no open write transaction.
2. **Medium — fixed in-scope**: the revert endpoint could return a stale
   `transaction.status` (e.g. `"committed"`) to the client after
   `revert_transaction`'s claim lost a race, contradicting the endpoint's
   own documented invariant. Fixed with `db.refresh(transaction)`.
3. **Low — accepted, filed as follow-up (not blocking, out of scope for
   this low-priority task)**: `_claim_transaction_status`'s
   `session.execute()` has no try/except around a possible raw
   `OperationalError` under real lock contention (distinct from the
   deliberate `rowcount==0` non-error path); it would propagate as an
   unhandled 500 instead of the endpoint's documented 200/409 contract.
4. **Low — accepted, filed as follow-up**: the `except OSError` guard in
   `purge_expired_delete_backups`'s rmtree failure path isn't fully
   exhaustive against every conceivable exception type from `shutil.rmtree`
   on unusual filesystems.

Findings 3 and 4 are genuine but low-severity, unlikely under this
project's single-process desktop deployment, and orthogonal to the P0/P1
safety property this task targets (no two sessions can both win the same
claim) — filed as a follow-up Saga task rather than expanding this
low-priority task's scope further.

Both P0/P1 safety properties from `atdd.md`'s Kabul Kriterleri are met and
covered by tests.
