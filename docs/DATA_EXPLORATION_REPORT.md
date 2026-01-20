# Data Exploration Report
**Date:** 2026-01-19
**Source:** Local Filesystem & External Drive `/Volumes/Miguel`

## Overview
Per user request, a comprehensive exploration of local data sources and the external drive `swimdump` (located at `/Volumes/Miguel/swimdatadump`) was conducted to identify available data for backtesting and analysis.

## Findings

### 1. External Drive: `swimdatadump`
**Path:** `/Volumes/Miguel/swimdatadump`

This directory appears to be the primary backup location for Team Manager and Meet Manager data.

*   **Master Database:** `Database Backups/SSTdata.mdb` (36MB)
    *   This is likely the master Microsoft Access database containing all historical data for Seton Swimming Team (SST).
    *   Contains tables for Athletes, Results, Meets, Teams, etc.
    *   **Recommendation:** This is the "Gold Standard" source of truth.
*   **Backups:** `Database Backups/*.zip`
    *   Sequential backups (e.g., `SwTM8BkupSSTdata-52.zip`). Can be used to restore state at specific points in time.
*   **Meet Files:** `swmeets4/`, `swmeets7/`, `swmeets8/`
    *   Likely contain specific Meet Manager databases (`.mdb`) for individual meets.
*   **Entry Files:** `SST-Entries-*.ZIP`
    *   Contains strict entry files for specific upcoming (or past) meets (e.g., `SST-Entries-VCAC Regular Season Championship-03Jan2026-001.ZIP`).

### 2. Local CSV Exports
**Path:** `data/real_exports/csv/`

These files (`teams.csv`, `athletes.csv`, `results.csv`, `meets.csv`) appear to be direct exports from the `SSTdata.mdb`.

*   **Status:** Validated.
*   **Usability:** High. Python `pandas` reads them natively.
*   **Coverage:** Confirmed to contain historical results back years, and full roster data for Meet 512 (VCAC Championship).

### 3. Backtesting Candidates
**Target Meet:** Meet 512 (VCAC Regular Season Championship, Jan 2026)

*   **Identified via:** `scripts/analyze_meet_512.py`
*   **Data Availability:**
    *   Roster: Complete (156 Seton athletes)
    *   Results: Complete (Individual times and DQs)
    *   Opponents: Data present (ids 30, 199, 158, etc.)

## Recommendations

1.  **Immediate Action (Phase 1):** Continue using CSV exports (`data/real_exports/csv`) for Backtesting. They are clean, accessible, and verified to contain necessary data for `AquaOptimizer`.
2.  **Future Integration (Phase 2):** If granular data (splits, relay takeoff times, non-exportable metadata) is required, develop a `MDBConnector` module using `mdb-tools` (or `pyodbc` on Windows) to query `SSTdata.mdb` directly.
3.  **Validation:** Use `SST-Entries-*.ZIP` files to verify that our "Generated Rosters" match the actual entries submitted for those meets.

## Next Steps
*   Complete the "Meet 512" baseline backtest using CSVs.
*   Benchmark `AquaOptimizer` speed.
*   Implement optimization improvements (Move Ordering).
