"""
TransferRoom Data Ingestion Pipeline
=====================================
Ingests data from TransferRoom API into PostgreSQL following best practices.
"""

import json
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from dataclasses import dataclass
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SyncRunStats:
    """Track statistics for a sync run"""
    records_fetched: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class TransferRoomAPIClient:
    """Handle API communication with TransferRoom"""
    
    BASE_URL = "https://apiprod.transferroom.com/api/external"
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.token: Optional[str] = None
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry logic"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def authenticate(self) -> str:
        """Authenticate and get bearer token"""
        logger.info("Authenticating with TransferRoom API...")
        
        auth_url = f"{self.BASE_URL}/login"
        params = {
            'email': self.email,
            'password': self.password
        }
        
        try:
            response = self.session.post(auth_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.token = data['token']
            logger.info("Authentication successful")
            return self.token
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.token:
            self.authenticate()
        
        return {
            "Authorization": f"Bearer {self.token}"
        }
    
    def fetch_competitions(self) -> List[Dict]:
        """Fetch all competitions"""
        logger.info("Fetching competitions from API...")
        
        # Note: Update this URL based on actual API endpoint
        # This is a placeholder - check API docs for actual endpoint
        url = f"{self.BASE_URL}/competitions"
        
        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched {len(data)} competitions")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch competitions: {e}")
            raise
    
    def fetch_players(self, offset: int = 0, limit: int = 10000) -> List[Dict]:
        """Fetch players with pagination"""
        logger.info(f"Fetching players from API (offset={offset}, limit={limit})...")
        
        url = f"{self.BASE_URL}/players"
        params = {
            'position': offset,
            'amount': limit
        }
        
        try:
            response = self.session.get(
                url,
                headers=self.get_headers(),
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list):
                logger.info(f"Fetched {len(data)} players")
                return data
            else:
                logger.warning("Unexpected response format")
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch players: {e}")
            raise


class TransferRoomDataPipeline:
    """Main pipeline for ingesting TransferRoom data"""
    
    POSITION_MAP = {
        "GK": "Goalkeeper",
        "CB": "Centre-Back",
        "LB": "Left-Back",
        "RB": "Right-Back",
        "DM": "Defensive-Midfield",
        "CM": "Central-Midfield",
        "AM": "Attacking-Midfield",
        "W": "Winger",
        "F": "Forward"
    }
    
    def __init__(self, db_connection_string: str, api_email: str, api_password: str):
        self.db_conn_string = db_connection_string
        self.api_client = TransferRoomAPIClient(api_email, api_password)
        self.sync_run_id: Optional[int] = None
    
    def _get_position_full_name(self, pos_code: Optional[str]) -> Optional[str]:
        """Map position code to full name"""
        if not pos_code:
            return None
        return self.POSITION_MAP.get(pos_code, pos_code)
    
    def _start_sync_run(self, conn, sync_type: str) -> int:
        """Start a new sync run and return its ID"""
        query = """
            INSERT INTO data_sync_runs (sync_type, status, started_at)
            VALUES (%s, %s, %s)
            RETURNING sync_run_id
        """
        
        with conn.cursor() as cur:
            cur.execute(query, (sync_type, 'in_progress', datetime.now(timezone.utc)))
            sync_run_id = cur.fetchone()[0]
            conn.commit()
            
        logger.info(f"Started sync run {sync_run_id} for {sync_type}")
        return sync_run_id
    
    def _complete_sync_run(
        self,
        conn,
        sync_run_id: int,
        status: str,
        stats: SyncRunStats,
        error_message: Optional[str] = None
    ):
        """Complete a sync run with final statistics"""
        started_query = "SELECT started_at FROM data_sync_runs WHERE sync_run_id = %s"
        
        with conn.cursor() as cur:
            cur.execute(started_query, (sync_run_id,))
            started_at = cur.fetchone()[0]
            
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - started_at).total_seconds())
            
            update_query = """
                UPDATE data_sync_runs
                SET status = %s,
                    records_fetched = %s,
                    records_inserted = %s,
                    records_updated = %s,
                    records_failed = %s,
                    error_message = %s,
                    completed_at = %s,
                    duration_seconds = %s,
                    metadata = %s
                WHERE sync_run_id = %s
            """
            
            metadata = json.dumps({'errors': stats.errors[:10]})  # Store first 10 errors
            
            cur.execute(update_query, (
                status,
                stats.records_fetched,
                stats.records_inserted,
                stats.records_updated,
                stats.records_failed,
                error_message,
                completed_at,
                duration,
                metadata,
                sync_run_id
            ))
            conn.commit()
        
        logger.info(
            f"Sync run {sync_run_id} completed: {status} "
            f"(fetched={stats.records_fetched}, "
            f"inserted={stats.records_inserted}, "
            f"updated={stats.records_updated}, "
            f"failed={stats.records_failed})"
        )
    
    def ingest_competitions(self, competitions_file: str = 'competitions.json'):
        """Ingest competitions from JSON file into database"""
        logger.info("Starting competitions ingestion...")
        
        stats = SyncRunStats()
        
        try:
            # Load competitions from file
            with open(competitions_file, 'r', encoding='utf-8') as f:
                competitions = json.load(f)
            
            stats.records_fetched = len(competitions)
            
            with psycopg.connect(self.db_conn_string) as conn:
                sync_run_id = self._start_sync_run(conn, 'competitions')
                
                try:
                    # First, upsert countries
                    country_map = self._upsert_countries(conn, competitions)
                    
                    # Then upsert competitions
                    for comp in competitions:
                        try:
                            self._upsert_competition(conn, comp, country_map)
                            stats.records_inserted += 1
                        except Exception as e:
                            logger.error(f"Failed to upsert competition {comp.get('Id')}: {e}")
                            stats.records_failed += 1
                            stats.errors.append(str(e))
                    
                    conn.commit()
                    self._complete_sync_run(conn, sync_run_id, 'completed', stats)
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Competitions ingestion failed: {e}")
                    self._complete_sync_run(conn, sync_run_id, 'failed', stats, str(e))
                    raise
        
        except Exception as e:
            logger.error(f"Failed to load competitions file: {e}")
            raise
    
    def _upsert_countries(self, conn, competitions: List[Dict]) -> Dict[int, int]:
        """Extract and upsert unique countries, return mapping of TR country_id -> DB country_id"""
        logger.info("Upserting countries...")
        
        # Extract unique countries
        countries = {}
        for comp in competitions:
            country_id = comp.get('CountryId')
            country_name = comp.get('Country')
            if country_id and country_name:
                countries[country_id] = country_name
        
        country_map = {}
        
        upsert_query = """
            INSERT INTO transferroom_countries (transferroom_country_id, country_name)
            VALUES (%s, %s)
            ON CONFLICT (transferroom_country_id) DO UPDATE
            SET country_name = EXCLUDED.country_name,
                updated_at = CURRENT_TIMESTAMP
            RETURNING country_id, transferroom_country_id
        """
        
        with conn.cursor() as cur:
            for tr_country_id, country_name in countries.items():
                cur.execute(upsert_query, (tr_country_id, country_name))
                result = cur.fetchone()
                country_map[tr_country_id] = result[0]
        
        logger.info(f"Upserted {len(countries)} countries")
        return country_map
    
    def _upsert_competition(self, conn, comp: Dict, country_map: Dict[int, int]):
        """Upsert a single competition"""
        tr_competition_id = comp.get('Id')
        tr_country_id = comp.get('CountryId')
        country_id = country_map.get(tr_country_id)
        
        # Parse teams JSON if it's a string
        teams_data = comp.get('Teams')
        if isinstance(teams_data, str):
            try:
                teams_data = json.loads(teams_data)
            except json.JSONDecodeError:
                teams_data = None
        
        upsert_query = """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (transferroom_competition_id) DO UPDATE
            SET competition_name = EXCLUDED.competition_name,
                country_id = EXCLUDED.country_id,
                transferroom_country_id = EXCLUDED.transferroom_country_id,
                country_name = EXCLUDED.country_name,
                division_level = EXCLUDED.division_level,
                teams_data = EXCLUDED.teams_data,
                avg_team_rating = EXCLUDED.avg_team_rating,
                avg_starter_rating = EXCLUDED.avg_starter_rating,
                updated_at = CURRENT_TIMESTAMP,
                last_synced_at = CURRENT_TIMESTAMP
        """
        
        with conn.cursor() as cur:
            cur.execute(upsert_query, (
                tr_competition_id,
                comp.get('CompetitionName'),
                country_id,
                tr_country_id,
                comp.get('Country'),
                comp.get('DivisionLevel'),
                json.dumps(teams_data) if teams_data else None,
                comp.get('AvgTeamRating'),
                comp.get('AvgStarterRating'),
                datetime.now(timezone.utc)
            ))
    
    def ingest_players_from_api(self, max_records: Optional[int] = None):
        """Ingest players from TransferRoom API"""
        logger.info("Starting players ingestion from API...")
        
        stats = SyncRunStats()
        
        with psycopg.connect(self.db_conn_string) as conn:
            sync_run_id = self._start_sync_run(conn, 'players')
            
            try:
                offset = 0
                batch_size = 10000  # API returns 10k per request
                process_batch_size = 100  # Process and commit every 100 players
                total_processed = 0
                
                while True:
                    # Check if we've reached max_records limit
                    if max_records and total_processed >= max_records:
                        logger.info(f"✅ Reached max_records limit: {max_records}")
                        break
                    
                    # Fetch batch from API
                    logger.info(f"📥 Fetching players from API (offset={offset}, limit={batch_size})...")
                    players = self.api_client.fetch_players(offset, batch_size)
                    
                    if not players:
                        logger.info("✅ No more players to fetch")
                        break
                    
                    stats.records_fetched += len(players)
                    logger.info(f"📦 Fetched {len(players)} players from API")
                    
                    # Process in smaller batches with commits
                    batch_count = 0
                    for i, player in enumerate(players):
                        try:
                            self._upsert_player(conn, player)
                            stats.records_inserted += 1
                            total_processed += 1
                            batch_count += 1
                            
                            # Commit and report progress every process_batch_size players
                            if batch_count >= process_batch_size:
                                conn.commit()
                                logger.info(
                                    f"  ✓ Processed {total_processed} players "
                                    f"(inserted: {stats.records_inserted}, "
                                    f"failed: {stats.records_failed})"
                                )
                                batch_count = 0
                            
                            if max_records and total_processed >= max_records:
                                break
                                
                        except Exception as e:
                            conn.rollback()  # Roll back the failed transaction
                            logger.error(f"❌ Failed to upsert player {player.get('TR_ID')}: {e}")
                            stats.records_failed += 1
                            if len(stats.errors) < 10:  # Only store first 10 errors
                                stats.errors.append(str(e))
                            batch_count = 0  # Reset batch count after error
                    
                    # Commit any remaining players in the batch
                    if batch_count > 0:
                        conn.commit()
                        logger.info(
                            f"  ✓ Processed {total_processed} players "
                            f"(inserted: {stats.records_inserted}, "
                            f"failed: {stats.records_failed})"
                        )
                    
                    logger.info(f"📊 Progress: {total_processed}/{stats.records_fetched} players processed")
                    
                    offset += batch_size
                    
                    # Rate limiting
                    time.sleep(0.5)
                
                logger.info(f"🎉 Finished! Total players processed: {total_processed}")
                self._complete_sync_run(conn, sync_run_id, 'completed', stats)
                
            except Exception as e:
                conn.rollback()
                logger.error(f"💥 Players ingestion failed: {e}")
                self._complete_sync_run(conn, sync_run_id, 'failed', stats, str(e))
                raise
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to YYYY-MM-DD format"""
        if not date_str:
            return None
        try:
            # Handle ISO format: "1995-06-26T00:00:00"
            if 'T' in date_str:
                return date_str.split('T')[0]
            return date_str
        except:
            return None
    
    def _parse_json_string(self, json_str: Optional[str]) -> Optional[str]:
        """Parse JSON string and return as JSON for JSONB field"""
        if not json_str:
            return None
        try:
            if isinstance(json_str, str):
                # Validate it's valid JSON
                parsed = json.loads(json_str)
                return json.dumps(parsed)
            return json.dumps(json_str)
        except:
            return None
    
    def _upsert_player(self, conn, player: Dict):
        """Upsert a single player with complete field mapping"""
        tr_player_id = player.get('TR_ID')
        
        # Get competition_id from database
        tr_competition_id = player.get('CompetitionId')
        competition_id = None
        
        if tr_competition_id:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT competition_id FROM transferroom_competitions WHERE transferroom_competition_id = %s",
                    (tr_competition_id,)
                )
                result = cur.fetchone()
                if result:
                    competition_id = result[0]
        
        # Map positions
        first_pos = player.get('FirstPosition')
        second_pos = player.get('SecondPosition')
        first_pos_full = self._get_position_full_name(first_pos)
        second_pos_full = self._get_position_full_name(second_pos)
        
        # Parse JSONB fields
        team_history = self._parse_json_string(player.get('TeamHistory'))
        xtv_history = self._parse_json_string(player.get('xTVHistory'))
        base_value_history = self._parse_json_string(player.get('BaseValueHistory'))
        
        # Parse dates
        birth_date = self._parse_date(player.get('BirthDate'))
        contract_expiry = self._parse_date(player.get('ContractExpiry'))
        
        # Convert boolean strings to actual booleans
        agency_verified = player.get('AgencyVerified')
        if isinstance(agency_verified, str):
            agency_verified = agency_verified.lower() == 'true'
        
        upsert_query = """
            INSERT INTO transferroom_players (
                transferroom_player_id,
                wyscout_id,
                trmarkt_id,
                name,
                birth_date,
                parent_team_id,
                current_team_id,
                parent_team,
                current_team,
                team_history,
                country,
                country_id,
                competition_id,
                transferroom_competition_id,
                competition,
                division_level,
                competition_name_mapped,
                parent_country,
                parent_country_id,
                parent_competition,
                parent_division_level,
                nationality1,
                nationality1_country_id,
                nationality2,
                nationality2_country_id,
                first_position,
                second_position,
                first_position_full,
                second_position_full,
                playing_style,
                preferred_foot,
                contract_expiry,
                agency,
                agency_verified,
                estimated_salary,
                shortlisted,
                current_club_recent_mins_perc,
                gbe_score,
                gbe_result,
                gbe_int_app_pts,
                gbe_dom_mins_pts,
                gbe_cont_mins_pts,
                gbe_league_pos_pts,
                gbe_cont_prog_pts,
                gbe_league_std_pts,
                xtv,
                xtv_change_6m_perc,
                xtv_change_12m_perc,
                xtv_history,
                base_value,
                base_value_history,
                rating,
                potential,
                available_sale,
                available_asking_price,
                available_sell_on,
                available_loan,
                available_monthly_loan_fee,
                available_currency,
                raw_data
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (transferroom_player_id) DO UPDATE
            SET wyscout_id = EXCLUDED.wyscout_id,
                trmarkt_id = EXCLUDED.trmarkt_id,
                name = EXCLUDED.name,
                birth_date = EXCLUDED.birth_date,
                parent_team_id = EXCLUDED.parent_team_id,
                current_team_id = EXCLUDED.current_team_id,
                parent_team = EXCLUDED.parent_team,
                current_team = EXCLUDED.current_team,
                team_history = EXCLUDED.team_history,
                country = EXCLUDED.country,
                country_id = EXCLUDED.country_id,
                competition_id = EXCLUDED.competition_id,
                transferroom_competition_id = EXCLUDED.transferroom_competition_id,
                competition = EXCLUDED.competition,
                division_level = EXCLUDED.division_level,
                competition_name_mapped = EXCLUDED.competition_name_mapped,
                parent_country = EXCLUDED.parent_country,
                parent_country_id = EXCLUDED.parent_country_id,
                parent_competition = EXCLUDED.parent_competition,
                parent_division_level = EXCLUDED.parent_division_level,
                nationality1 = EXCLUDED.nationality1,
                nationality1_country_id = EXCLUDED.nationality1_country_id,
                nationality2 = EXCLUDED.nationality2,
                nationality2_country_id = EXCLUDED.nationality2_country_id,
                first_position = EXCLUDED.first_position,
                second_position = EXCLUDED.second_position,
                first_position_full = EXCLUDED.first_position_full,
                second_position_full = EXCLUDED.second_position_full,
                playing_style = EXCLUDED.playing_style,
                preferred_foot = EXCLUDED.preferred_foot,
                contract_expiry = EXCLUDED.contract_expiry,
                agency = EXCLUDED.agency,
                agency_verified = EXCLUDED.agency_verified,
                estimated_salary = EXCLUDED.estimated_salary,
                shortlisted = EXCLUDED.shortlisted,
                current_club_recent_mins_perc = EXCLUDED.current_club_recent_mins_perc,
                gbe_score = EXCLUDED.gbe_score,
                gbe_result = EXCLUDED.gbe_result,
                gbe_int_app_pts = EXCLUDED.gbe_int_app_pts,
                gbe_dom_mins_pts = EXCLUDED.gbe_dom_mins_pts,
                gbe_cont_mins_pts = EXCLUDED.gbe_cont_mins_pts,
                gbe_league_pos_pts = EXCLUDED.gbe_league_pos_pts,
                gbe_cont_prog_pts = EXCLUDED.gbe_cont_prog_pts,
                gbe_league_std_pts = EXCLUDED.gbe_league_std_pts,
                xtv = EXCLUDED.xtv,
                xtv_change_6m_perc = EXCLUDED.xtv_change_6m_perc,
                xtv_change_12m_perc = EXCLUDED.xtv_change_12m_perc,
                xtv_history = EXCLUDED.xtv_history,
                base_value = EXCLUDED.base_value,
                base_value_history = EXCLUDED.base_value_history,
                rating = EXCLUDED.rating,
                potential = EXCLUDED.potential,
                available_sale = EXCLUDED.available_sale,
                available_asking_price = EXCLUDED.available_asking_price,
                available_sell_on = EXCLUDED.available_sell_on,
                available_loan = EXCLUDED.available_loan,
                available_monthly_loan_fee = EXCLUDED.available_monthly_loan_fee,
                available_currency = EXCLUDED.available_currency,
                raw_data = EXCLUDED.raw_data,
                updated_at = CURRENT_TIMESTAMP,
                last_synced_at = CURRENT_TIMESTAMP
        """
        
        with conn.cursor() as cur:
            cur.execute(upsert_query, (
                tr_player_id,
                player.get('wyscout_id'),
                player.get('trmarkt_id'),
                player.get('Name'),
                birth_date,
                player.get('ParentTeamId'),
                player.get('CurrentTeamId'),
                player.get('ParentTeam'),
                player.get('CurrentTeam'),
                team_history,
                player.get('Country'),
                player.get('CountryId'),
                competition_id,
                tr_competition_id,
                player.get('Competition'),
                player.get('DivisionLevel'),
                player.get('CompetitionName_Mapped'),
                player.get('ParentCountry'),
                player.get('ParentCountryId'),
                player.get('ParentCompetition'),
                player.get('ParentDivisionLevel'),
                player.get('Nationality1'),
                player.get('Nationality1CountryId'),
                player.get('Nationality2'),
                player.get('Nationality2CountryId'),
                first_pos,
                second_pos,
                first_pos_full,
                second_pos_full,
                player.get('PlayingStyle'),
                player.get('PreferredFoot'),
                contract_expiry,
                player.get('Agency'),
                agency_verified,
                player.get('EstimatedSalary'),
                player.get('Shortlisted'),
                player.get('CurrentClubRecentMinsPerc'),
                player.get('GBEScore'),
                player.get('GBEResult'),
                player.get('GBEIntAppPts'),
                player.get('GBEDomMinsPts'),
                player.get('GBEContMinsPts'),
                player.get('GBELeaguePosPts'),
                player.get('GBEContProgPts'),
                player.get('GBELeagueStdPts'),
                player.get('xTV'),
                player.get('xTVChange6mPerc'),
                player.get('xTVChange12mPerc'),
                xtv_history,
                player.get('BaseValue'),
                base_value_history,
                player.get('Rating'),
                player.get('Potential'),
                player.get('AvailableSale'),
                player.get('AvailableAskingPrice'),
                player.get('AvailableSellOn'),
                player.get('AvailableLoan'),
                player.get('AvailableMonthlyLoanFee'),
                player.get('AvailableCurrency'),
                json.dumps(player)
            ))


def main():
    """Main entry point"""
    import os
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='TransferRoom Data Ingestion Pipeline')
    parser.add_argument('--competitions-only', action='store_true', 
                        help='Only ingest competitions (skip players)')
    parser.add_argument('--players-only', action='store_true',
                        help='Only ingest players (skip competitions)')
    parser.add_argument('--max-players', type=int, default=None,
                        help='Maximum number of players to fetch (default: all)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: fetch only 100 players')
    args = parser.parse_args()
    
    # Configuration (use environment variables in production)
    DB_CONNECTION = os.getenv(
        'DATABASE_URL',
        'postgresql://localhost/transferroom'
    )
    API_EMAIL = os.getenv('TRANSFERROOM_EMAIL', 'varga.samu@ujpestfc.hu')
    API_PASSWORD = os.getenv('TRANSFERROOM_PASSWORD', 'Ujpest1885!')
    
    # Create pipeline
    pipeline = TransferRoomDataPipeline(DB_CONNECTION, API_EMAIL, API_PASSWORD)
    
    # Run ingestion
    logger.info("=" * 80)
    logger.info("Starting TransferRoom Data Ingestion")
    logger.info("=" * 80)
    
    try:
        # Determine max records
        max_records = 100 if args.test else args.max_players
        
        # Ingest competitions from file (unless players-only)
        if not args.players_only:
            logger.info("Ingesting competitions...")
            pipeline.ingest_competitions('competitions.json')
        
        # Ingest players from API (unless competitions-only)
        if not args.competitions_only:
            logger.info("Ingesting players from API...")
            if max_records:
                logger.info(f"Max players to fetch: {max_records}")
            pipeline.ingest_players_from_api(max_records=max_records)
        
        logger.info("=" * 80)
        logger.info("Data ingestion completed successfully!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Data ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
