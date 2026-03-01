from statsbombpy import sb

creds = {"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"}
competitions = sb.competitions(creds=creds)


hungary_competitions = competitions[competitions.country_name == "Hungary"]


nb1 = 1522
season_nb1_25_26= 318

matches = sb.matches(competition_id=nb1, season_id=season_nb1_25_26, creds=creds)
matches = matches[(matches.home_team == "Ujpest") | (matches.away_team == "Ujpest")].sort_values(by="match_date")
mathces = matches[matches.data_version == "1.1.0"]


import json
import os 

for idx,row in matches.iterrows():
 
    match_id = row.match_id
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

    ujpest_lineup.to_csv(f"matches/{row.match_date}/ujpest_lineup.csv", index=False)
    opponent_lineup.to_csv(f"matches/{row.match_date}/opponent_lineup.csv", index=False)
    events.to_csv(f"matches/{row.match_date}/events.csv", index=False)
    player_match_stats.to_csv(f"matches/{row.match_date}/player_match_stats.csv", index=False)
    team_match_stats.to_csv(f"matches/{row.match_date}/team_match_stats.csv", index=False)
    os.makedirs(f"matches/{row.match_date}", exist_ok=True) 


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