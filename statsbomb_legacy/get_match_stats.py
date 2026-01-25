from statsbombpy import sb
creds = {"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"}
Competitions = sb.competitions(creds={"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"})


competitions = Competitions[Competitions.competition_gender == "male"]
season_id = 318
competition_id = 1522
season_name = "2025/2026"

matches = sb.matches(season_id=season_id, competition_id=competition_id,creds=creds)

print(matches.shape)
print(matches.columns)
print(matches[(matches.away_team == "Ujpest") | (matches.home_team == "Ujpest")][["match_id", "away_team", "home_team", "match_date"]].sort_values(by="match_date"))
match_ids = [4003626, 4003632, 4003641, 4003644, 4003652, 4003656, 4003664] 


for match_id in match_ids:
    match_stats = sb.team_match_stats(match_id=match_id, creds=creds)
    match_stats.to_csv(f"match_data/stats_{match_id}.csv")

    events = sb.events(match_id=match_id, creds=creds)
    events.to_csv(f"events_{match_id}.csv")


team_season_stats = sb.team_season_stats(season_id=season_id, competition_id=competition_id, creds=creds)
team_season_stats.to_csv(f"team_season_stats_{season_id}_{competition_id}.csv")
