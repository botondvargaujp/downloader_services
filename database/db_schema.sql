-- =============================================================================
-- TransferRoom Database Schema
-- =============================================================================
-- Best Practices Applied:
-- 1. Use surrogate keys (serial/bigserial) for primary keys
-- 2. Add natural unique constraints where appropriate
-- 3. Add timestamps for data tracking (created_at, updated_at)
-- 4. Use proper data types (JSONB for nested data, numeric for ratings)
-- 5. Add indexes for frequently queried columns
-- 6. Use foreign keys for referential integrity
-- 7. Add check constraints for data validation
-- 8. Use proper naming conventions (snake_case)
-- =============================================================================

-- Enable UUID extension (optional, for future use)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- LOOKUP/DIMENSION TABLES
-- =============================================================================

-- Countries table (normalized from competitions data)
CREATE TABLE IF NOT EXISTS transferroom_countries (
    country_id SERIAL PRIMARY KEY,
    transferroom_country_id INTEGER UNIQUE NOT NULL, -- Original CountryId from API
    country_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX idx_countries_name ON transferroom_countries(country_name);
CREATE INDEX idx_countries_tr_id ON transferroom_countries(transferroom_country_id);

-- =============================================================================
-- COMPETITIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS transferroom_competitions (
    competition_id BIGSERIAL PRIMARY KEY,
    transferroom_competition_id INTEGER UNIQUE NOT NULL, -- Original Id from API
    competition_name VARCHAR(255) NOT NULL,
    country_id INTEGER REFERENCES transferroom_countries(country_id) ON DELETE SET NULL,
    transferroom_country_id INTEGER, -- Denormalized for easier queries
    country_name VARCHAR(100), -- Denormalized for easier queries
    division_level INTEGER CHECK (division_level >= 1 AND division_level <= 10),
    teams_data JSONB, -- Store the Teams JSON array
    avg_team_rating NUMERIC(10, 2), -- Allow NULL for missing data
    avg_starter_rating NUMERIC(10, 2), -- Allow NULL for missing data
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_competitions_tr_id ON transferroom_competitions(transferroom_competition_id);
CREATE INDEX idx_competitions_country ON transferroom_competitions(country_id);
CREATE INDEX idx_competitions_division ON transferroom_competitions(division_level);
CREATE INDEX idx_competitions_country_division ON transferroom_competitions(country_id, division_level);
CREATE INDEX idx_competitions_avg_rating ON transferroom_competitions(avg_team_rating) WHERE avg_team_rating IS NOT NULL;
CREATE INDEX idx_competitions_is_active ON transferroom_competitions(is_active) WHERE is_active = TRUE;

-- GIN index for JSONB queries on teams_data
CREATE INDEX idx_competitions_teams_gin ON transferroom_competitions USING GIN (teams_data);

-- =============================================================================
-- TEAMS TABLE (Extracted from competitions)
-- =============================================================================

CREATE TABLE IF NOT EXISTS transferroom_teams (
    team_id BIGSERIAL PRIMARY KEY,
    transferroom_team_id INTEGER UNIQUE NOT NULL, -- TR_id from Teams array
    competition_id BIGINT REFERENCES transferroom_competitions(competition_id) ON DELETE CASCADE,
    team_name VARCHAR(255), -- To be populated if available from API
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_teams_tr_id ON transferroom_teams(transferroom_team_id);
CREATE INDEX idx_teams_competition ON transferroom_teams(competition_id);

-- =============================================================================
-- PLAYERS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS transferroom_players (
    player_id BIGSERIAL PRIMARY KEY,
    transferroom_player_id INTEGER UNIQUE NOT NULL, -- TR_ID from API
    
    -- External IDs
    wyscout_id INTEGER,
    trmarkt_id INTEGER,
    
    -- Basic Information
    name VARCHAR(255), -- Full name from API
    birth_date DATE,
    
    -- Team Information
    parent_team_id INTEGER,
    current_team_id INTEGER,
    parent_team VARCHAR(255),
    current_team VARCHAR(255),
    team_history JSONB, -- Array of transfer history
    
    -- Country and Competition Information
    country VARCHAR(100),
    country_id INTEGER,
    competition_id BIGINT REFERENCES transferroom_competitions(competition_id) ON DELETE SET NULL,
    transferroom_competition_id INTEGER, -- CompetitionId from API
    competition VARCHAR(255),
    division_level INTEGER,
    competition_name_mapped VARCHAR(255), -- CompetitionName_Mapped from API
    
    -- Parent Competition Information (for loan players)
    parent_country VARCHAR(100),
    parent_country_id INTEGER,
    parent_competition VARCHAR(255),
    parent_division_level INTEGER,
    
    -- Nationality Information (can have dual nationality)
    nationality1 VARCHAR(100),
    nationality1_country_id INTEGER,
    nationality2 VARCHAR(100),
    nationality2_country_id INTEGER,
    
    -- Position Information
    first_position VARCHAR(50), -- e.g., 'CB', 'RB', 'F'
    second_position VARCHAR(50),
    first_position_full VARCHAR(100), -- Mapped full name (e.g., "Centre-Back")
    second_position_full VARCHAR(100),
    playing_style VARCHAR(50), -- e.g., 'Balanced'
    preferred_foot VARCHAR(20), -- 'Left', 'Right', 'Both'
    
    -- Contract Information
    contract_expiry DATE,
    agency VARCHAR(255),
    agency_verified BOOLEAN,
    estimated_salary VARCHAR(50), -- e.g., "20K - 30K"
    
    -- Scouting Information
    shortlisted VARCHAR(10), -- 'Yes', 'No'
    current_club_recent_mins_perc NUMERIC(5, 2), -- Percentage
    
    -- GBE (Governing Body Endorsement) Metrics
    gbe_score INTEGER CHECK (gbe_score >= 0 AND gbe_score <= 100),
    gbe_result VARCHAR(20), -- 'Pass', 'Fail'
    gbe_int_app_pts INTEGER, -- International appearance points
    gbe_dom_mins_pts INTEGER, -- Domestic minutes points
    gbe_cont_mins_pts INTEGER, -- Continental minutes points
    gbe_league_pos_pts INTEGER, -- League position points
    gbe_cont_prog_pts INTEGER, -- Continental progression points
    gbe_league_std_pts INTEGER, -- League standard points
    
    -- Transfer Value Metrics (xTV = Expected Transfer Value)
    xtv NUMERIC(15, 2), -- Current expected transfer value in euros
    xtv_change_6m_perc NUMERIC(6, 2), -- 6-month percentage change
    xtv_change_12m_perc NUMERIC(6, 2), -- 12-month percentage change
    xtv_history JSONB, -- Historical xTV values by month/year
    
    -- Base Value Metrics
    base_value NUMERIC(15, 2), -- Base market value in euros
    base_value_history JSONB, -- Historical base values by month/year
    
    -- Performance Ratings
    rating NUMERIC(4, 1) CHECK (rating >= 0 AND rating <= 100), -- Current rating (e.g., 59.8)
    potential NUMERIC(4, 1) CHECK (potential >= 0 AND potential <= 100), -- Potential rating (e.g., 65.0)
    
    -- Availability Information
    available_sale BOOLEAN,
    available_asking_price NUMERIC(15, 2),
    available_sell_on NUMERIC(5, 2), -- Sell-on percentage
    available_loan BOOLEAN,
    available_monthly_loan_fee NUMERIC(15, 2),
    available_currency VARCHAR(10), -- Currency for availability prices
    
    -- Raw Data (store full API response for flexibility)
    raw_data JSONB,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_players_tr_id ON transferroom_players(transferroom_player_id);
CREATE INDEX idx_players_wyscout ON transferroom_players(wyscout_id) WHERE wyscout_id IS NOT NULL;
CREATE INDEX idx_players_trmarkt ON transferroom_players(trmarkt_id) WHERE trmarkt_id IS NOT NULL;
CREATE INDEX idx_players_name ON transferroom_players(name);
CREATE INDEX idx_players_first_position ON transferroom_players(first_position);
CREATE INDEX idx_players_second_position ON transferroom_players(second_position) WHERE second_position IS NOT NULL;
CREATE INDEX idx_players_competition ON transferroom_players(competition_id);
CREATE INDEX idx_players_tr_competition ON transferroom_players(transferroom_competition_id) WHERE transferroom_competition_id IS NOT NULL;
CREATE INDEX idx_players_country ON transferroom_players(country);
CREATE INDEX idx_players_nationality1 ON transferroom_players(nationality1);
CREATE INDEX idx_players_rating ON transferroom_players(rating) WHERE rating IS NOT NULL;
CREATE INDEX idx_players_potential ON transferroom_players(potential) WHERE potential IS NOT NULL;
CREATE INDEX idx_players_xtv ON transferroom_players(xtv) WHERE xtv IS NOT NULL;
CREATE INDEX idx_players_gbe_score ON transferroom_players(gbe_score) WHERE gbe_score IS NOT NULL;
CREATE INDEX idx_players_available_sale ON transferroom_players(available_sale) WHERE available_sale = TRUE;
CREATE INDEX idx_players_available_loan ON transferroom_players(available_loan) WHERE available_loan = TRUE;
CREATE INDEX idx_players_contract_expiry ON transferroom_players(contract_expiry) WHERE contract_expiry IS NOT NULL;
CREATE INDEX idx_players_current_team_id ON transferroom_players(current_team_id);
CREATE INDEX idx_players_parent_team_id ON transferroom_players(parent_team_id);

-- Composite indexes for common query patterns
CREATE INDEX idx_players_position_rating ON transferroom_players(first_position, rating DESC) WHERE rating IS NOT NULL;
CREATE INDEX idx_players_competition_position ON transferroom_players(transferroom_competition_id, first_position);
CREATE INDEX idx_players_country_position ON transferroom_players(country, first_position);
CREATE INDEX idx_players_division_rating ON transferroom_players(division_level, rating DESC) WHERE rating IS NOT NULL;

-- GIN indexes for JSONB queries
CREATE INDEX idx_players_raw_data_gin ON transferroom_players USING GIN (raw_data);
CREATE INDEX idx_players_team_history_gin ON transferroom_players USING GIN (team_history);
CREATE INDEX idx_players_xtv_history_gin ON transferroom_players USING GIN (xtv_history);

-- Full-text search index for player names
CREATE INDEX idx_players_fulltext_name ON transferroom_players USING GIN (to_tsvector('english', COALESCE(name, '')));

-- =============================================================================
-- AUDIT/SYNC TRACKING TABLES
-- =============================================================================

-- Track each sync/ingestion run
CREATE TABLE IF NOT EXISTS data_sync_runs (
    sync_run_id BIGSERIAL PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL, -- 'competitions', 'players', 'teams'
    status VARCHAR(50) NOT NULL, -- 'in_progress', 'completed', 'failed'
    records_fetched INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    metadata JSONB -- Store additional info about the sync
);

CREATE INDEX idx_sync_runs_type ON data_sync_runs(sync_type);
CREATE INDEX idx_sync_runs_status ON data_sync_runs(status);
CREATE INDEX idx_sync_runs_started ON data_sync_runs(started_at DESC);

-- =============================================================================
-- PLAYER HISTORY TABLE (Track changes over time)
-- =============================================================================

CREATE TABLE IF NOT EXISTS transferroom_players_history (
    history_id BIGSERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES transferroom_players(player_id) ON DELETE CASCADE,
    transferroom_player_id INTEGER NOT NULL,
    
    -- Track what changed
    change_type VARCHAR(50), -- 'club_change', 'rating_change', 'contract_update', etc.
    old_value JSONB,
    new_value JSONB,
    
    -- Metadata
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sync_run_id BIGINT REFERENCES data_sync_runs(sync_run_id) ON DELETE SET NULL
);

CREATE INDEX idx_players_history_player ON transferroom_players_history(player_id);
CREATE INDEX idx_players_history_changed_at ON transferroom_players_history(changed_at DESC);
CREATE INDEX idx_players_history_change_type ON transferroom_players_history(change_type);

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all relevant tables
CREATE TRIGGER update_countries_updated_at BEFORE UPDATE ON transferroom_countries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_competitions_updated_at BEFORE UPDATE ON transferroom_competitions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON transferroom_teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON transferroom_players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- View: Active competitions with full details
CREATE OR REPLACE VIEW vw_active_competitions AS
SELECT 
    c.competition_id,
    c.transferroom_competition_id,
    c.competition_name,
    c.country_name,
    c.division_level,
    c.avg_team_rating,
    c.avg_starter_rating,
    jsonb_array_length(c.teams_data) as team_count,
    c.last_synced_at
FROM transferroom_competitions c
WHERE c.is_active = TRUE
ORDER BY c.avg_team_rating DESC NULLS LAST, c.division_level;

-- View: Available players with competition details
CREATE OR REPLACE VIEW vw_available_players AS
SELECT 
    p.player_id,
    p.transferroom_player_id,
    p.name,
    p.birth_date,
    EXTRACT(YEAR FROM AGE(p.birth_date)) as age,
    p.nationality1,
    p.first_position,
    p.first_position_full,
    p.second_position_full,
    p.rating,
    p.potential,
    p.current_team,
    p.competition,
    p.country,
    c.avg_team_rating as competition_rating,
    p.division_level,
    p.contract_expiry,
    p.xtv,
    p.base_value,
    p.available_sale,
    p.available_asking_price,
    p.available_loan,
    p.available_monthly_loan_fee,
    p.gbe_score,
    p.gbe_result,
    p.last_synced_at
FROM transferroom_players p
LEFT JOIN transferroom_competitions c ON p.competition_id = c.competition_id
WHERE p.is_active = TRUE
    AND (p.available_sale = TRUE OR p.available_loan = TRUE)
ORDER BY p.rating DESC NULLS LAST;

-- View: Competition rankings by division and country
CREATE OR REPLACE VIEW vw_competition_rankings AS
SELECT 
    c.country_name,
    c.division_level,
    c.competition_name,
    c.avg_team_rating,
    c.avg_starter_rating,
    jsonb_array_length(c.teams_data) as team_count,
    RANK() OVER (PARTITION BY c.division_level ORDER BY c.avg_team_rating DESC NULLS LAST) as division_rank,
    RANK() OVER (PARTITION BY c.country_name ORDER BY c.division_level) as country_tier
FROM transferroom_competitions c
WHERE c.is_active = TRUE AND c.avg_team_rating IS NOT NULL
ORDER BY c.avg_team_rating DESC;

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE transferroom_competitions IS 'Stores football competitions from TransferRoom API with team ratings and division levels';
COMMENT ON TABLE transferroom_players IS 'Stores player profiles from TransferRoom API including positions, ratings, xTV metrics, GBE scores, and availability';
COMMENT ON TABLE transferroom_countries IS 'Normalized country reference table';
COMMENT ON TABLE transferroom_teams IS 'Teams extracted from competition data';
COMMENT ON TABLE data_sync_runs IS 'Tracks data synchronization runs from TransferRoom API';
COMMENT ON TABLE transferroom_players_history IS 'Audit trail for tracking player data changes over time';

COMMENT ON COLUMN transferroom_competitions.teams_data IS 'JSONB array of team IDs from the API response';
COMMENT ON COLUMN transferroom_players.raw_data IS 'Full JSON response from API for future reference and analysis';
COMMENT ON COLUMN transferroom_players.last_synced_at IS 'Timestamp of last successful sync from API';
COMMENT ON COLUMN transferroom_players.team_history IS 'JSONB array of player transfer history with dates, teams, and transfer types';
COMMENT ON COLUMN transferroom_players.xtv_history IS 'JSONB array of historical Expected Transfer Value (xTV) by month/year';
COMMENT ON COLUMN transferroom_players.base_value_history IS 'JSONB array of historical base market values by month/year';
COMMENT ON COLUMN transferroom_players.xtv IS 'Expected Transfer Value in euros - predicted market value';
COMMENT ON COLUMN transferroom_players.gbe_score IS 'Governing Body Endorsement score (UK work permit eligibility)';
COMMENT ON COLUMN transferroom_players.rating IS 'Current performance rating (0-100)';
COMMENT ON COLUMN transferroom_players.potential IS 'Potential future rating (0-100)';

-- =============================================================================
-- GRANT PERMISSIONS (adjust as needed for your setup)
-- =============================================================================

-- Example: Grant permissions to an application user
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO transferroom_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO transferroom_app;
