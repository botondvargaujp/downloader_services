# StatsBomb API Reference Guide

## Authentication

All API calls require credentials passed as a dictionary:

```python
CREDS = {"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"}
```

These credentials are used with the `statsbombpy` Python library (not raw HTTP requests). Install it with:

```bash
pip install statsbombpy
```

Then import and pass `creds` to every call:

```python
from statsbombpy import sb

result = sb.competitions(creds=CREDS)
```

Under the hood, `statsbombpy` calls the StatsBomb REST API with HTTP Basic Auth against `https://data.statsbomb.com/api/...` endpoints.

---

## Available API Endpoints

### 1. Competitions

Returns all competitions and seasons your account has access to.

```python
competitions = sb.competitions(creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v4/competitions`

**Returns:** DataFrame with one row per competition-season pair.

**Key columns:**

| Column | Description |
|--------|-------------|
| `competition_id` | Unique competition identifier (e.g. `42` for La Liga 2) |
| `season_id` | Unique season identifier (e.g. `318` for 2025/2026) |
| `competition_name` | Human-readable name (e.g. "La Liga 2") |
| `season_name` | e.g. "2025/2026" |
| `country_name` | e.g. "Spain", "Hungary" |
| `competition_gender` | "male" or "female" |
| `match_available` | Timestamp of latest available match |
| `match_updated` | Timestamp of latest match update |

**Example — filter for a specific league:**

```python
comps = sb.competitions(creds=CREDS)
la_liga_2 = comps[
    (comps.country_name == "Spain")
    & (comps.competition_name.str.contains("La Liga 2", case=False))
    & (comps.competition_gender == "male")
]
competition_id = la_liga_2.competition_id.iloc[0]  # 42
```

**Currently available competitions under these credentials:**

| competition_id | Competition | country | Seasons available |
|---|---|---|---|
| 42 | La Liga 2 | Spain | 2023/2024, 2024/2025, 2025/2026 |
| 1522 | NB1 | Hungary | (check dynamically) |

---

### 2. Matches

Returns all matches for a given competition-season.

```python
matches = sb.matches(competition_id=42, season_id=318, creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v6/competitions/{competition_id}/seasons/{season_id}/matches`

**Returns:** DataFrame with one row per match.

**Key columns:**

| Column | Description |
|--------|-------------|
| `match_id` | Unique match identifier (used by all match-level endpoints) |
| `match_date` | Date string, e.g. "2025-10-19" |
| `home_team` | Home team name |
| `away_team` | Away team name |
| `home_score` | Goals scored by home team |
| `away_score` | Goals scored by away team |
| `competition` | Competition name |
| `season` | Season name |
| `competition_stage` | e.g. "Regular Season" |
| `stadium` | Venue name |
| `referee` | Referee name |
| `home_managers` | Home team manager(s) |
| `away_managers` | Away team manager(s) |
| `kick_off` | Kick-off time |
| `match_week` | Matchday number |
| `data_version` | StatsBomb data version |
| `collection_status` | e.g. "available" |

**Example — get Ujpest matches:**

```python
matches = sb.matches(competition_id=1522, season_id=318, creds=CREDS)
ujpest = matches[
    (matches.home_team == "Ujpest") | (matches.away_team == "Ujpest")
].sort_values("match_date")
```

---

### 3. Events

The core event stream for a match. This is the main dataset for analytics.

```python
events = sb.events(match_id=4007731, creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v9/events/{match_id}`

**Returns:** DataFrame with one row per event (typically 2000-4000 rows per match).

**Key columns (110+ total):**

| Column | Description |
|--------|-------------|
| `id` | Unique event ID |
| `type` | Event type: Pass, Shot, Carry, Dribble, Foul Committed, Pressure, etc. |
| `minute`, `second` | Match clock |
| `period` | 1 = first half, 2 = second half, etc. |
| `team`, `team_id` | Team performing the action |
| `player`, `player_id` | Player performing the action |
| `position` | Player's position at the time |
| `location` | [x, y] pitch coordinates |
| `possession` | Possession sequence number |
| `possession_team` | Team in possession |
| `play_pattern` | e.g. "Regular Play", "From Corner", "From Free Kick" |
| `duration` | Duration of the event in seconds |
| `under_pressure` | Boolean — was the player under pressure |
| `counterpress` | Boolean — was this a counterpress action |
| **Pass fields** | |
| `pass_end_location` | [x, y] where the pass ended |
| `pass_length`, `pass_angle` | Pass metrics |
| `pass_body_part` | "Right Foot", "Left Foot", "Head" |
| `pass_height` | "Ground Pass", "High Pass", "Low Pass" |
| `pass_outcome` | null = complete, "Incomplete", "Out", etc. |
| `pass_type` | "Corner", "Free Kick", "Throw-in", "Goal Kick", etc. |
| `pass_cross` | Boolean |
| `pass_through_ball` | Boolean |
| `pass_switch` | Boolean |
| `pass_goal_assist` | Boolean |
| `pass_shot_assist` | Boolean |
| `pass_recipient`, `pass_recipient_id` | Target player |
| `pass_pass_cluster_label` | StatsBomb pass cluster category |
| `pass_pass_success_probability` | ML-predicted completion probability |
| `pass_xclaim` | Expected claim value |
| **Shot fields** | |
| `shot_statsbomb_xg` | Expected goals value |
| `shot_outcome` | "Goal", "Saved", "Off T", "Blocked", "Wayward", "Post" |
| `shot_technique` | "Normal", "Volley", "Half Volley", "Lob", "Overhead Kick" |
| `shot_body_part` | "Right Foot", "Left Foot", "Head" |
| `shot_type` | "Open Play", "Free Kick", "Penalty", "Corner" |
| `shot_end_location` | [x, y, z] where the shot ended |
| `shot_freeze_frame` | JSON array of player positions at shot time |
| `shot_first_time` | Boolean |
| `shot_one_on_one` | Boolean |
| `shot_shot_execution_xg` | Execution quality xG |
| `shot_gk_positioning_xg_suppression` | GK positioning effect on xG |
| **OBV (On-Ball Value) fields** | |
| `obv_for_before`, `obv_for_after`, `obv_for_net` | OBV for the acting team |
| `obv_against_before`, `obv_against_after`, `obv_against_net` | OBV against |
| `obv_total_net` | Net OBV of the action |
| **Other event types** | |
| `dribble_outcome` | "Complete" or "Incomplete" |
| `duel_type`, `duel_outcome` | Duel details |
| `foul_committed_card` | "Yellow Card", "Red Card" |
| `interception_outcome` | Interception result |
| `carry_end_location` | [x, y] where the carry ended |
| `clearance_body_part` | Clearance details |
| `goalkeeper_type` | GK action type |

---

### 4. Lineups

Player participation and formations for a match.

```python
lineups = sb.lineups(match_id=4007731, creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v5/lineups/{match_id}`

**Returns:** Dictionary of `{team_name: DataFrame}`. Two keys, one per team.

```python
teams = list(lineups.keys())        # e.g. ["Córdoba CF", "Almería"]
home_lineup = lineups[teams[0]]      # DataFrame
away_lineup = lineups[teams[1]]      # DataFrame
```

**Lineup DataFrame columns:**

| Column | Description |
|--------|-------------|
| `player_id` | Unique player ID |
| `player_name` | Full name |
| `player_nickname` | Short name (may be null) |
| `jersey_number` | Shirt number |
| `country` | Nationality (JSON object) |
| `birth_date` | Date of birth |
| `player_gender` | "male" / "female" |
| `player_height` | Height in cm |
| `player_weight` | Weight in kg |
| `positions` | JSON — list of positions played with from/to times |
| `formations` | JSON — formation info |
| `events` | JSON — cards, substitutions |
| `stats` | JSON — HOPS ratings, lineup summaries |

---

### 5. Player Match Stats (Aggregated)

Pre-aggregated per-player metrics for a single match.

```python
player_stats = sb.player_match_stats(match_id=4007731, creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v5/matches/{match_id}/player-stats`

**Returns:** DataFrame with one row per player who appeared in the match (typically 28-36 rows).

**Key columns (170+ total):**

| Column | Description |
|--------|-------------|
| `player_id`, `player_name` | Player identifiers |
| `team_id`, `team_name` | Team identifiers |
| `match_id` | Match reference |
| `player_match_minutes` | Minutes played |
| `player_match_goals` | Goals scored |
| `player_match_assists` | Assists |
| `player_match_np_xg` | Non-penalty xG |
| `player_match_np_shots` | Non-penalty shots |
| `player_match_xa` | Expected assists |
| `player_match_op_xa` | Open-play xA |
| `player_match_key_passes` | Key passes |
| `player_match_passes` | Total passes |
| `player_match_successful_passes` | Completed passes |
| `player_match_passing_ratio` | Pass completion % |
| `player_match_forward_passes` | Forward passes |
| `player_match_op_passes_into_box` | Open-play passes into box |
| `player_match_crosses_into_box` | Crosses into box |
| `player_match_through_balls` | Through balls |
| `player_match_long_balls` | Long balls |
| `player_match_touches` | Total touches |
| `player_match_touches_inside_box` | Touches in opponent's box |
| `player_match_dribbles` | Dribble attempts |
| `player_match_pressures` | Pressures applied |
| `player_match_pressure_regains` | Possession regained from pressure |
| `player_match_tackles` | Tackles |
| `player_match_interceptions` | Interceptions |
| `player_match_clearances` | Clearances |
| `player_match_aerials` | Aerial duels |
| `player_match_fouls` | Fouls committed |
| `player_match_fouls_won` | Fouls won |
| `player_match_obv` | Total on-ball value |
| `player_match_obv_pass` | OBV from passes |
| `player_match_obv_shot` | OBV from shots |
| `player_match_obv_defensive_action` | OBV from defensive actions |
| `player_match_obv_dribble_carry` | OBV from dribbles and carries |
| `player_match_obv_gk` | OBV from GK actions |
| `player_match_op_xgchain` | Open-play xG chain |
| `player_match_op_xgbuildup` | Open-play xG buildup |
| `player_match_deep_completions` | Passes completed within 20m of goal |
| `player_match_deep_progressions` | Carries/passes entering final 20m |
| **Goalkeeper-specific** | |
| `player_match_np_psxg` | Post-shot xG faced |
| `player_match_goals_conceded` | Goals let in |
| `player_match_gsaa` | Goals saved above average |
| `player_match_save_ratio` | Save percentage |
| **360 data (where available)** | |
| `player_match_ball_receipts_in_space_*` | Receipts in space (2m/5m/10m) |

---

### 6. Team Match Stats (Aggregated)

Pre-aggregated team-level metrics for a single match.

```python
team_stats = sb.team_match_stats(match_id=4007731, creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v2/matches/{match_id}/team-stats`

**Returns:** DataFrame with 2 rows (one per team), 184 columns.

**Key columns:**

| Column | Description |
|--------|-------------|
| `team_id`, `team_name` | Team identifiers |
| `opposition_id`, `opposition_name` | Opponent identifiers |
| `team_match_possession` | Possession % |
| `team_match_passes` / `team_match_successful_passes` | Pass volume |
| `team_match_np_shots` | Non-penalty shots |
| `team_match_np_xg` | Non-penalty xG |
| `team_match_np_xg_per_shot` | Shot quality |
| `team_match_op_shots` | Open-play shots |
| `team_match_op_xg` | Open-play xG |
| `team_match_sp_xg` | Set-piece xG |
| `team_match_goals` | Goals scored |
| `team_match_goals_conceded` | Goals conceded |
| `team_match_gd` / `team_match_xgd` | Goal/xG difference |
| `team_match_directness` | Directness score |
| `team_match_ppda` | Passes per defensive action (pressing) |
| `team_match_defensive_distance` | Average defensive line height |
| `team_match_pressures` | Total pressures |
| `team_match_counterpressures` | Counterpresses |
| `team_match_aggressive_actions` | Aggressive actions |
| `team_match_corners` / `team_match_corners_conceded` | Corner counts |
| `team_match_corner_xg` | xG from corners |
| `team_match_completed_dribbles` | Successful dribbles |
| `team_match_obv` | Total team OBV |
| `team_match_obv_pass` | OBV from passing |
| `team_match_obv_shot` | OBV from shots |
| `team_match_deep_completions` | Deep completions |
| `team_match_deep_progressions` | Deep progressions |
| `team_match_ball_in_play_time` | Ball in play (seconds) |
| `team_match_yellow_cards` / `team_match_red_cards` | Cards |

---

### 7. Player Season Stats (Aggregated)

Season-level aggregated stats for all players in a competition-season. Rates are per 90 minutes.

```python
player_season = sb.player_season_stats(competition_id=42, season_id=318, creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v4/competitions/{competition_id}/seasons/{season_id}/player-stats`

**Returns:** DataFrame with one row per player (224 columns).

**Key columns (all per-90 unless noted):**

| Column | Description |
|--------|-------------|
| `player_id`, `player_name` | Player identifiers |
| `team_id`, `team_name` | Team |
| `player_season_minutes` | Total minutes played |
| `player_season_90s_played` | 90s equivalent |
| `player_season_appearances` | Matches played |
| `player_season_np_xg_90` | Non-penalty xG per 90 |
| `player_season_xa_90` | xA per 90 |
| `player_season_obv_90` | OBV per 90 |
| `player_season_passes_90` | Passes per 90 |
| `player_season_passing_ratio` | Pass completion % |
| `player_season_touches_inside_box_90` | Box touches per 90 |
| `player_season_pressures_90` | Pressures per 90 |
| `player_season_dribbles_90` | Dribbles per 90 |
| `player_season_tackles_90` | Tackles per 90 |
| `player_season_interceptions_90` | Interceptions per 90 |
| `player_season_aerial_ratio` | Aerial duel win % |
| `player_season_deep_completions_90` | Deep completions per 90 |
| `player_season_carry_length` | Average carry distance |
| **Player metadata** | |
| `birth_date` | Date of birth |
| `player_height` | Height in cm |
| `country_id` | Nationality ID |

**Use cases:** Season leaderboards, player comparisons, scouting models.

---

### 8. Team Season Stats (Aggregated)

Season-level aggregated stats for all teams. Rates are per game.

```python
team_season = sb.team_season_stats(competition_id=42, season_id=318, creds=CREDS)
```

**REST equivalent:** `GET https://data.statsbomb.com/api/v3/competitions/{competition_id}/seasons/{season_id}/team-stats`

**Returns:** DataFrame with one row per team (181 columns). All `_pg` columns are per-game averages.

**Key columns:**

| Column | Description |
|--------|-------------|
| `team_id`, `team_name` | Team identifiers |
| `team_season_matches` | Games played |
| `team_season_gd` | Total goal difference |
| `team_season_xgd` | Total xG difference |
| `team_season_possession` | Average possession % |
| `team_season_np_xg_pg` | Non-penalty xG per game |
| `team_season_np_xg_conceded_pg` | NP xG conceded per game |
| `team_season_directness` | Directness score |
| `team_season_ppda` | PPDA (pressing intensity) |
| `team_season_defensive_distance` | Defensive line height |
| `team_season_obv_pg` | OBV per game |
| `team_season_goals_pg` | Goals per game |
| `team_season_goals_conceded_pg` | Goals conceded per game |
| `team_season_corners_pg` | Corners per game |
| `team_season_aggressive_actions_pg` | Aggressive actions per game |
| `team_season_deep_completions_pg` | Deep completions per game |
| `team_season_deep_progressions_pg` | Deep progressions per game |

**Use cases:** Team rankings, tactical profiling, league-wide comparisons.

---

## Known IDs

| Entity | ID | Notes |
|--------|-----|-------|
| La Liga 2 (Spain) | `competition_id=42` | 3 seasons available (2023-2026) |
| NB1 (Hungary) | `competition_id=1522` | |
| Season 2025/2026 | `season_id=318` | Current season |
| Season 2024/2025 | `season_id=317` | |
| Season 2023/2024 | `season_id=281` | |

---

## Typical Workflow

```python
from statsbombpy import sb

CREDS = {"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"}

# 1. Find competitions and seasons
comps = sb.competitions(creds=CREDS)

# 2. Get matches for a competition-season
matches = sb.matches(competition_id=42, season_id=318, creds=CREDS)

# 3. For each match, get detailed data
for _, match in matches.iterrows():
    mid = match.match_id

    events       = sb.events(match_id=mid, creds=CREDS)               # raw event stream
    lineups      = sb.lineups(match_id=mid, creds=CREDS)              # dict of DataFrames
    player_stats = sb.player_match_stats(match_id=mid, creds=CREDS)   # aggregated player stats
    team_stats   = sb.team_match_stats(match_id=mid, creds=CREDS)     # aggregated team stats

# 4. Get season-level aggregates (no need to loop matches)
player_season = sb.player_season_stats(competition_id=42, season_id=318, creds=CREDS)
team_season   = sb.team_season_stats(competition_id=42, season_id=318, creds=CREDS)
```

---

## Tips and Gotchas

1. **Future matches return empty data.** Always filter by `match_date <= today` before calling match-level endpoints.

2. **`sb.events()` can raise `ValueError: No objects to concatenate`** for matches with no event data (future or unavailable matches). Wrap in try/except.

3. **`sb.lineups()` returns a dict, not a DataFrame.** Access teams with `lineups["Team Name"]`.

4. **`FutureWarning` spam from pandas.** Suppress with:
   ```python
   import warnings
   warnings.filterwarnings("ignore", category=FutureWarning)
   ```

5. **`statsbombpy` is NOT thread-safe.** If parallelizing, use `ProcessPoolExecutor` (separate processes), not `ThreadPoolExecutor`. Threads will cause segfaults.

6. **Rate limiting:** The API does not enforce strict rate limits for normal usage, but connection resets can occur under heavy parallel load. Use retry logic with exponential backoff on errors.

7. **Column naming conventions:**
   - Match-level player stats: `player_match_*` (raw counts)
   - Season-level player stats: `player_season_*_90` (per-90 rates)
   - Match-level team stats: `team_match_*` (raw counts)
   - Season-level team stats: `team_season_*_pg` (per-game averages)

8. **OBV (On-Ball Value):** StatsBomb's proprietary possession value model. Positive = good for acting team. Available on events, player stats, and team stats.

9. **xG fields:** `shot_statsbomb_xg` on events, `player_match_np_xg` on player stats, `team_match_np_xg` on team stats. All exclude penalties unless otherwise noted.

10. **Converting season per-90 rates back to totals:**
    ```python
    raw_total = per_90_value * (player_season_minutes / 90)
    ```
