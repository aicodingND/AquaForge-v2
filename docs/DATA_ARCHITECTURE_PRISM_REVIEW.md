# AquaForge Data Architecture - PRISM Review

## Document Purpose
This document captures the comprehensive analysis and recommendations for optimizing, refactoring, and restructuring AquaForge's data layer to support production-level enterprise deployment.

**Review Date:** 2026-01-19
**Methodology:** PRISM (Perspective-based Recursive Iterative Self-improvement Method) + Ralph (Iterative Development)

---

## 1. Data Inventory & Assessment

### 1.1 Project Data Sources (`/data/`)

| Directory                   | Contents                  | Size   | Format  | Priority |
| --------------------------- | ------------------------- | ------ | ------- | -------- |
| `scraped/`                  | SwimCloud competitor data | ~115KB | JSON    | HIGH     |
| `swimcloud/`                | Organized scrape outputs  | TBD    | JSON    | HIGH     |
| `championship_data/`        | VCAC 2026 psych sheets    | ~420KB | JSON    | CRITICAL |
| `real_exports/csv/`         | HyTek historical exports  | ~8.2MB | CSV     | CRITICAL |
| `real_exports/entry_files/` | Meet entry archives       | ~175KB | ZIP/HY3 | HIGH     |
| `sample/`                   | Demo data for testing     | ~50KB  | CSV     | MEDIUM   |

### 1.2 External Drive Data (`/Volumes/Miguel/swimdatadump/`)

| Directory           | Contents                | Notes                 |
| ------------------- | ----------------------- | --------------------- |
| `SSTdata.mdb`       | Master HyTek database   | 36MB - PRIMARY SOURCE |
| `swmeets4/7/8/`     | Legacy meet databases   | Historical data       |
| `Database Backups/` | Point-in-time snapshots | Disaster recovery     |
| `Entry ZIPs`        | 20+ meet entry files    | 2025-2026 season      |
| `TM5Data/`          | Team Manager exports    | Legacy format         |

### 1.3 SwimCloud Scraped Data (Competitor Intelligence)

```
data/scraped/
├── BI_swimcloud.json    (1.6KB)  - Benedictine
├── DJO_swimcloud.json   (12KB)   - Don Bosco
├── FCS_swimcloud.json   (16KB)   - Fresta Valley
├── ICS_swimcloud.json   (32KB)   - Immanuel Christian ⭐ Key competitor
├── OAK_swimcloud.json   (25KB)   - Oakwood
├── PVI_swimcloud.json   (180B)   - Paul VI (needs refresh)
└── TCS_swimcloud.json   (25KB)   - Trinity Christian
```

---

## 2. Multi-Perspective Critique (PRISM Phase 2)

### 🏗️ Data Architect Perspective

**Issues Identified:**
1. **Schema Fragmentation**: No unified schema across data sources
2. **Entity Resolution Gap**: Same swimmer may exist in HyTek, SwimCloud, and entries with no linking ID
3. **Temporal Inconsistency**: Historical data uses different date/time formats
4. **Storage Inefficiency**: CSV files are not optimized for analytical queries

**Recommendations:**
- Implement a canonical data model with Pydantic schemas
- Create a unified `swimmer_id` using hash of (name, team, birth_year)
- Convert CSV exports to Parquet for 10x query performance
- Use DuckDB as the analytical layer

### ⚡ Performance Engineer Perspective

**Critical Path Analysis:**
1. `results.csv` at 77K rows is manageable but will grow
2. Real-time optimization requires sub-second data access
3. Current file-based approach has I/O overhead

**Recommendations:**
- Implement lazy loading with DuckDB memory mapping
- Cache frequently accessed data (active roster, recent results)
- Pre-compute swimmer aggregates (best times, event counts)

### 🔬 Data Scientist Perspective

**Analytics Opportunities:**
1. **Historical Trends**: 20+ years of swim data enables powerful modeling
2. **Performance Prediction**: ML models for time drops, taper optimization
3. **Competitor Analysis**: SwimCloud data enables strategic insights
4. **Championship Projections**: Monte Carlo simulations need clean entry data

**Data Quality Concerns:**
- Missing birth dates in `athletes.csv` (many entries show age=0)
- Inconsistent grade/class fields
- Some results have SCORE values that need conversion to times

### 🛡️ Security & Compliance Perspective

**Considerations:**
1. **FERPA**: Student athlete data requires protection
2. **Data Retention**: Define policies for historical data
3. **Access Control**: Production deployment needs role-based access

**Recommendations:**
- PII fields (name, DOB) should be encrypted at rest
- Implement audit logging for data access
- Create data anonymization for demo/testing

---

## 3. Proposed Architecture

### 3.1 Unified Data Directory Structure

```
data/
├── raw/                    # Original source data (immutable)
│   ├── hytek/              # MDB exports, HY3 files
│   ├── swimcloud/          # Scraped JSON
│   └── external/           # Copied from /Volumes/Miguel
│
├── processed/              # Cleaned, normalized data
│   ├── swimmers.parquet    # Unified swimmer records
│   ├── results.parquet     # Historical results
│   ├── meets.parquet       # Meet metadata
│   ├── entries.parquet     # Psych sheet entries
│   └── teams.parquet       # Team registry
│
├── warehouse/              # Analytical layer
│   ├── aquaforge.duckdb    # Embedded analytics DB
│   └── indexes/            # Precomputed aggregates
│
└── cache/                  # Runtime caches
    ├── active_roster.json  # Current season swimmers
    └── recent_results.json # Last 30 days
```

### 3.2 Canonical Data Models

```python
# data_contracts.py - Already exists, extend with:

class UnifiedSwimmer(BaseModel):
    """Canonical swimmer record across all sources."""
    swimmer_id: str           # UUID or deterministic hash
    name: str
    first_name: str
    last_name: str
    team_code: str
    team_name: str
    grade: Optional[str]
    birth_date: Optional[date]
    gender: Literal["M", "F"]
    
    # Source tracking
    hytek_id: Optional[int]
    swimcloud_id: Optional[int]
    
    # Computed fields
    best_times: Dict[str, float]  # event -> time_seconds
    event_count: int

class UnifiedResult(BaseModel):
    """Canonical race result record."""
    result_id: str
    swimmer_id: str
    meet_id: str
    event: str
    distance: int
    stroke: str
    time_seconds: float
    points: float
    place: int
    course: Literal["SCY", "SCM", "LCM"]
    date: date

class UnifiedMeet(BaseModel):
    """Canonical meet record."""
    meet_id: str
    name: str
    date: date
    location: Optional[str]
    meet_type: Literal["dual", "invitational", "championship"]
    course: str
```

### 3.3 Ingestion Pipeline

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Raw Sources   │───▶│   ETL Pipeline  │───▶│  Data Warehouse │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       │                       │                       │
       ▼                       ▼                       ▼
  ┌─────────┐           ┌─────────────┐         ┌───────────┐
  │ HyTek   │           │ Python ETL  │         │ DuckDB    │
  │ SwimCld │           │ + Pandas    │         │ + Parquet │
  │ HY3     │           │ + Pydantic  │         │           │
  └─────────┘           └─────────────┘         └───────────┘
```

---

## 4. Implementation Plan

### Phase 1: Consolidation (Week 1)
- [ ] Copy external drive data to `data/raw/external/`
- [ ] Create `data/raw/hytek/` and organize MDB/CSV files
- [ ] Implement basic ETL script for CSV → Parquet conversion
- [ ] Set up DuckDB with initial schema

### Phase 2: Entity Resolution (Week 2)
- [ ] Implement swimmer deduplication algorithm
- [ ] Create cross-reference tables for ID mapping
- [ ] Validate with known swimmers across sources
- [ ] Generate unified `swimmers.parquet`

### Phase 3: Full Pipeline (Week 3)
- [ ] Build complete ETL for results, meets, entries
- [ ] Implement SwimCloud → unified schema converter
- [ ] Create HY3 parser for entry files
- [ ] Validate data quality with automated tests

### Phase 4: Integration (Week 4)
- [ ] Create DataService with DuckDB backend
- [ ] Expose API endpoints for unified data access
- [ ] Update frontend to use new data layer
- [ ] Performance testing and optimization

---

## 5. Pros and Cons Analysis

### Proposed Architecture

| Pros                              | Cons                              |
| --------------------------------- | --------------------------------- |
| ✅ Single source of truth          | ⚠️ Initial migration effort        |
| ✅ 10x faster queries with Parquet | ⚠️ Learning curve for DuckDB       |
| ✅ Clean entity resolution         | ⚠️ Ongoing ETL maintenance         |
| ✅ Production-ready scalability    | ⚠️ Data synchronization complexity |
| ✅ ML-ready feature store          |                                   |

### Alternative: Keep Current Structure

| Pros                    | Cons                     |
| ----------------------- | ------------------------ |
| ✅ No migration required | ❌ Scattered data sources |
| ✅ Familiar tools        | ❌ Slow file I/O          |
|                         | ❌ No entity linking      |
|                         | ❌ Not production-ready   |

---

## 6. Priority Actions

### Immediate (Today)
1. ✅ Create this architecture document
2. Create `data/raw/external/` and begin copying from external drive
3. Write initial `etl/` module with CSV → Parquet conversion

### Short-Term (This Week)
1. Implement `UnifiedSwimmer` entity resolution
2. Create data quality validation tests
3. Update `docs/COST_EFFORT_LOG.md` with progress

### Medium-Term (This Month)
1. Full DuckDB warehouse implementation
2. API integration with new data layer
3. Frontend data source migration

---

## 7. Appendix: Data Format Specifications

### HyTek SCORE Field Conversion
The `SCORE` field in `results.csv` represents time in centiseconds:
- `2598` = 25.98 seconds
- `14160` = 2:21.60 (141.60 seconds)

### SwimCloud JSON Schema
```json
{
  "team_code": "ICS",
  "team_name": "Immanuel Christian High School",
  "team_id": 10026495,
  "roster": [...],
  "times": [
    {
      "swimmer_name": "Caleb Fiala",
      "team": "ICS",
      "event": "Boys 50 Free",
      "seed_time": 22.7,
      "gender": "M"
    }
  ]
}
```

---

*Document generated as part of PRISM workflow. Review and iterate as implementation progresses.*
