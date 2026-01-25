# TransferRoom Data Pipeline Architecture

## Overview
This document outlines the architecture for ingesting data from the TransferRoom API into a PostgreSQL database following industry best practices.

## Architecture Components

### 1. Data Sources
- **TransferRoom API**: Primary data source
  - Competitions endpoint
  - Players endpoint
  - Teams data (embedded in competitions)
- **API Documentation**: https://www.transferroom.com/api-docs

### 2. Database Schema Design

#### Core Tables
1. **transferroom_countries** - Normalized country reference table
2. **transferroom_competitions** - Competition details with ratings
3. **transferroom_teams** - Teams extracted from competition data
4. **transferroom_players** - Player profiles with detailed attributes
5. **data_sync_runs** - Audit trail for sync operations
6. **transferroom_players_history** - Track player changes over time

#### Design Principles Applied
- ✅ Surrogate keys (BIGSERIAL) for scalability
- ✅ Natural unique constraints on API IDs
- ✅ Timestamps (created_at, updated_at, last_synced_at)
- ✅ JSONB for flexible nested data storage
- ✅ Proper indexing strategy for query performance
- ✅ Foreign key constraints for referential integrity
- ✅ Check constraints for data validation
- ✅ Audit tables for change tracking
- ✅ Materialized views for complex queries

## Data Ingestion Pipeline

### Pipeline Architecture

```
┌─────────────────┐
│  TransferRoom   │
│      API        │
└────────┬────────┘
         │
         │ HTTP/JSON
         │
         ▼
┌─────────────────────────────────────────────────┐
│           Data Ingestion Layer                  │
│  ┌──────────────────────────────────────────┐  │
│  │  1. API Client (with retry & rate limit) │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  2. Data Validation & Transformation     │  │
│  │     - Schema validation                  │  │
│  │     - Data cleaning                      │  │
│  │     - Type conversion                    │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  3. Upsert Logic (Idempotent)           │  │
│  │     - Detect changes                     │  │
│  │     - Update or insert                   │  │
│  │     - Track history                      │  │
│  └──────────────┬───────────────────────────┘  │
└─────────────────┼───────────────────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │   PostgreSQL    │
         │    Database     │
         └─────────────────┘
```

### Pipeline Stages

#### Stage 1: Data Extraction
```python
1. Initialize sync run (record in data_sync_runs)
2. Authenticate with TransferRoom API
3. Fetch data with pagination:
   - Competitions (single request)
   - Players (paginated, 10k per request)
4. Handle rate limiting and retries
5. Validate API responses
```

#### Stage 2: Data Transformation
```python
1. Parse JSON responses
2. Normalize nested structures:
   - Extract countries from competitions
   - Extract teams from competitions
3. Apply business rules:
   - Calculate derived fields
   - Map position codes to full names
   - Convert date formats
4. Validate data quality:
   - Check required fields
   - Validate data ranges
   - Handle missing values
```

#### Stage 3: Data Loading (Upsert Pattern)
```python
1. Use PostgreSQL UPSERT (INSERT ... ON CONFLICT)
2. For each entity:
   a. Check if exists (by transferroom_*_id)
   b. If exists:
      - Compare with existing data
      - If changed: Update + record in history table
      - Update last_synced_at timestamp
   c. If not exists:
      - Insert new record
3. Handle foreign key relationships:
   - Countries → Competitions → Players
4. Update sync run statistics
```

### Idempotency Strategy

The pipeline is designed to be **fully idempotent**:
- Multiple runs with same data = same result
- Uses UPSERT pattern (ON CONFLICT DO UPDATE)
- Tracks changes in history tables
- Safe to re-run on failures

## Best Practices Implementation

### 1. Data Quality
- ✅ Schema validation before insert
- ✅ Check constraints on critical fields
- ✅ NULL handling with explicit defaults
- ✅ Data type enforcement
- ✅ Referential integrity via foreign keys

### 2. Performance Optimization
- ✅ Batch processing (bulk inserts)
- ✅ Strategic indexing:
  - B-tree indexes for exact matches
  - GIN indexes for JSONB queries
  - Composite indexes for common joins
- ✅ Connection pooling
- ✅ Async processing where possible
- ✅ Materialized views for expensive queries

### 3. Monitoring & Observability
- ✅ Sync run tracking table
- ✅ Success/failure rates
- ✅ Duration metrics
- ✅ Record counts (inserted/updated/failed)
- ✅ Error logging with stack traces
- ✅ Alert on sync failures

### 4. Data Governance
- ✅ Audit trail (history tables)
- ✅ Soft deletes (is_active flag)
- ✅ Change tracking with timestamps
- ✅ Raw data preservation (JSONB fields)
- ✅ Data lineage (sync_run_id references)

### 5. Scalability Considerations
- ✅ BIGSERIAL for high-volume tables
- ✅ Partitioning ready (can partition by date)
- ✅ Index-only scans where possible
- ✅ Efficient pagination handling
- ✅ Horizontal scaling ready

### 6. Error Handling
- ✅ Graceful API failures
- ✅ Retry logic with exponential backoff
- ✅ Transaction rollback on errors
- ✅ Partial success handling
- ✅ Dead letter queue for failed records

## Data Sync Strategy

### Full Sync vs Incremental Sync

#### Full Sync (Initial Load & Weekly)
```
- Fetch all competitions
- Fetch all players
- Upsert everything
- Good for: Initial load, data corrections
- Frequency: Weekly (e.g., Sunday night)
```

#### Incremental Sync (Daily)
```
- Fetch only updated players (if API supports)
- Update changed records only
- Good for: Daily updates
- Frequency: Daily (e.g., 2 AM)
```

### Recommended Schedule
```
- Initial Load: Full sync
- Daily: Incremental sync at 2 AM
- Weekly: Full sync on Sunday 11 PM
- On-Demand: Manual trigger via API/CLI
```

## Example Ingestion Workflow

### 1. Competitions Ingestion
```sql
-- Upsert countries
INSERT INTO transferroom_countries (transferroom_country_id, country_name)
VALUES ($1, $2)
ON CONFLICT (transferroom_country_id) DO UPDATE
SET country_name = EXCLUDED.country_name,
    updated_at = CURRENT_TIMESTAMP;

-- Upsert competitions
INSERT INTO transferroom_competitions (
    transferroom_competition_id,
    competition_name,
    country_id,
    transferroom_country_id,
    country_name,
    division_level,
    teams_data,
    avg_team_rating,
    avg_starter_rating,
    last_synced_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_TIMESTAMP)
ON CONFLICT (transferroom_competition_id) DO UPDATE
SET competition_name = EXCLUDED.competition_name,
    country_id = EXCLUDED.country_id,
    country_name = EXCLUDED.country_name,
    division_level = EXCLUDED.division_level,
    teams_data = EXCLUDED.teams_data,
    avg_team_rating = EXCLUDED.avg_team_rating,
    avg_starter_rating = EXCLUDED.avg_starter_rating,
    updated_at = CURRENT_TIMESTAMP,
    last_synced_at = CURRENT_TIMESTAMP;
```

### 2. Players Ingestion
```sql
-- Upsert players with change detection
INSERT INTO transferroom_players (
    transferroom_player_id,
    first_name,
    last_name,
    full_name,
    nationality,
    age,
    first_position,
    second_position,
    current_club,
    competition_id,
    overall_rating,
    contract_expires,
    raw_data,
    last_synced_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, CURRENT_TIMESTAMP)
ON CONFLICT (transferroom_player_id) DO UPDATE
SET first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    full_name = EXCLUDED.full_name,
    nationality = EXCLUDED.nationality,
    age = EXCLUDED.age,
    first_position = EXCLUDED.first_position,
    second_position = EXCLUDED.second_position,
    current_club = EXCLUDED.current_club,
    competition_id = EXCLUDED.competition_id,
    overall_rating = EXCLUDED.overall_rating,
    contract_expires = EXCLUDED.contract_expires,
    raw_data = EXCLUDED.raw_data,
    updated_at = CURRENT_TIMESTAMP,
    last_synced_at = CURRENT_TIMESTAMP
RETURNING player_id, transferroom_player_id;
```

## Deployment Considerations

### Infrastructure
- **Database**: PostgreSQL 14+ (for enhanced JSONB features)
- **Connection Pooling**: PgBouncer or built-in application pooling
- **Backup**: Daily automated backups with point-in-time recovery
- **Monitoring**: PostgreSQL metrics, slow query log, connection stats

### Application Stack
- **Language**: Python 3.12+
- **DB Library**: psycopg3 (async support) or SQLAlchemy
- **HTTP Client**: httpx or aiohttp (async)
- **Scheduler**: APScheduler or Celery for scheduled jobs
- **Config Management**: Environment variables or config files

### Security
- ✅ API credentials stored in environment variables
- ✅ Database credentials in secure vault
- ✅ SSL/TLS for database connections
- ✅ Row-level security (if multi-tenant)
- ✅ Audit logging for sensitive operations

## Query Examples

### Find top-rated players by position in top competitions
```sql
SELECT 
    p.full_name,
    p.first_position_full,
    p.overall_rating,
    p.current_club,
    c.competition_name,
    c.country_name,
    c.division_level
FROM transferroom_players p
JOIN transferroom_competitions c ON p.competition_id = c.competition_id
WHERE p.first_position = 'F'
    AND c.division_level <= 2
    AND p.overall_rating IS NOT NULL
ORDER BY p.overall_rating DESC
LIMIT 50;
```

### Track player club changes
```sql
SELECT 
    p.full_name,
    h.change_type,
    h.old_value->>'current_club' as old_club,
    h.new_value->>'current_club' as new_club,
    h.changed_at
FROM transferroom_players_history h
JOIN transferroom_players p ON h.player_id = p.player_id
WHERE h.change_type = 'club_change'
ORDER BY h.changed_at DESC;
```

### Competition strength by country
```sql
SELECT 
    country_name,
    division_level,
    COUNT(*) as competition_count,
    AVG(avg_team_rating) as avg_rating,
    MIN(avg_team_rating) as min_rating,
    MAX(avg_team_rating) as max_rating
FROM transferroom_competitions
WHERE avg_team_rating IS NOT NULL
GROUP BY country_name, division_level
ORDER BY avg_rating DESC;
```

## Maintenance Tasks

### Daily
- Monitor sync run success/failure rates
- Check for API errors
- Review slow queries

### Weekly
- Analyze index usage
- Review table sizes and growth
- Check for data quality issues

### Monthly
- VACUUM ANALYZE on large tables
- Review and archive old history records
- Update statistics for query planner

## Future Enhancements

1. **Real-time Updates**: WebSocket or webhook support
2. **ML Features**: Player performance predictions
3. **Data Lake**: Export to Parquet for analytics
4. **API Layer**: REST API on top of database
5. **Caching**: Redis for frequently accessed data
6. **CDC**: Change Data Capture for downstream systems
