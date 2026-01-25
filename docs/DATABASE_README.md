# TransferRoom Database Setup

This directory contains the PostgreSQL database schema and data ingestion pipeline for TransferRoom data.

## Prerequisites

- PostgreSQL 14+ installed
- Python 3.12+
- Access to TransferRoom API

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv pip install psycopg[binary] requests

# Or using pip
pip install psycopg[binary] requests
```

### 2. Create Database

```bash
# Create database
createdb transferroom

# Or using psql
psql -U postgres -c "CREATE DATABASE transferroom;"
```

### 3. Initialize Schema

```bash
# Apply database schema
psql -U postgres -d transferroom -f db_schema.sql

# Or using psql interactively
psql -U postgres transferroom < db_schema.sql
```

### 4. Configure Environment Variables

```bash
# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://postgres:password@localhost:5432/transferroom
TRANSFERROOM_EMAIL=your_email@example.com
TRANSFERROOM_PASSWORD=your_password
EOF
```

### 5. Run Initial Data Load

```bash
# Ingest competitions from JSON file
python ingest_pipeline.py
```

## Database Schema

### Core Tables

#### 1. `transferroom_countries`
- Normalized country reference table
- Links to competitions via foreign key

#### 2. `transferroom_competitions`
- Competition details with ratings and division levels
- Includes JSONB field for teams data
- Tracks average team and starter ratings

#### 3. `transferroom_teams`
- Teams extracted from competition data
- Links to competitions

#### 4. `transferroom_players`
- Comprehensive player profiles
- Positions, ratings, contracts, physical attributes
- Full API response stored in JSONB for flexibility

#### 5. `data_sync_runs`
- Audit trail for all data synchronization operations
- Tracks success/failure, timing, and statistics

#### 6. `transferroom_players_history`
- Historical tracking of player changes
- Enables trend analysis and change detection

### Views

- **`vw_active_competitions`**: All active competitions with details
- **`vw_available_players`**: Players available for transfer/loan
- **`vw_competition_rankings`**: Competition rankings by rating

## Data Ingestion Pipeline

### Architecture

```
TransferRoom API → API Client → Transformation → PostgreSQL
                                      ↓
                               Validation & Error Handling
```

### Features

- ✅ **Idempotent**: Safe to re-run multiple times
- ✅ **Upsert Logic**: Updates existing records, inserts new ones
- ✅ **Change Tracking**: Records all changes in history tables
- ✅ **Error Handling**: Graceful failure with detailed logging
- ✅ **Retry Logic**: Automatic retry on API failures
- ✅ **Batch Processing**: Efficient bulk operations
- ✅ **Audit Trail**: Complete sync run tracking

### Pipeline Usage

```python
from ingest_pipeline import TransferRoomDataPipeline

# Initialize pipeline
pipeline = TransferRoomDataPipeline(
    db_connection_string="postgresql://localhost/transferroom",
    api_email="your_email@example.com",
    api_password="your_password"
)

# Ingest competitions from file
pipeline.ingest_competitions('competitions.json')

# Ingest players from API
pipeline.ingest_players_from_api(max_records=10000)
```

## Common Queries

### Find top-rated players by position

```sql
SELECT 
    full_name,
    first_position_full,
    overall_rating,
    current_club,
    competition_name
FROM transferroom_players
WHERE first_position = 'F'
    AND overall_rating IS NOT NULL
ORDER BY overall_rating DESC
LIMIT 20;
```

### Competition strength by country

```sql
SELECT 
    country_name,
    division_level,
    competition_name,
    avg_team_rating
FROM transferroom_competitions
WHERE avg_team_rating IS NOT NULL
ORDER BY avg_team_rating DESC;
```

### Track recent sync runs

```sql
SELECT 
    sync_run_id,
    sync_type,
    status,
    records_fetched,
    records_inserted,
    records_updated,
    records_failed,
    duration_seconds,
    started_at
FROM data_sync_runs
ORDER BY started_at DESC
LIMIT 10;
```

### Find players in top 3 divisions

```sql
SELECT 
    p.full_name,
    p.first_position_full,
    p.age,
    p.nationality,
    c.competition_name,
    c.country_name,
    c.division_level,
    p.overall_rating
FROM transferroom_players p
JOIN transferroom_competitions c ON p.competition_id = c.competition_id
WHERE c.division_level <= 3
    AND p.overall_rating IS NOT NULL
ORDER BY c.division_level, p.overall_rating DESC;
```

## Maintenance

### Daily Tasks

```sql
-- Check latest sync status
SELECT * FROM data_sync_runs ORDER BY started_at DESC LIMIT 5;

-- Check for failed syncs
SELECT * FROM data_sync_runs WHERE status = 'failed' ORDER BY started_at DESC;
```

### Weekly Tasks

```sql
-- Analyze tables for query optimization
ANALYZE transferroom_competitions;
ANALYZE transferroom_players;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monthly Tasks

```sql
-- Vacuum and analyze
VACUUM ANALYZE transferroom_competitions;
VACUUM ANALYZE transferroom_players;

-- Archive old history (older than 6 months)
DELETE FROM transferroom_players_history
WHERE changed_at < CURRENT_TIMESTAMP - INTERVAL '6 months';
```

## Performance Optimization

### Indexes

The schema includes comprehensive indexes for:
- Primary key lookups (B-tree)
- Foreign key relationships
- JSONB queries (GIN indexes)
- Full-text search (GIN indexes)
- Common query patterns (composite indexes)

### Connection Pooling

For production, use connection pooling:

```python
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    "postgresql://localhost/transferroom",
    min_size=2,
    max_size=10
)
```

## Troubleshooting

### Connection Issues

```bash
# Test database connection
psql -U postgres -d transferroom -c "SELECT version();"

# Check if database exists
psql -U postgres -l | grep transferroom
```

### Schema Issues

```bash
# Re-create schema (WARNING: drops all data)
psql -U postgres -d transferroom -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -U postgres -d transferroom -f db_schema.sql
```

### API Issues

```python
# Test API authentication
from ingest_pipeline import TransferRoomAPIClient

client = TransferRoomAPIClient("email", "password")
token = client.authenticate()
print(f"Token: {token}")
```

## Security Best Practices

1. **Never commit credentials** - Use environment variables
2. **Use SSL for database connections** in production
3. **Restrict database user permissions** - Create app-specific user
4. **Enable row-level security** if multi-tenant
5. **Regular backups** - Automated daily backups with PITR

## Deployment

### Production Checklist

- [ ] Database running on dedicated server
- [ ] SSL/TLS enabled for database connections
- [ ] Connection pooling configured (PgBouncer)
- [ ] Automated backups scheduled
- [ ] Monitoring and alerting setup
- [ ] Environment variables configured
- [ ] API rate limiting handled
- [ ] Cron jobs for scheduled syncs
- [ ] Log rotation configured

## Support & Documentation

- [TransferRoom API Documentation](https://www.transferroom.com/api-docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/)

## License

Proprietary - Internal Use Only
