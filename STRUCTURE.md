# 📁 Repository Structure

## Overview
Clean, organized structure for multiple football data downloader services.

## Directory Structure

```
downloader_services/
│
├── transferroom_service/          # TransferRoom API integration
│   ├── ingest_pipeline.py        # Main ingestion pipeline (800 lines)
│   └── env.template               # Configuration template
│
├── database/                      # Database schemas
│   └── db_schema.sql             # PostgreSQL schema (6 tables, 40+ indexes)
│
├── data/                          # Source data files
│   └── competitions.json         # Competition reference data
│
├── docs/                          # Complete documentation (2,500+ lines)
│   ├── DATABASE_README.md        # Setup and usage guide
│   ├── PIPELINE_ARCHITECTURE.md  # System architecture
│   ├── FINAL_SUCCESS_REPORT.md   # Latest status report
│   └── ... (8 more docs)
│
├── exports/                       # Data exports and analysis
│   ├── competition_ratings.xlsx  # Competition analysis
│   └── process_competitions.py   # Export script
│
├── tmroom_legacy/                # Legacy scripts (reference only)
│   ├── tmroom_api_testing.py    # Old testing script
│   ├── test_comps.py            # Old test
│   └── main.py                   # Old main
│
├── pyproject.toml                # Python project config (uv)
├── requirements.txt              # Pip requirements
├── uv.lock                       # Dependency lock
├── .gitignore                    # Git ignore rules
└── README.md                     # Main documentation
```

## Service Organization

### Active Services
1. **transferroom_service/** - TransferRoom API downloader
   - Status: ✅ Operational
   - Data: ~190K players, 357 competitions
   - Features: Batch processing, progress tracking, error handling

### Future Services
2. **[datasource2]_service/** - Template for next data source
   - Follow same pattern as transferroom_service
   - Each service is independent and self-contained

## File Purposes

### Core Application Files
- `transferroom_service/ingest_pipeline.py` - Main data ingestion script
- `transferroom_service/env.template` - Environment configuration template
- `database/db_schema.sql` - Complete PostgreSQL database schema

### Configuration Files
- `pyproject.toml` - Project dependencies and metadata (uv package manager)
- `requirements.txt` - Alternative pip requirements
- `.gitignore` - Files to exclude from git
- `README.md` - Main project documentation

### Data Files
- `data/competitions.json` - Source competition data (357 competitions)
- `exports/` - Generated analysis files (not in git)

### Documentation
- `docs/DATABASE_README.md` - Database setup and queries
- `docs/PIPELINE_ARCHITECTURE.md` - System design and architecture
- `docs/FINAL_SUCCESS_REPORT.md` - Latest test results and status
- `docs/PLAYER_INGESTION_GUIDE.md` - Usage instructions
- Plus 7 more detailed guides

### Legacy (Reference Only)
- `tmroom_legacy/` - Old scripts kept for reference
- Not used in production

## Key Features

### Clean Separation
✅ Each data source has its own service directory  
✅ Shared database schema in central location  
✅ Documentation separate from code  
✅ Legacy code isolated  

### Scalability
✅ Easy to add new data sources  
✅ Independent service deployments  
✅ Shared database infrastructure  
✅ Centralized documentation  

### Maintainability
✅ Clear file organization  
✅ Self-documenting structure  
✅ Consistent patterns  
✅ Version controlled  

## Quick Navigation

**Need to...**
- Start ingesting data? → `transferroom_service/ingest_pipeline.py`
- Setup database? → `database/db_schema.sql`
- Configure environment? → `transferroom_service/env.template`
- Read documentation? → `docs/`
- Add new data source? → Create new `[source]_service/` directory
- Analyze data? → `exports/`
- Reference old code? → `tmroom_legacy/`

## Commands by Directory

### From Root
```bash
# Setup
createdb transferroom
psql -d transferroom -f database/db_schema.sql

# Run ingestion
uv run transferroom_service/ingest_pipeline.py --test
```

### TransferRoom Service
```bash
cd transferroom_service
uv run ingest_pipeline.py --players-only --max-players 10000
```

### Database
```bash
cd database
psql -d transferroom -f db_schema.sql
```

### Exports
```bash
cd exports
python process_competitions.py
```

## Adding New Data Source

1. **Create service directory:**
```bash
mkdir new_datasource_service
cd new_datasource_service
```

2. **Create files:**
```
new_datasource_service/
├── ingest_pipeline.py    # Copy and adapt from transferroom_service
├── env.template          # Add new source credentials
└── README.md            # Document the new source
```

3. **Update main README** with new service info

4. **Update database schema** if needed (add tables in `database/`)

## Size Information

```
Database Schema:    ~20 KB (400 lines SQL)
Python Pipeline:    ~40 KB (800 lines)
Documentation:      ~150 KB (2,500+ lines)
Data Files:        ~200 KB (competitions.json)
Total (no data):   ~500 KB
With 190K players: ~1 GB
```

## Clean Architecture Benefits

✅ **Easy to understand** - Clear directory names
✅ **Easy to extend** - Add new services without conflicts  
✅ **Easy to maintain** - Find files quickly  
✅ **Easy to deploy** - Independent services  
✅ **Easy to document** - Centralized docs  
✅ **Easy to test** - Isolated components  

---

**Structure Status**: ✅ Clean and Production Ready
