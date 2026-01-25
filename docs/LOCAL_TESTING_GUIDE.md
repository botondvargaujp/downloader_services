# 🚀 Local PostgreSQL Setup & Testing Guide

## Step 1: Install PostgreSQL

```bash
# Install PostgreSQL using Homebrew
brew install postgresql@14

# Start PostgreSQL service
brew services start postgresql@14

# Add PostgreSQL to PATH (add to ~/.zshrc for permanent)
echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify installation
psql --version
```

**Expected output**: `psql (PostgreSQL) 14.x`

---

## Step 2: Create Database and Apply Schema

```bash
# Navigate to project directory
cd /Users/botondvarga/downloader_services

# Create the database
createdb transferroom

# Verify database was created
psql -l | grep transferroom

# Apply the schema
psql -d transferroom -f db_schema.sql

# Verify tables were created
psql -d transferroom -c "\dt"
```

**Expected output**: Should show 6 tables:
- `transferroom_countries`
- `transferroom_competitions`
- `transferroom_teams`
- `transferroom_players`
- `transferroom_players_history`
- `data_sync_runs`

---

## Step 3: Install Python Dependencies

```bash
# Make sure you're in the project directory
cd /Users/botondvarga/downloader_services

# Install dependencies using uv
uv pip install psycopg[binary] requests urllib3

# Verify installation
python3 -c "import psycopg; print('psycopg3 installed successfully!')"
```

---

## Step 4: Test Database Connection

Create a quick test script:

```bash
cat > test_db_connection.py << 'EOF'
import psycopg

try:
    # Connect to database
    conn = psycopg.connect("postgresql://localhost/transferroom")
    print("✅ Database connection successful!")
    
    # Test query
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ PostgreSQL version: {version}")
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        print(f"\n✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
    
    conn.close()
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
EOF

# Run the test
python3 test_db_connection.py
```

---

## Step 5: Test Competition Data Ingestion

```bash
# Run the ingestion pipeline (competitions only for now)
python3 ingest_pipeline.py
```

**This will**:
1. Load `competitions.json`
2. Extract and insert countries
3. Insert competitions
4. Track the sync run in `data_sync_runs`

---

## Step 6: Verify Data Was Loaded

```bash
# Check how many records were inserted
psql -d transferroom << 'EOF'
-- Check countries
SELECT 'Countries' as table_name, COUNT(*) as count FROM transferroom_countries
UNION ALL
SELECT 'Competitions', COUNT(*) FROM transferroom_competitions
UNION ALL
SELECT 'Players', COUNT(*) FROM transferroom_players;

-- Check sync runs
SELECT 
    sync_type,
    status,
    records_fetched,
    records_inserted,
    duration_seconds
FROM data_sync_runs
ORDER BY started_at DESC;

-- Show sample competitions
SELECT 
    competition_name,
    country_name,
    division_level,
    avg_team_rating
FROM transferroom_competitions
WHERE avg_team_rating IS NOT NULL
ORDER BY avg_team_rating DESC
LIMIT 10;
EOF
```

---

## Step 7: Query the Data

```bash
# Interactive PostgreSQL session
psql -d transferroom

# Or run specific queries:
psql -d transferroom -c "SELECT country_name, COUNT(*) as competitions FROM transferroom_competitions GROUP BY country_name ORDER BY competitions DESC LIMIT 10;"
```

### Example Queries to Test

```sql
-- Top competitions by rating
SELECT 
    competition_name,
    country_name,
    division_level,
    avg_team_rating,
    avg_starter_rating
FROM transferroom_competitions
WHERE avg_team_rating IS NOT NULL
ORDER BY avg_team_rating DESC
LIMIT 20;

-- Competitions by country
SELECT 
    country_name,
    COUNT(*) as total_competitions,
    COUNT(CASE WHEN division_level = 1 THEN 1 END) as tier1,
    COUNT(CASE WHEN division_level = 2 THEN 1 END) as tier2,
    AVG(avg_team_rating) as avg_rating
FROM transferroom_competitions
GROUP BY country_name
HAVING AVG(avg_team_rating) IS NOT NULL
ORDER BY avg_rating DESC
LIMIT 15;

-- Check data quality
SELECT 
    COUNT(*) as total_competitions,
    COUNT(CASE WHEN avg_team_rating IS NOT NULL THEN 1 END) as with_rating,
    COUNT(CASE WHEN avg_team_rating IS NULL THEN 1 END) as without_rating,
    MIN(division_level) as min_division,
    MAX(division_level) as max_division
FROM transferroom_competitions;
```

---

## Step 8: Test Player Data (Optional - Small Sample)

If you want to test player ingestion (without fetching from API):

```bash
# Create a test player insert script
cat > test_player_insert.py << 'EOF'
import psycopg
import json
from datetime import datetime

# Sample player data (based on your example)
test_player = {
    "TR_ID": 37388,
    "wyscout_id": 290911,
    "trmarkt_id": 298696,
    "Name": "Nurlan Dairov",
    "BirthDate": "1995-06-26T00:00:00",
    "CurrentTeam": "FC Taraz",
    "FirstPosition": "CB",
    "SecondPosition": "RB",
    "Rating": 59.8,
    "Potential": 65.0,
    "Country": "Kazakhstan",
    "CountryId": 129,
    "CompetitionId": 1993,
    "Competition": "1. Division",
    "DivisionLevel": 2,
    "Nationality1": "Kazakhstan",
    "FirstPosition": "CB",
    "SecondPosition": "RB",
    "PreferredFoot": "Right",
    "ContractExpiry": "2026-12-31T00:00:00",
    "GBEScore": 2,
    "GBEResult": "Fail",
    "xTV": 60000,
    "BaseValue": 70000,
    "EstimatedSalary": "20K - 30K"
}

conn = psycopg.connect("postgresql://localhost/transferroom")

try:
    with conn.cursor() as cur:
        # Simple insert to test
        cur.execute("""
            INSERT INTO transferroom_players (
                transferroom_player_id,
                wyscout_id,
                trmarkt_id,
                name,
                birth_date,
                current_team,
                first_position,
                second_position,
                rating,
                potential,
                country,
                country_id,
                transferroom_competition_id,
                competition,
                division_level,
                nationality1,
                preferred_foot,
                contract_expiry,
                gbe_score,
                gbe_result,
                xtv,
                base_value,
                estimated_salary,
                raw_data
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (transferroom_player_id) DO NOTHING
            RETURNING player_id;
        """, (
            test_player['TR_ID'],
            test_player['wyscout_id'],
            test_player['trmarkt_id'],
            test_player['Name'],
            '1995-06-26',
            test_player['CurrentTeam'],
            test_player['FirstPosition'],
            test_player['SecondPosition'],
            test_player['Rating'],
            test_player['Potential'],
            test_player['Country'],
            test_player['CountryId'],
            test_player['CompetitionId'],
            test_player['Competition'],
            test_player['DivisionLevel'],
            test_player['Nationality1'],
            test_player['PreferredFoot'],
            '2026-12-31',
            test_player['GBEScore'],
            test_player['GBEResult'],
            test_player['xTV'],
            test_player['BaseValue'],
            test_player['EstimatedSalary'],
            json.dumps(test_player)
        ))
        
        result = cur.fetchone()
        if result:
            print(f"✅ Test player inserted successfully! player_id: {result[0]}")
        else:
            print("⚠️  Player already exists (ON CONFLICT triggered)")
    
    conn.commit()
    
    # Verify
    with conn.cursor() as cur:
        cur.execute("""
            SELECT name, first_position, rating, xtv, gbe_result 
            FROM transferroom_players 
            WHERE transferroom_player_id = %s
        """, (test_player['TR_ID'],))
        
        player = cur.fetchone()
        print(f"\n✅ Verified player data:")
        print(f"   Name: {player[0]}")
        print(f"   Position: {player[1]}")
        print(f"   Rating: {player[2]}")
        print(f"   xTV: €{player[3]:,.0f}")
        print(f"   GBE: {player[4]}")
    
    conn.close()
    print("\n✅ Player insert test passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
    conn.close()
EOF

# Run the test
python3 test_player_insert.py
```

---

## Troubleshooting

### PostgreSQL won't start
```bash
# Check status
brew services list | grep postgresql

# Try restarting
brew services restart postgresql@14

# Check logs
tail -f /opt/homebrew/var/log/postgresql@14.log
```

### Can't connect to database
```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Try connecting as default user
psql postgres

# Check connection settings
psql -h localhost -d transferroom
```

### Schema errors
```bash
# Drop and recreate database
dropdb transferroom
createdb transferroom
psql -d transferroom -f db_schema.sql
```

### Python import errors
```bash
# Reinstall dependencies
uv pip install --force-reinstall psycopg[binary]
```

---

## Quick Command Reference

```bash
# Database operations
createdb transferroom          # Create database
dropdb transferroom            # Drop database
psql -d transferroom           # Connect to database
psql -l                        # List all databases

# Schema operations
psql -d transferroom -f db_schema.sql              # Apply schema
psql -d transferroom -c "\dt"                      # List tables
psql -d transferroom -c "\d transferroom_players"  # Describe table

# Query shortcuts
psql -d transferroom -c "SELECT COUNT(*) FROM transferroom_competitions;"

# Backup & Restore
pg_dump transferroom > backup.sql               # Backup
psql -d transferroom < backup.sql               # Restore
```

---

## Success Checklist

After running all steps, you should have:

- ✅ PostgreSQL 14 installed and running
- ✅ `transferroom` database created
- ✅ 6 tables created with proper schema
- ✅ Competition data loaded from `competitions.json`
- ✅ Countries extracted and stored
- ✅ Sync run tracked in `data_sync_runs`
- ✅ Able to query the data successfully

---

## Next Steps After Testing

1. **Update ingestion pipeline** to match new player schema
2. **Test with small player batch** (100-1000 players)
3. **Monitor performance** with indexes
4. **Set up regular syncs** (cron job)
5. **Build analytics queries** for your use case

---

## Performance Tips

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Analyze tables for better query planning
ANALYZE transferroom_competitions;
ANALYZE transferroom_players;
```

---

Ready to test! Start with **Step 1** and work your way through. Let me know if you hit any issues! 🚀
