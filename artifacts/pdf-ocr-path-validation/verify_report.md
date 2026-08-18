# Verify Report — Saga #307

## Test Gate
`python -m pytest backend/ -v` (venv: `.venv`)

Result: **196 passed**, 0 failed, 138 warnings (pre-existing `datetime.utcnow()`
deprecation warnings, unrelated to this change).

New tests included and passing:
- `backend/tests/test_orchestrator.py::test_apply_plan_runs_ocr_on_a_pdf_inside_allowed_root_without_moving_it`
- `backend/tests/test_orchestrator.py::test_apply_plan_rejects_ocr_of_a_path_outside_allowed_root`
- `backend/tests/test_models.py::test_plan_step_rejects_ocr_with_more_than_one_file_name`

No regressions in MOVE/COPY/DELETE/RENAME/LIST/MERGE/SPLIT/revert/recover/purge
test suites.

## Build/Lint
N/A — pure-Python backend, no separate build step for this change; no
lint gate configured in this project's pipeline beyond pytest.

## Security
- `OperationType.OCR` wired into `apply_plan` in `backend/orchestrator.py`
  with an explicit `is_path_allowed(source_path, allowed_root)` check
  BEFORE calling `ocr_pdf_file` — matches the MERGE/SPLIT/DELETE pattern.
- `backend/pdf_ocr.py` left untouched — no duplicated path-validation
  logic, security choke point stays centralized in orchestrator.py per
  the red-team requirement.
- `validate_plan_paths` (called at the top of `apply_plan`) already
  validates every `pdf_files` entry against `allowed_root` as a first
  layer; the new `is_path_allowed` check in the OCR step is an explicit
  second layer directly guarding the `ocr_pdf_file` call site, making
  the "never pass a raw path" guarantee visible at the call site itself.

## Red-Team Round
Independent `obss-red-team` review (2026-08-18): `ready_to_commit: yes`.
One low-severity nit fixed before commit: the negative test
`test_apply_plan_rejects_ocr_of_a_path_outside_allowed_root` asserted a
generic `Exception` instead of the specific `PathWhitelistError` — tightened
to assert `PathWhitelistError` explicitly so the test can't pass green for
the wrong reason (e.g. an unrelated AttributeError). Re-ran full suite after
the fix: still 196 passed.

## Gate Summary
| Gate | Result |
|---|---|
| Unit tests | PASS (196/196) |
| Regression (existing MERGE/SPLIT/DELETE tests) | PASS |
| Security (path validation centralized, no duplication in pdf_ocr.py) | PASS |
| Build | N/A |
