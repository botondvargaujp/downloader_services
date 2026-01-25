# Player Ingestion Guide

## Updated `ingest_pipeline.py`

The pipeline has been completely updated to:
- ✅ Match the **actual TransferRoom API player structure**
- ✅ Map all **60+ player fields** correctly
- ✅ Handle **JSONB fields** (team_history, xtv_history, base_value_history)
- ✅ Parse **dates** properly
- ✅ Support **command-line arguments** for flexible ingestion

---

## Usage

### 1. Test Mode (100 players only)
```bash
cd /Users/botondvarga/downloader_services
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
export DATABASE_URL="postgresql://localhost/transferroom"

# Test with 100 players
uv run ingest_pipeline.py --test
```

### 2. Fetch Specific Number of Players
```bash
# Fetch 1,000 players
uv run ingest_pipeline.py --players-only --max-players 1000

# Fetch 10,000 players
uv run ingest_pipeline.py --players-only --max-players 10000
```

### 3. Full Ingestion (All Players)
```bash
# Competitions + All Players
uv run ingest_pipeline.py

# Players only (skip competitions)
uv run ingest_pipeline.py --players-only
```

### 4. Competitions Only
```bash
uv run ingest_pipeline.py --competitions-only
```

---

## Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `--test` | Test mode: fetch only 100 players |
| `--max-players N` | Limit to N players |
| `--players-only` | Skip competitions, only fetch players |
| `--competitions-only` | Skip players, only fetch competitions |
| (no args) | Fetch both competitions and all players |

---

## Field Mapping

### Player Fields Mapped (60+ fields)

#### Identity & External IDs
```python
TR_ID → transferroom_player_id
wyscout_id → wyscout_id
trmarkt_id → trmarkt_id
Name → name
BirthDate → birth_date
```

#### Team Information
```python
ParentTeamId → parent_team_id
CurrentTeamId → current_team_id
ParentTeam → parent_team
CurrentTeam → current_team
TeamHistory → team_history (JSONB)
```

#### Competition & Location
```python
Country → country
CountryId → country_id
CompetitionId → transferroom_competition_id
Competition → competition
DivisionLevel → division_level
CompetitionName_Mapped → competition_name_mapped
```

#### Parent Competition (for loaned players)
```python
ParentCountry → parent_country
ParentCountryId → parent_country_id
ParentCompetition → parent_competition
ParentDivisionLevel → parent_division_level
```

#### Nationality
```python
Nationality1 → nationality1
Nationality1CountryId → nationality1_country_id
Nationality2 → nationality2
Nationality2CountryId → nationality2_country_id
```

#### Position & Style
```python
FirstPosition → first_position (e.g., 'CB')
SecondPosition → second_position (e.g., 'RB')
PlayingStyle → playing_style (e.g., 'Balanced')
PreferredFoot → preferred_foot (e.g., 'Right')
```

#### Contract & Agency
```python
ContractExpiry → contract_expiry
Agency → agency
AgencyVerified → agency_verified
EstimatedSalary → estimated_salary (e.g., "20K - 30K")
```

#### Scouting
```python
Shortlisted → shortlisted ('Yes'/'No')
CurrentClubRecentMinsPerc → current_club_recent_mins_perc
```

#### GBE (UK Work Permit) Metrics
```python
GBEScore → gbe_score
GBEResult → gbe_result ('Pass'/'Fail')
GBEIntAppPts → gbe_int_app_pts
GBEDomMinsPts → gbe_dom_mins_pts
GBEContMinsPts → gbe_cont_mins_pts
GBELeaguePosPts → gbe_league_pos_pts
GBEContProgPts → gbe_cont_prog_pts
GBELeagueStdPts → gbe_league_std_pts
```

#### Transfer Value (xTV)
```python
xTV → xtv (Expected Transfer Value)
xTVChange6mPerc → xtv_change_6m_perc
xTVChange12mPerc → xtv_change_12m_perc
xTVHistory → xtv_history (JSONB)
BaseValue → base_value
BaseValueHistory → base_value_history (JSONB)
```

#### Ratings
```python
Rating → rating (e.g., 59.8)
Potential → potential (e.g., 65.0)
```

#### Availability
```python
AvailableSale → available_sale
AvailableAskingPrice → available_asking_price
AvailableSellOn → available_sell_on
AvailableLoan → available_loan
AvailableMonthlyLoanFee → available_monthly_loan_fee
AvailableCurrency → available_currency
```

---

## Testing Flow

### Step 1: Test with 100 Players
```bash
# Start small to verify everything works
uv run ingest_pipeline.py --test
```

**Expected output:**
```
Starting TransferRoom Data Ingestion
Starting players ingestion from API...
Max players to fetch: 100
Fetched 100 players
Processed 100 players so far...
Sync run 2 completed: completed (fetched=100, inserted=100, updated=0, failed=0)
```

### Step 2: Check the Data
```bash
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
psql -d transferroom << 'EOF'
-- Check counts
SELECT COUNT(*) as total_players FROM transferroom_players;

-- Sample player data
SELECT 
    name,
    first_position,
    rating,
    xtv,
    country,
    current_team
FROM transferroom_players
ORDER BY rating DESC NULLS LAST
LIMIT 10;

-- Check GBE data
SELECT 
    name,
    gbe_score,
    gbe_result,
    nationality1
FROM transferroom_players
WHERE gbe_score IS NOT NULL
ORDER BY gbe_score DESC
LIMIT 10;
EOF
```

### Step 3: Verify JSONB Fields
```sql
-- Check team history
SELECT 
    name,
    current_team,
    jsonb_array_length(team_history) as transfer_count
FROM transferroom_players
WHERE team_history IS NOT NULL
ORDER BY transfer_count DESC
LIMIT 5;

-- Check xTV history
SELECT 
    name,
    xtv,
    xtv_change_12m_perc,
    jsonb_array_length(xtv_history) as historical_points
FROM transferroom_players
WHERE xtv_history IS NOT NULL
ORDER BY xtv DESC NULLS LAST
LIMIT 5;
```

### Step 4: Expand to 1,000 Players
```bash
# If test went well, try 1,000
uv run ingest_pipeline.py --players-only --max-players 1000
```

### Step 5: Full Ingestion
```bash
# When ready, fetch all players
uv run ingest_pipeline.py --players-only
```

---

## Monitoring During Ingestion

### Check Progress
```sql
-- Watch sync runs in real-time
SELECT 
    sync_run_id,
    sync_type,
    status,
    records_fetched,
    records_inserted,
    records_failed,
    started_at,
    duration_seconds
FROM data_sync_runs
ORDER BY started_at DESC
LIMIT 5;
```

### Check Table Size
```sql
SELECT 
    pg_size_pretty(pg_total_relation_size('transferroom_players')) as size,
    COUNT(*) as row_count
FROM transferroom_players;
```

---

## Useful Queries After Ingestion

### Top Rated Players
```sql
SELECT 
    name,
    first_position,
    rating,
    potential,
    current_team,
    country,
    xtv
FROM transferroom_players
WHERE rating IS NOT NULL
ORDER BY rating DESC
LIMIT 20;
```

### UK Work Permit Eligible Players
```sql
SELECT 
    name,
    nationality1,
    gbe_score,
    gbe_result,
    rating,
    xtv
FROM transferroom_players
WHERE gbe_result = 'Pass'
  AND rating > 70
ORDER BY rating DESC;
```

### Available Players for Transfer
```sql
SELECT 
    name,
    first_position,
    rating,
    xtv,
    available_asking_price,
    current_team,
    contract_expiry
FROM transferroom_players
WHERE available_sale = TRUE
  AND rating > 65
ORDER BY rating DESC;
```

### Rising Star Players (xTV Increasing)
```sql
SELECT 
    name,
    age,
    first_position,
    rating,
    potential,
    xtv,
    xtv_change_12m_perc,
    current_team
FROM transferroom_players
WHERE xtv_change_12m_perc > 50
  AND rating IS NOT NULL
ORDER BY xtv_change_12m_perc DESC;
```

### Players by Competition Level
```sql
SELECT 
    division_level,
    COUNT(*) as player_count,
    ROUND(AVG(rating), 1) as avg_rating,
    ROUND(AVG(xtv), 0) as avg_xtv
FROM transferroom_players
WHERE rating IS NOT NULL
GROUP BY division_level
ORDER BY division_level;
```

### Transfer History Analysis
```sql
SELECT 
    name,
    current_team,
    jsonb_array_length(team_history) as career_moves,
    team_history
FROM transferroom_players
WHERE team_history IS NOT NULL
ORDER BY career_moves DESC
LIMIT 10;
```

---

## Troubleshooting

### API Authentication Issues
```bash
# Test API connection first
python3 -c "
from ingest_pipeline import TransferRoomAPIClient
client = TransferRoomAPIClient('varga.samu@ujpestfc.hu', 'Ujpest1885!')
token = client.authenticate()
print(f'✅ Token: {token[:50]}...')
"
```

### Database Connection Issues
```bash
# Test database connection
python3 -c "
import psycopg
conn = psycopg.connect('postgresql://localhost/transferroom')
print('✅ Database connection successful!')
conn.close()
"
```

### Check for Errors in Sync Runs
```sql
SELECT 
    sync_run_id,
    sync_type,
    status,
    records_failed,
    error_message,
    metadata
FROM data_sync_runs
WHERE status = 'failed' OR records_failed > 0
ORDER BY started_at DESC;
```

---

## Performance Tips

### Rate Limiting
The pipeline includes automatic rate limiting:
- 0.5 second delay between API requests
- Automatic retry on failures (3 attempts)
- Exponential backoff on rate limit errors

### Batch Processing
Players are processed in batches of 10,000 per API request:
- Efficient pagination
- Commits after each batch
- Progress logging every batch

### Expected Timing
- **100 players**: ~10-20 seconds
- **1,000 players**: ~1-2 minutes
- **10,000 players**: ~10-15 minutes
- **100,000 players**: ~1-2 hours
- **500,000+ players**: ~5-10 hours

---

## Success Checklist

After running player ingestion, verify:

- ✅ Sync run completed successfully
- ✅ records_fetched > 0
- ✅ records_inserted matches expected
- ✅ records_failed = 0
- ✅ Sample queries return data
- ✅ JSONB fields populated
- ✅ Dates parsed correctly
- ✅ Ratings in valid range (0-100)

---

Ready to test! Start with:

```bash
uv run ingest_pipeline.py --test
```

Good luck! 🚀
