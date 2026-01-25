# Football Data Downloader Services

A comprehensive system for downloading, processing, and storing football data from multiple sources.

## 📁 Project Structure

```
downloader_services/
├── transferroom_service/     # TransferRoom API integration
│   ├── ingest_pipeline.py   # Main ingestion pipeline
│   └── env.template         # Environment configuration
│
├── database/                 # Database schemas and migrations
│   └── db_schema.sql        # PostgreSQL schema
│
├── data/                     # Raw data files
│   └── competitions.json    # Competition data
│
├── docs/                     # Documentation
│   ├── DATABASE_README.md
│   ├── PIPELINE_ARCHITECTURE.md
│   └── ...
│
├── exports/                  # Data exports and analysis
│   ├── competition_ratings.xlsx
│   └── process_competitions.py
│
├── tmroom_legacy/           # Legacy scripts (for reference)
│   └── ...
│
├── pyproject.toml           # Python dependencies
├── uv.lock                  # Dependency lock file
└── README.md                # This file
```

## 🚀 Quick Start

### 1. Setup Database

```bash
# Install PostgreSQL (if not installed)
brew install postgresql@14
brew services start postgresql@14

# Create database
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
createdb transferroom

# Apply schema
psql -d transferroom -f database/db_schema.sql
```

### 2. Configure Environment

```bash
# Copy template and configure
cp transferroom_service/env.template .env

# Edit .env with your credentials
nano .env
```

### 3. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install psycopg[binary] requests urllib3 pandas openpyxl
```

### 4. Run Data Ingestion

```bash
# Set environment variables
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
export DATABASE_URL="postgresql://localhost/transferroom"

# Test with 100 players
uv run transferroom_service/ingest_pipeline.py --test

# Full ingestion (~190K players, 20-30 minutes)
uv run transferroom_service/ingest_pipeline.py --players-only
```

## 📊 Current Data Sources

### 1. TransferRoom API (`transferroom_service/`)
- **Players**: ~190,000 professional players
- **Competitions**: 357 competitions worldwide
- **Countries**: 167 countries
- **Features**: Ratings, transfer values, work permits, history

**Status**: ✅ Operational

### 2. Future Data Sources
Additional downloader services can be added following the same pattern:
```
├── datasource2_service/
│   ├── ingest_pipeline.py
│   └── env.template
```

## 🗄️ Database Schema

### Main Tables
- `transferroom_countries` - Country reference (167 rows)
- `transferroom_competitions` - Competition details (357 rows)
- `transferroom_players` - Player profiles (190K+ rows)
- `transferroom_teams` - Team information
- `transferroom_players_history` - Change tracking
- `data_sync_runs` - Audit trail

### Key Features
- ✅ 60+ player attributes
- ✅ JSONB fields for historical data
- ✅ 40+ optimized indexes
- ✅ Full audit trail
- ✅ Idempotent operations

## 📖 Documentation

Comprehensive documentation available in `docs/`:
- **DATABASE_README.md** - Database setup and queries
- **PIPELINE_ARCHITECTURE.md** - System architecture
- **PLAYER_INGESTION_GUIDE.md** - Usage instructions
- **FINAL_SUCCESS_REPORT.md** - Latest status

## 🔧 Common Commands

### Data Ingestion
```bash
# Competitions only
uv run transferroom_service/ingest_pipeline.py --competitions-only

# Players only (with limit)
uv run transferroom_service/ingest_pipeline.py --players-only --max-players 10000

# Both competitions and players
uv run transferroom_service/ingest_pipeline.py
```

### Database Queries
```bash
# Connect to database
psql -d transferroom

# Check record counts
psql -d transferroom -c "
SELECT 'Players' as table, COUNT(*) FROM transferroom_players
UNION ALL
SELECT 'Competitions', COUNT(*) FROM transferroom_competitions;
"

# View top players
psql -d transferroom -c "
SELECT name, first_position, rating, current_team 
FROM transferroom_players 
ORDER BY rating DESC LIMIT 10;
"
```

### Maintenance
```bash
# Backup database
pg_dump transferroom > backups/backup_$(date +%Y%m%d).sql

# Check sync history
psql -d transferroom -c "
SELECT * FROM data_sync_runs ORDER BY started_at DESC LIMIT 5;
"
```

## 🎯 Use Cases

### Player Scouting
```sql
-- Find high-potential young players
SELECT name, rating, potential, xtv, current_team
FROM transferroom_players
WHERE potential > rating + 5 AND rating > 70
ORDER BY (potential - rating) DESC;
```

### Market Analysis
```sql
-- Rising stars (value increasing)
SELECT name, rating, xtv, xtv_change_12m_perc
FROM transferroom_players
WHERE xtv_change_12m_perc > 50
ORDER BY xtv_change_12m_perc DESC;
```

### Work Permit Analysis
```sql
-- UK work permit eligible players
SELECT name, nationality1, gbe_score, rating
FROM transferroom_players
WHERE gbe_result = 'Pass' AND rating > 75
ORDER BY rating DESC;
```

## 📈 Performance

- **Ingestion Speed**: ~1,000 players/minute
- **Database Size**: ~1 GB for 190K players
- **Query Performance**: < 10ms for most queries
- **Success Rate**: 100% (after initial setup)

## 🔄 Scheduled Updates

Set up daily updates with cron:
```bash
# Edit crontab
crontab -e

# Add daily update at 2 AM
0 2 * * * cd /Users/botondvarga/downloader_services && uv run transferroom_service/ingest_pipeline.py --players-only
```

## 🛠️ Development

### Adding New Data Source

1. Create new service directory:
```bash
mkdir new_datasource_service
```

2. Create ingestion pipeline following the TransferRoom pattern
3. Add configuration to env.template
4. Update database schema if needed
5. Document in README

### Running Tests
```bash
# Test database connection
python3 -c "import psycopg; psycopg.connect('postgresql://localhost/transferroom')"

# Test API authentication
python3 -c "from transferroom_service.ingest_pipeline import TransferRoomAPIClient; 
client = TransferRoomAPIClient('email', 'password'); 
print(client.authenticate())"
```

## 📝 License

Proprietary - Internal Use Only

## 🤝 Support

For issues or questions, refer to:
- Documentation in `docs/`
- TransferRoom API: https://www.transferroom.com/api-docs
- PostgreSQL docs: https://www.postgresql.org/docs/

---

**Status**: ✅ Production Ready | **Last Updated**: January 2026
