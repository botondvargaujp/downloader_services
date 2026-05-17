from statsbombpy import sb

creds = {"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"}
competitions = sb.competitions(creds=creds)


hungary_competitions = competitions[competitions.country_name == "Hungary"]


nb1 = 1522
season_nb1_25_26= 318

matches = sb.matches(competition_id=nb1, season_id=season_nb1_25_26, creds=creds)
matches = matches[(matches.home_team == "Ujpest") | (matches.away_team == "Ujpest")].sort_values(by="match_date")
mathces = matches[matches.data_version == "1.1.0"]


import os

REQUIRED_FILES = {"events.csv", "opponent_lineup.csv", "player_match_stats.csv",
                  "team_match_stats.csv", "ujpest_lineup.csv"}

skipped = 0
downloaded = 0

for idx, row in matches.iterrows():
    match_dir = f"matches/{row.match_date}"

    if os.path.isdir(match_dir) and REQUIRED_FILES.issubset(set(os.listdir(match_dir))):
        skipped += 1
        continue

    os.makedirs(match_dir, exist_ok=True)
    match_id = row.match_id
    print(f"Downloading {row.home_team} vs {row.away_team} ({row.match_date})...")

    lineups = sb.lineups(match_id=match_id, creds=creds)
    events = sb.events(match_id=match_id, creds=creds)
    player_match_stats = sb.player_match_stats(match_id=match_id, creds=creds)
    team_match_stats = sb.team_match_stats(match_id=match_id, creds=creds)

    teams = list(lineups.keys())
    if teams[0] == "Ujpest":
        opponent_team = teams[1]
    else:
        opponent_team = teams[0]

    ujpest_lineup = lineups.get("Ujpest")
    opponent_lineup = lineups.get(opponent_team)

    ujpest_lineup.to_csv(f"{match_dir}/ujpest_lineup.csv", index=False)
    opponent_lineup.to_csv(f"{match_dir}/opponent_lineup.csv", index=False)
    events.to_csv(f"{match_dir}/events.csv", index=False)
    player_match_stats.to_csv(f"{match_dir}/player_match_stats.csv", index=False)
    team_match_stats.to_csv(f"{match_dir}/team_match_stats.csv", index=False)
    downloaded += 1

print(f"\nDone: {downloaded} downloaded, {skipped} skipped (already complete)")


team_season_stats = sb.team_season_stats(competition_id=nb1, season_id=season_nb1_25_26, creds=creds)
player_season_stats = sb.player_season_stats(competition_id=nb1, season_id=season_nb1_25_26, creds=creds)

# Compute per-team average of player_season_touches_inside_box_90
avg_touches_by_team = (
    player_season_stats
    .groupby("team_name")["player_season_touches_inside_box_90"]
    .mean()
    .rename("team_season_avg_touches_inside_box_90")
)
print(avg_touches_by_team.columns)
team_season_stats = team_season_stats.merge(
    avg_touches_by_team, on="team_name", how="left"
)
print(team_season_stats.columns)
team_season_stats.to_csv(f"seasonal_stats/team_season_stats.csv", index=False)
player_season_stats.to_csv(f"seasonal_stats/player_season_stats.csv", index=False)