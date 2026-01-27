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