"""Enrich step of the weekly StatsBomb pipeline.

For each downloaded match folder, derives extra team-level metrics (touches in
the opponent box, F3 forward passes, possession count, passes per possession)
and writes them back into team_match_stats.csv. Also recomputes the season-level
per-game touches-inside-box average.

Run standalone with `python get_aggregate_stats_for_games.py`, or import
`enrich()` from the orchestrator.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MATCHES_DIR = ROOT / "matches"
SEASONAL_DIR = ROOT / "seasonal_stats"


def enrich() -> None:
    """Recompute derived per-match and per-season aggregate stats in place."""
    for match_folder in os.listdir(MATCHES_DIR):
        folder_path = MATCHES_DIR / match_folder
        if not folder_path.is_dir() or len(os.listdir(folder_path)) == 0:
            continue

        match_date = match_folder
        player_stats_match = pd.read_csv(folder_path / "player_match_stats.csv")
        ujpest_stats = player_stats_match[player_stats_match.team_name == "Ujpest"]
        opponent_stats = player_stats_match[player_stats_match.team_name != "Ujpest"]
        opp_team_name = opponent_stats.team_name.unique()[0]

        ujpest_touches_in_opp_box = ujpest_stats["player_match_touches_inside_box"].sum()
        opponent_touches_in_opp_box = opponent_stats["player_match_touches_inside_box"].sum()
        ujpest_match_op_f3_passes = ujpest_stats["player_match_op_f3_forward_passes"].sum()
        opponent_match_op_f3_passes = opponent_stats["player_match_op_f3_forward_passes"].sum()

        df = pd.DataFrame({
            "match_date": [match_date, match_date],
            "team_name": ["Ujpest", opp_team_name],
            "team_touches_in_opp_box": [ujpest_touches_in_opp_box, opponent_touches_in_opp_box],
            "team_match_op_f3_passes": [ujpest_match_op_f3_passes, opponent_match_op_f3_passes],
            "team_match_f3_forward_passes": [ujpest_match_op_f3_passes, opponent_match_op_f3_passes],
        })

        match_stats_df = pd.read_csv(folder_path / "team_match_stats.csv")
        # Drop any leftover unnamed index column and columns from previous runs
        # so the merge stays clean and idempotent.
        match_stats_df = match_stats_df.loc[:, ~match_stats_df.columns.str.startswith("Unnamed")]
        enriched_cols = ["match_date", "team_touches_in_opp_box", "team_match_op_f3_passes",
                         "team_match_f3_forward_passes", "possession_count", "passes_per_possession"]
        match_stats_df = match_stats_df.drop(
            columns=[c for c in enriched_cols if c in match_stats_df.columns], errors="ignore"
        )
        match_stats_df = pd.merge(match_stats_df, df, on="team_name", how="left")

        match_events = pd.read_csv(folder_path / "events.csv")
        possession_counts = (
            match_events["possession_team"]
            .ne(match_events["possession_team"].shift(1))
            .groupby(match_events["possession_team"])
            .sum()
        )
        poss_df = pd.DataFrame({
            "team_name": possession_counts.index,
            "possession_count": possession_counts.values,
        })
        match_stats_df = pd.merge(match_stats_df, poss_df, on="team_name", how="left")
        match_stats_df["passes_per_possession"] = (
            match_stats_df["team_match_passes"] / match_stats_df["possession_count"]
        )

        match_stats_df.to_csv(folder_path / "team_match_stats.csv", index=False)

    # Season-level: per-team touches inside box per game (same logic as per match:
    # sum raw player touches, then divide by games played).
    player_season_stats = pd.read_csv(SEASONAL_DIR / "player_season_stats.csv")
    team_season_stats = pd.read_csv(SEASONAL_DIR / "team_season_stats.csv")

    player_season_stats["_raw_touches"] = (
        player_season_stats["player_season_touches_inside_box_90"]
        * player_season_stats["player_season_minutes"] / 90
    )
    total_touches_by_team = player_season_stats.groupby("team_name")["_raw_touches"].sum()

    matches_by_team = team_season_stats.set_index("team_name")["team_season_matches"]
    avg_touches_by_team = (
        (total_touches_by_team / matches_by_team)
        .rename("team_season_avg_touches_inside_box_90")
    )
    if "team_season_avg_touches_inside_box_90" in team_season_stats.columns:
        team_season_stats = team_season_stats.drop(columns=["team_season_avg_touches_inside_box_90"])
    team_season_stats = team_season_stats.merge(avg_touches_by_team, on="team_name", how="left")
    team_season_stats.to_csv(SEASONAL_DIR / "team_season_stats.csv", index=False)


if __name__ == "__main__":
    enrich()
