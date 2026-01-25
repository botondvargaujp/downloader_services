# TransferRoom Database Schema Diagram

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TRANSFERROOM DATABASE SCHEMA                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐
│  transferroom_countries      │
├──────────────────────────────┤
│ PK  country_id              │
│ UQ  transferroom_country_id │──┐
│     country_name             │  │
│     created_at               │  │
│     updated_at               │  │
└──────────────────────────────┘  │
                                   │
                                   │ FK
                                   │
┌──────────────────────────────────▼───────────────────────────────┐
│  transferroom_competitions                                       │
├──────────────────────────────────────────────────────────────────┤
│ PK  competition_id                                              │
│ UQ  transferroom_competition_id                                 │
│ FK  country_id                    → transferroom_countries      │
│     transferroom_country_id       (denormalized)                │
│     competition_name                                            │
│     country_name                  (denormalized)                │
│     division_level                CHECK (1-10)                  │
│     teams_data                    JSONB                         │
│     avg_team_rating               NUMERIC(10,2)                 │
│     avg_starter_rating            NUMERIC(10,2)                 │
│     is_active                     BOOLEAN                       │
│     created_at                    TIMESTAMPTZ                   │
│     updated_at                    TIMESTAMPTZ                   │
│     last_synced_at                TIMESTAMPTZ                   │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    │ FK                          │ FK
                    │                             │
         ┌──────────▼─────────────┐   ┌──────────▼────────────────────────────────┐
         │ transferroom_teams     │   │  transferroom_players                     │
         ├────────────────────────┤   ├───────────────────────────────────────────┤
         │ PK  team_id           │   │ PK  player_id                            │
         │ UQ  transferroom_     │   │ UQ  transferroom_player_id               │
         │     team_id           │   │     first_name                           │
         │ FK  competition_id    │   │     last_name                            │
         │     team_name         │   │     full_name                            │
         │     is_active         │   │     nationality                          │
         │     created_at        │   │     date_of_birth                        │
         │     updated_at        │   │     age                                  │
         │     last_synced_at    │   │     first_position                       │
         └───────────────────────┘   │     second_position                      │
                                     │     first_position_full                  │
                                     │     second_position_full                 │
                                     │     current_club                         │
                                     │     transferroom_team_id                 │
                                     │ FK  competition_id                       │
                                     │     transferroom_competition_id          │
                                     │     competition_name                     │
                                     │     contract_expires                     │
                                     │     contract_expires_string              │
                                     │     market_value_euros                   │
                                     │     market_value_currency                │
                                     │     height_cm            CHECK(0-250)    │
                                     │     weight_kg            CHECK(0-200)    │
                                     │     preferred_foot                       │
                                     │     overall_rating       CHECK(0-100)    │
                                     │     potential_rating     CHECK(0-100)    │
                                     │     availability_status                  │
                                     │     transfer_type                        │
                                     │     is_available_for_transfer  BOOLEAN   │
                                     │     is_available_for_loan      BOOLEAN   │
                                     │     raw_data                   JSONB     │
                                     │     is_active                  BOOLEAN   │
                                     │     created_at                 TIMESTAMPTZ│
                                     │     updated_at                 TIMESTAMPTZ│
                                     │     last_synced_at             TIMESTAMPTZ│
                                     └──────────────────┬────────────────────────┘
                                                        │
                                                        │
                                                        │ FK
                                                        │
                              ┌─────────────────────────▼────────────────────────┐
                              │  transferroom_players_history                    │
                              ├──────────────────────────────────────────────────┤
                              │ PK  history_id                                  │
                              │ FK  player_id        → transferroom_players     │
                              │     transferroom_player_id                      │
                              │     change_type                                 │
                              │     old_value         JSONB                     │
                              │     new_value         JSONB                     │
                              │     changed_at        TIMESTAMPTZ               │
                              │ FK  sync_run_id      → data_sync_runs           │
                              └─────────────────────────────────────────────────┘


┌────────────────────────────────────────────────────────────────┐
│  data_sync_runs                                                │
├────────────────────────────────────────────────────────────────┤
│ PK  sync_run_id                                               │
│     sync_type              ('competitions', 'players', etc.)   │
│     status                 ('in_progress', 'completed', etc.)  │
│     records_fetched                                            │
│     records_inserted                                           │
│     records_updated                                            │
│     records_failed                                             │
│     error_message          TEXT                                │
│     started_at             TIMESTAMPTZ                         │
│     completed_at           TIMESTAMPTZ                         │
│     duration_seconds       INTEGER                             │
│     metadata               JSONB                               │
└────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                          VIEWS                                  │
├─────────────────────────────────────────────────────────────────┤
│  • vw_active_competitions      - Active competitions with stats │
│  • vw_available_players        - Players available for transfer │
│  • vw_competition_rankings     - Competition strength rankings  │
└─────────────────────────────────────────────────────────────────┘
```

## Table Relationships

### Primary Relationships

1. **Countries → Competitions** (1:N)
   - One country has many competitions
   - Allows filtering competitions by country

2. **Competitions → Teams** (1:N)
   - One competition has many teams
   - Teams are extracted from JSONB `teams_data` field

3. **Competitions → Players** (1:N)
   - One competition has many players
   - Players are associated with their current competition

4. **Players → Players History** (1:N)
   - One player has many history records
   - Tracks all changes to player data over time

5. **Sync Runs → Players History** (1:N)
   - One sync run can affect many player records
   - Provides audit trail for when changes occurred

## Indexing Strategy

### B-Tree Indexes (Standard Lookups)
```
transferroom_countries:
  - PRIMARY KEY: country_id
  - UNIQUE: transferroom_country_id
  - INDEX: country_name

transferroom_competitions:
  - PRIMARY KEY: competition_id
  - UNIQUE: transferroom_competition_id
  - INDEX: country_id
  - INDEX: division_level
  - COMPOSITE: (country_id, division_level)
  - PARTIAL: avg_team_rating WHERE NOT NULL
  - PARTIAL: is_active WHERE TRUE

transferroom_players:
  - PRIMARY KEY: player_id
  - UNIQUE: transferroom_player_id
  - INDEX: first_position, second_position
  - INDEX: competition_id
  - INDEX: nationality
  - INDEX: age, overall_rating
  - INDEX: last_name, full_name
  - COMPOSITE: (first_position, overall_rating DESC)
  - COMPOSITE: (competition_id, first_position)
  - PARTIAL: is_available_for_transfer WHERE TRUE
  - PARTIAL: contract_expires WHERE NOT NULL
```

### GIN Indexes (JSONB & Full-Text Search)
```
transferroom_competitions:
  - GIN: teams_data (for JSONB queries)

transferroom_players:
  - GIN: raw_data (for JSONB queries)
  - GIN: to_tsvector(full_name) (for full-text search)
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION FLOW                          │
└─────────────────────────────────────────────────────────────────────┘

 API Request
      │
      ▼
┌──────────────────┐
│ TransferRoom API │
└────────┬─────────┘
         │
         │ JSON Response
         │
         ▼
┌────────────────────────────┐
│  API Client                │
│  - Authentication          │
│  - Retry Logic             │
│  - Rate Limiting           │
└────────┬───────────────────┘
         │
         │ Parsed Data
         │
         ▼
┌────────────────────────────┐
│  Data Transformation       │
│  - Normalize structures    │
│  - Map position codes      │
│  - Validate fields         │
│  - Extract relationships   │
└────────┬───────────────────┘
         │
         │ Transformed Records
         │
         ▼
┌────────────────────────────┐      ┌──────────────────────┐
│  Upsert Logic              │─────▶│  data_sync_runs      │
│  - Check if exists         │      │  (Start tracking)    │
│  - Compare with current    │      └──────────────────────┘
│  - Insert or Update        │
│  - Record in history       │
└────────┬───────────────────┘
         │
         │ Database Operations
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
│                                                             │
│  1. Upsert Countries                                        │
│     └─► transferroom_countries                             │
│                                                             │
│  2. Upsert Competitions                                     │
│     └─► transferroom_competitions                          │
│                                                             │
│  3. Extract & Upsert Teams                                  │
│     └─► transferroom_teams                                 │
│                                                             │
│  4. Upsert Players                                          │
│     └─► transferroom_players                               │
│          └─► transferroom_players_history (if changed)     │
│                                                             │
│  5. Update Sync Run                                         │
│     └─► data_sync_runs (Complete)                          │
└─────────────────────────────────────────────────────────────┘
```

## Data Types Summary

### JSONB Fields (Flexible Schema)
- `competitions.teams_data` - Array of team objects from API
- `players.raw_data` - Complete player object from API
- `players_history.old_value` - Previous state snapshot
- `players_history.new_value` - New state snapshot
- `sync_runs.metadata` - Additional sync information

### Timestamp Fields (Audit Trail)
- `created_at` - When record was first inserted
- `updated_at` - When record was last modified (auto-updated via trigger)
- `last_synced_at` - When data was last fetched from API
- `changed_at` - When change occurred (history table)

### Enum-like Fields (String Constraints)
```sql
sync_type:          'competitions', 'players', 'teams'
status:             'in_progress', 'completed', 'failed'
change_type:        'club_change', 'rating_change', 'contract_update'
availability_status: 'Available', 'Not Available', 'On Loan'
transfer_type:      'Permanent', 'Loan', 'Free Transfer'
preferred_foot:     'Left', 'Right', 'Both'
```

## Performance Characteristics

### Query Performance (Estimated)

| Query Type                        | Rows    | Index Used                  | Est. Time |
|-----------------------------------|---------|-----------------------------|-----------|
| Player by ID                      | 1       | PK (player_id)              | < 1ms     |
| Players by position               | ~5K     | idx_players_first_position  | < 10ms    |
| Top players by rating             | 100     | idx_players_overall_rating  | < 5ms     |
| Players in competition            | ~500    | idx_players_competition     | < 5ms     |
| Competition by country & division | 1       | idx_competitions_country_   | < 2ms     |
| Full-text player name search      | ~10     | idx_players_fulltext_name   | < 20ms    |
| JSONB query on raw_data           | Varies  | idx_players_raw_data_gin    | < 50ms    |

### Storage Estimates (for planning)

| Table                  | Est. Rows  | Est. Size  | Notes                        |
|------------------------|------------|------------|------------------------------|
| countries              | ~200       | < 1 MB     | Small reference table        |
| competitions           | ~2,000     | 5-10 MB    | Includes JSONB teams_data    |
| teams                  | ~40,000    | 10-20 MB   | Extracted from competitions  |
| players                | ~500,000   | 500 MB-1GB | Includes large JSONB field   |
| players_history        | ~5,000,000 | 2-5 GB     | Grows over time             |
| data_sync_runs         | ~1,000     | < 5 MB     | Audit trail                 |

**Total Estimated**: 3-7 GB (after 1 year of operation)

## Security & Access Control

### Recommended User Roles

```sql
-- Read-only role for analytics
CREATE ROLE transferroom_readonly;
GRANT CONNECT ON DATABASE transferroom TO transferroom_readonly;
GRANT USAGE ON SCHEMA public TO transferroom_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO transferroom_readonly;

-- Application role for data ingestion
CREATE ROLE transferroom_app;
GRANT CONNECT ON DATABASE transferroom TO transferroom_app;
GRANT USAGE ON SCHEMA public TO transferroom_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO transferroom_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO transferroom_app;

-- Admin role for maintenance
CREATE ROLE transferroom_admin;
GRANT ALL PRIVILEGES ON DATABASE transferroom TO transferroom_admin;
```

## Monitoring Queries

### Check Sync Health
```sql
SELECT 
    sync_type,
    status,
    COUNT(*) as run_count,
    AVG(duration_seconds) as avg_duration,
    MAX(started_at) as last_run
FROM data_sync_runs
WHERE started_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY sync_type, status;
```

### Table Growth Over Time
```sql
SELECT 
    date_trunc('day', created_at) as day,
    COUNT(*) as new_players
FROM transferroom_players
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY day
ORDER BY day;
```

### Most Changed Players
```sql
SELECT 
    p.full_name,
    COUNT(h.history_id) as change_count,
    MAX(h.changed_at) as last_change
FROM transferroom_players_history h
JOIN transferroom_players p ON h.player_id = p.player_id
GROUP BY p.player_id, p.full_name
ORDER BY change_count DESC
LIMIT 20;
```
