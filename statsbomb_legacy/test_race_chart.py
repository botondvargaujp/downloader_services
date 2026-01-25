import pandas as pd
import plotly.graph_objects as go

# -----------------------
# CONFIG
# -----------------------
CSV_PATH = "../match_data/events_4003652.csv"
UJPEST_NAME = "Ujpest"

COLOR_UJPEST = "#6A0DAD"
COLOR_OTHER = "#C94A4A"

# -----------------------
# LOAD & PREP
# -----------------------
df = pd.read_csv(CSV_PATH)

# Sort by period first, then minute and second to ensure proper chronological order
df = df.sort_values(["period", "minute", "second"], na_position="last").reset_index(drop=True)

# Calculate time as continuous from start
df["time"] = df["minute"] + df.get("second", 0).fillna(0) / 60

# Find the last event time in the data
MATCH_END_MINUTE = df["time"].max()

# -----------------------
# TEAM DETECTION
# -----------------------
teams = df["team"].dropna().unique().tolist()

if UJPEST_NAME not in teams or len(teams) != 2:
    raise ValueError(f"Expected exactly 2 teams incl. '{UJPEST_NAME}', got {teams}")

other_team = [t for t in teams if t != UJPEST_NAME][0]

# -----------------------
# SHOTS
# -----------------------
shots = df[
    (df["type"] == "Shot") &
    (df["shot_statsbomb_xg"].notna())
].copy()

shots["shot_xg"] = shots["shot_statsbomb_xg"].round(2)

# -----------------------
# MARKERS (Goals, Penalties, Cards, Subs)
# -----------------------
# Goals
goals = shots[shots["shot_outcome"] == "Goal"].copy()

# Penalties (separate from other goals)
penalties = shots[shots["shot_type"] == "Penalty"].copy() if "shot_type" in shots.columns else pd.DataFrame()

# Cards
cards = df[df["foul_committed_card"].notna()].copy()

# Substitutions
subs = df[df["type"] == "Substitution"].copy()

# -----------------------
# STEP BUILDER
# -----------------------
def build_step_series(team_shots):
    """Build step series for cumulative xG race chart starting from minute 0"""
    x = [0]
    y = [0.0]
    player = ["Match Start"]
    action = ["—"]
    xg = ["0.00"]

    cum_xg = 0.0

    for _, r in team_shots.iterrows():
        # flat to shot
        x.append(r["time"])
        y.append(cum_xg)
        player.append(r["player"])
        action.append(r.get("shot_type", "Shot"))
        xg.append(f"{r['shot_xg']:.2f}")

        # vertical jump
        cum_xg = round(cum_xg + r["shot_xg"], 2)
        x.append(r["time"])
        y.append(cum_xg)
        player.append(r["player"])
        action.append(r.get("shot_type", "Shot"))
        xg.append(f"{r['shot_xg']:.2f}")

    # extend to last event time
    x.append(MATCH_END_MINUTE)
    y.append(cum_xg)
    player.append("Match End")
    action.append("—")
    xg.append("0.00")

    return pd.DataFrame({
        "time": x,
        "cum_xg": y,
        "player": player,
        "action": action,
        "xg": xg
    })

# -----------------------
# BUILD SERIES
# -----------------------
series = {
    UJPEST_NAME: build_step_series(shots[shots["team"] == UJPEST_NAME]),
    other_team: build_step_series(shots[shots["team"] == other_team])
}

# -----------------------
# PLOT
# -----------------------
fig = go.Figure()

def add_trace(df, team, color):
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["cum_xg"],
        mode="lines",
        name=team,
        line=dict(color=color, width=4),
        hovertemplate=(
            "<b>%{y:.2f} xG</b><br>"
            "Player: %{customdata[0]}<br>"
            "Action: %{customdata[1]}<br>"
            "Shot xG: %{customdata[2]}<extra></extra>"
        ),
        customdata=df[["player", "action", "xg"]].values
    ))

add_trace(series[UJPEST_NAME], UJPEST_NAME, COLOR_UJPEST)
add_trace(series[other_team], other_team, COLOR_OTHER)

# -----------------------
# ADD MARKERS
# -----------------------
def add_markers(events_df, team, color, symbol, size, label):
    """Add markers for specific events (goals, cards, subs)"""
    if len(events_df) == 0:
        return
    
    team_events = events_df[events_df["team"] == team].copy()
    if len(team_events) == 0:
        return
    
    # For each event, find the cumulative xG at that time
    y_values = []
    for _, event in team_events.iterrows():
        event_time = event["time"]
        # Get cumulative xG for this team at this time
        team_series = series[team]
        cum_xg_at_time = team_series[team_series["time"] <= event_time]["cum_xg"].iloc[-1] if len(team_series[team_series["time"] <= event_time]) > 0 else 0
        y_values.append(cum_xg_at_time)
    
    fig.add_trace(go.Scatter(
        x=team_events["time"],
        y=y_values,
        mode="markers",
        name=f"{team} {label}",
        marker=dict(
            symbol=symbol,
            size=size,
            color=color,
            line=dict(width=2, color="white")
        ),
        hovertemplate=(
            f"<b>{label}</b><br>"
            "Player: %{customdata[0]}<br>"
            "Minute: %{x:.1f}<extra></extra>"
        ),
        customdata=team_events[["player"]].values,
        showlegend=True
    ))

# Add goals
for team in [UJPEST_NAME, other_team]:
    color = COLOR_UJPEST if team == UJPEST_NAME else COLOR_OTHER
    add_markers(goals, team, color, "star", 20, "Goal")

# Add penalties
for team in [UJPEST_NAME, other_team]:
    color = COLOR_UJPEST if team == UJPEST_NAME else COLOR_OTHER
    add_markers(penalties, team, color, "circle", 15, "Penalty")

# Add yellow cards
for team in [UJPEST_NAME, other_team]:
    color = "yellow"
    yellow_cards = cards[cards["foul_committed_card"] == "Yellow Card"]
    add_markers(yellow_cards, team, color, "square", 12, "Yellow Card")

# Add red cards
for team in [UJPEST_NAME, other_team]:
    color = "red"
    red_cards = cards[cards["foul_committed_card"] == "Red Card"]
    add_markers(red_cards, team, color, "square", 12, "Red Card")

# Add substitutions
for team in [UJPEST_NAME, other_team]:
    color = COLOR_UJPEST if team == UJPEST_NAME else COLOR_OTHER
    add_markers(subs, team, color, "diamond", 12, "Substitution")

# -----------------------
# LAYOUT
# -----------------------
fig.update_layout(
    title=dict(text="Cumulative xG Race", x=0.02),
    xaxis=dict(
        title="Minute",
        range=[0, MATCH_END_MINUTE],
        showgrid=True,
        gridcolor="rgba(0,0,0,0.05)"
    ),
    yaxis=dict(
        title="xG",
        showgrid=True,
        gridcolor="rgba(0,0,0,0.05)"
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0
    ),
    margin=dict(l=60, r=40, t=80, b=60)
)

fig.show()
