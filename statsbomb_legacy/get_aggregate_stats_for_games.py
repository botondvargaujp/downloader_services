import os
import pandas as pd
import numpy as np
mathces_folders = os.listdir("matches")
for match_folder in mathces_folders:
    if len(os.listdir(f"matches/{match_folder}")) == 0:
        continue
    match_date = match_folder
    palyer_stats_match = pd.read_csv(f"matches/{match_folder}/player_match_stats.csv")
    ujpest_stats = palyer_stats_match[palyer_stats_match.team_name == "Ujpest"]
    opponent_stats = palyer_stats_match[palyer_stats_match.team_name != "Ujpest"]
    opp_team_name = opponent_stats.team_name.unique()[0]
    team_match_stats = pd.read_csv(f"matches/{match_folder}/team_match_stats.csv")
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
    match_stats_df = pd.read_csv(f"matches/{match_folder}/team_match_stats.csv")
    # Drop columns from previous runs to allow clean re-merge
    enriched_cols = ["match_date", "team_touches_in_opp_box", "team_match_op_f3_passes",
                     "team_match_f3_forward_passes", "possession_count", "passes_per_possession"]
    match_stats_df = match_stats_df.drop(columns=[c for c in enriched_cols if c in match_stats_df.columns], errors="ignore")
    match_stats_df = pd.merge(match_stats_df, df, on="team_name", how="left")
    match_events = pd.read_csv(f"matches/{match_folder}/events.csv")
    possession_counts = (
        match_events["possession_team"]
        .ne(match_events["possession_team"].shift(1))
        .groupby(match_events["possession_team"])
        .sum()
    )
    df = pd.DataFrame()
    df["team_name"] = possession_counts.index
    df["possession_count"] = possession_counts.values
    match_stats_df = pd.merge(match_stats_df, df, on="team_name", how="left")
    match_stats_df["passes_per_possession"] = match_stats_df["team_match_passes"] / match_stats_df["possession_count"]


    match_stats_df.to_csv(f"matches/{match_folder}/team_match_stats.csv")

# Compute per-team touches inside box per game (same logic as match: sum raw player touches, then per game)
player_season_stats = pd.read_csv("seasonal_stats/player_season_stats.csv")
team_season_stats = pd.read_csv("seasonal_stats/team_season_stats.csv")

# Convert per-90 rate back to raw season totals, then sum per team
player_season_stats["_raw_touches"] = (
    player_season_stats["player_season_touches_inside_box_90"]
    * player_season_stats["player_season_minutes"] / 90
)
total_touches_by_team = player_season_stats.groupby("team_name")["_raw_touches"].sum()

# Divide by number of matches to get per-game average (comparable to match totals)
matches_by_team = team_season_stats.set_index("team_name")["team_season_matches"]
avg_touches_by_team = (total_touches_by_team / matches_by_team).rename("team_season_avg_touches_inside_box_90")
# Drop column if it already exists to avoid duplicates on re-run
if "team_season_avg_touches_inside_box_90" in team_season_stats.columns:
    team_season_stats = team_season_stats.drop(columns=["team_season_avg_touches_inside_box_90"])
team_season_stats = team_season_stats.merge(
    avg_touches_by_team, on="team_name", how="left"
)
team_season_stats.to_csv("seasonal_stats/team_season_stats.csv", index=False)