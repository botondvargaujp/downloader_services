"""Fetch step of the weekly StatsBomb pipeline.

Scans the NB1 (Hungary) season for Ujpest matches whose StatsBomb data has
actually been published, then downloads only the games we don't already have.
Idempotent: re-running only fetches new/incomplete games.

Run standalone with `python statsbomb_data_downloader.py`, or import
`download_new_games()` / `download_season_stats()` from the orchestrator.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from statsbombpy import sb

# Anchor all data paths to the repo root (parent of statsbomb_legacy/) so the
# job works no matter what directory launchd/cron invokes it from.
ROOT = Path(__file__).resolve().parent.parent
MATCHES_DIR = ROOT / "matches"
SEASONAL_DIR = ROOT / "seasonal_stats"

# Credentials are loaded from a git-ignored .env at the repo root (never committed).
# See .env.example for the required keys.
load_dotenv(ROOT / ".env")


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"Missing {key}. Copy .env.example to .env at the repo root and fill in "
            "your StatsBomb credentials."
        )
    return value


CREDS = {
    "user": _require("STATSBOMB_USER"),
    "passwd": _require("STATSBOMB_PASSWD"),
}

COMPETITION_ID = 1522   # NB1 (Hungary)
SEASON_ID = 351         # 2025/26
TEAM = "Ujpest"

REQUIRED_FILES = {
    "events.csv",
    "opponent_lineup.csv",
    "player_match_stats.csv",
    "team_match_stats.csv",
    "ujpest_lineup.csv",
}


def available_ujpest_matches():
    """Return Ujpest matches that StatsBomb has published data for, oldest first."""
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID, creds=CREDS)
    matches = matches[(matches.home_team == TEAM) | (matches.away_team == TEAM)]

    # Only keep games with data actually available. `match_status == "available"`
    # is StatsBomb's canonical signal; fall back to "has a final score" if the
    # column is ever missing.
    if "match_status" in matches.columns:
        matches = matches[matches.match_status == "available"]
    else:
        matches = matches[matches.home_score.notna()]

    return matches.sort_values(by="match_date")


def download_new_games() -> int:
    """Download every available Ujpest game we don't already have. Returns count fetched."""
    MATCHES_DIR.mkdir(exist_ok=True)
    matches = available_ujpest_matches()

    skipped = 0
    downloaded = 0
    for _, row in matches.iterrows():
        match_dir = MATCHES_DIR / str(row.match_date)

        if match_dir.is_dir() and REQUIRED_FILES.issubset(set(os.listdir(match_dir))):
            skipped += 1
            continue

        match_dir.mkdir(parents=True, exist_ok=True)
        match_id = row.match_id
        print(f"Downloading {row.home_team} vs {row.away_team} ({row.match_date})...")

        lineups = sb.lineups(match_id=match_id, creds=CREDS)
        events = sb.events(match_id=match_id, creds=CREDS)
        player_match_stats = sb.player_match_stats(match_id=match_id, creds=CREDS)
        team_match_stats = sb.team_match_stats(match_id=match_id, creds=CREDS)

        teams = list(lineups.keys())
        opponent_team = teams[1] if teams[0] == TEAM else teams[0]

        lineups.get(TEAM).to_csv(match_dir / "ujpest_lineup.csv", index=False)
        lineups.get(opponent_team).to_csv(match_dir / "opponent_lineup.csv", index=False)
        events.to_csv(match_dir / "events.csv", index=False)
        player_match_stats.to_csv(match_dir / "player_match_stats.csv", index=False)
        team_match_stats.to_csv(match_dir / "team_match_stats.csv", index=False)
        downloaded += 1

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped (already complete)")
    return downloaded


def download_season_stats() -> None:
    """Refresh season-level team/player stats and the derived avg-touches column."""
    SEASONAL_DIR.mkdir(exist_ok=True)

    team_season_stats = sb.team_season_stats(
        competition_id=COMPETITION_ID, season_id=SEASON_ID, creds=CREDS
    )
    player_season_stats = sb.player_season_stats(
        competition_id=COMPETITION_ID, season_id=SEASON_ID, creds=CREDS
    )

    # Per-team average of player_season_touches_inside_box_90.
    avg_touches_by_team = (
        player_season_stats
        .groupby("team_name")["player_season_touches_inside_box_90"]
        .mean()
        .rename("team_season_avg_touches_inside_box_90")
    )
    team_season_stats = team_season_stats.merge(avg_touches_by_team, on="team_name", how="left")

    team_season_stats.to_csv(SEASONAL_DIR / "team_season_stats.csv", index=False)
    player_season_stats.to_csv(SEASONAL_DIR / "player_season_stats.csv", index=False)


if __name__ == "__main__":
    download_new_games()
    download_season_stats()
