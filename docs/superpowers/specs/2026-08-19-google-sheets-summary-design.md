# Google Sheets Summary Tab — Design Spec

**Date:** 2026-08-19  
**Status:** Approved

## Overview

Add a summary table (`Summary` tab) on the first sheet of the Google Spreadsheet to automatically aggregate totals (Total Amount, Total Net, Stripe Fee) for each monthly tab (`YYYY-MM`) as well as an overall Total row at the top.

## Summary Tab Structure

- **Tab Name:** `Summary` (reuses the default first worksheet, renaming it if necessary).
- **Header (Row 1):**
  `Month` | `Total Amount` | `Total Net` | `Stripe Fee`
- **Total (Row 2):**
  `Total` | `=SUM(B3:B)` | `=SUM(C3:C)` | `=SUM(D3:D)`
- **Monthly Rows (Row 3+):**
  For each tab `YYYY-MM`:
  - Column A (`Month`): `'YYYY-MM'` (e.g. `2024-06`)
  - Column B (`Total Amount`): `=SUM('YYYY-MM'!F2:F)`
  - Column C (`Total Net`): `=SUM('YYYY-MM'!H2:H)`
  - Column D (`Stripe Fee`): `=SUM('YYYY-MM'!G2:G)`

## Source Columns on Monthly Tabs (`YYYY-MM`)

| Column Index | Header | Purpose |
|---|---|---|
| F (Col 6) | `Amount` | Total transaction amount |
| G (Col 7) | `Stripe Fee` | Fee charged by Stripe |
| H (Col 8) | `Net` | Net amount received (`Amount - Stripe Fee`) |

## Implementation Details

### 1. `sheets_client.py`
- Add constants:
  - `_SUMMARY_TAB_NAME = "Summary"`
  - `_SUMMARY_HEADER = ["Month", "Total Amount", "Total Net", "Stripe Fee"]`
  - `_SUMMARY_TOTAL_ROW = ["Total", "=SUM(B3:B)", "=SUM(C3:C)", "=SUM(D3:D)"]`
- Functions:
  - `_get_or_create_summary_sheet(spreadsheet)`:
    - Checks for `Summary` worksheet. If not found, gets the first worksheet (`spreadsheet.get_worksheet(0)`) and updates its title to `Summary` (or creates a new one at index 0 if none exists).
    - If the worksheet has no rows or missing header, writes `_SUMMARY_HEADER` (Row 1) and `_SUMMARY_TOTAL_ROW` (Row 2) using `value_input_option="USER_ENTERED"`.
    - Returns the summary worksheet.
  - `_ensure_month_in_summary(spreadsheet, tab_name: str)`:
    - Ensures the summary sheet exists.
    - Checks if `tab_name` already exists in column A (Row 3+).
    - If not present, appends `[tab_name, f"=SUM('{tab_name}'!F2:F)", f"=SUM('{tab_name}'!H2:H)", f"=SUM('{tab_name}'!G2:G)"]` with `value_input_option="USER_ENTERED"`.
  - Update `_get_or_create_sheet(spreadsheet, tab_name)`:
    - When a new monthly sheet is created, call `_ensure_month_in_summary(spreadsheet, tab_name)`.
  - `sync_summary_sheet(spreadsheet=None)`:
    - Finds all existing worksheets in spreadsheet matching regex `^\d{4}-\d{2}$`.
    - Sorts month tabs chronologically.
    - Re-initializes/syncs the `Summary` tab so all existing months are listed.

### 2. `backfill_sheets.py`
- Add `--sync-summary` flag (or automatically run summary sync during backfill) so historical sheets already in the spreadsheet are registered in `Summary`.

### 3. Error Handling & Resilience
- Google Sheets operations use `value_input_option="USER_ENTERED"` to ensure formulas are parsed correctly.
- Summary sheet operations are wrapped in try-except in runtime path (non-blocking for Telegram notifications and polling).

### 4. Testing
- Unit tests in `tests/test_sheets_client.py` verifying:
  - Initializing summary sheet when empty.
  - Adding a month formula row to summary.
  - Not duplicating month row if already in summary.
  - Formula format correctness (`USER_ENTERED`).
  - `sync_summary_sheet()` populating all `YYYY-MM` tabs in chronological order.
