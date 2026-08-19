# Google Sheets Summary Tab Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create and maintain a Summary table on the first sheet of Google Sheets that calculates total amounts, net amounts, and Stripe fees across all monthly tabs using Google Sheets formulas.

**Architecture:** Extend `sheets_client.py` with summary sheet initialization and month-formula registration (`USER_ENTERED`). Add `sync_summary_sheet()` to synchronize all existing `YYYY-MM` tabs into the Summary sheet. Update `backfill_sheets.py` with `--sync-summary` CLI support.

**Tech Stack:** Python 3.13, `gspread`, `pytest`, `pytest-mock`

---

### Task 1: Summary Sheet Helper Functions in `sheets_client.py` and Unit Tests

**Files:**
- Modify: `sheets_client.py`
- Modify: `tests/test_sheets_client.py`

**Step 1: Write failing tests in `tests/test_sheets_client.py`**
- `test_get_or_create_summary_sheet_renames_first_sheet_and_initializes_headers`
- `test_ensure_month_in_summary_appends_formula_row`
- `test_ensure_month_in_summary_skips_existing_month`
- `test_get_or_create_sheet_registers_month_in_summary`

**Step 2: Run tests to verify failure**
Run: `venv/bin/pytest tests/test_sheets_client.py`
Expected: FAIL

**Step 3: Implement `_get_or_create_summary_sheet`, `_ensure_month_in_summary`, and update `_get_or_create_sheet` in `sheets_client.py`**

**Step 4: Run tests to verify they pass**
Run: `venv/bin/pytest tests/test_sheets_client.py`
Expected: PASS

---

### Task 2: Implement `sync_summary_sheet()` in `sheets_client.py` and Unit Tests

**Files:**
- Modify: `sheets_client.py`
- Modify: `tests/test_sheets_client.py`

**Step 1: Write failing tests in `tests/test_sheets_client.py`**
- `test_sync_summary_sheet_scans_and_adds_all_month_tabs`

**Step 2: Run tests to verify failure**
Run: `venv/bin/pytest tests/test_sheets_client.py -k test_sync_summary`
Expected: FAIL

**Step 3: Implement `sync_summary_sheet` in `sheets_client.py`**
- Regex match `^\d{4}-\d{2}$` for all worksheet titles.
- Chronologically sort tab names.
- Ensure summary sheet exists.
- Add any missing month tabs to the Summary sheet with `value_input_option="USER_ENTERED"`.

**Step 4: Run tests to verify they pass**
Run: `venv/bin/pytest tests/test_sheets_client.py`
Expected: PASS

---

### Task 3: Add `--sync-summary` Option in `backfill_sheets.py` and Run Verification

**Files:**
- Modify: `backfill_sheets.py`

**Step 1: Add `--sync-summary` CLI argument and logic to `backfill_sheets.py`**
- Support running `python backfill_sheets.py --sync-summary` standalone or alongside backfill.

**Step 2: Run full test suite**
Run: `venv/bin/pytest`
Expected: 100% PASS
