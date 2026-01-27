import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import glob
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import tempfile
from PIL import Image as PILImage

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(
    page_title="Match Report Dashboard",
    layout="wide",
)

# Ujpest colors (our team)
UJPEST_COLOR = "#6A0DAD"  # Purple
UJPEST_LIGHT = "#9B4FD4"  # Lighter purple

# Opposition colors
OPPOSITION_COLOR = "#95A5A6"  # Gray
OPPOSITION_LIGHT = "#BDC3C7"  # Light gray

BACKGROUND_LIGHT = "#F8F9FA"

# -------------------------
# LOAD DATA
# -------------------------
@st.cache_data
def load_data():
    """Load all match stats from the matches folder"""
    # Get all team_match_stats.csv files from matches subfolders
    matches_path = os.path.join(os.path.dirname(__file__), "matches", "*", "team_match_stats.csv")
    csv_files = glob.glob(matches_path)
    
    # Load and combine all CSV files
    dfs = []
    for file in csv_files:
        df_temp = pd.read_csv(file)
        # Extract match date from folder name
        match_date = os.path.basename(os.path.dirname(file))
        df_temp['match_date'] = match_date
        dfs.append(df_temp)
    
    # Combine all dataframes
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        st.error("No match data files found in matches/ folder")
        return pd.DataFrame()

@st.cache_data
def load_team_season_stats():
    """Load team season stats for comparison"""
    # Look for team_season_stats_*.csv in match_data folder
    data_path = os.path.join(os.path.dirname(__file__), "match_data", "team_season_stats_*.csv")
    csv_files = glob.glob(data_path)
    
    if csv_files:
        # Load the first matching file (should be one per season)
        df = pd.read_csv(csv_files[0])
        return df
    else:
        return pd.DataFrame()

@st.cache_data
def load_events_data(match_date):
    """Load event data for a specific match date"""
    events_path = os.path.join(os.path.dirname(__file__), "matches", match_date, "events.csv")
    if os.path.exists(events_path):
        df_events = pd.read_csv(events_path)
        # Sort by period, minute, second
        df_events = df_events.sort_values(["period", "minute", "second"], na_position="last").reset_index(drop=True)
        # Calculate continuous time
        df_events["time"] = df_events["minute"] + df_events.get("second", 0).fillna(0) / 60
        return df_events
    return None

def parse_starting_xi(events_df):
    """Parse starting XI data from events dataframe"""
    import ast
    
    starting_xi_data = {}
    
    # Filter for Starting XI events
    starting_xi_events = events_df[events_df['type'] == 'Starting XI'].copy()
    
    for _, row in starting_xi_events.iterrows():
        team = row['team']
        tactics_str = row['tactics']
        
        if pd.notna(tactics_str):
            try:
                tactics = ast.literal_eval(tactics_str)
                starting_xi_data[team] = {
                    'formation': tactics['formation'],
                    'lineup': tactics['lineup']
                }
            except:
                pass
    
    return starting_xi_data

def calculate_player_average_positions(events_df, team_name, starting_xi_players):
    """Calculate average pass locations for starting XI players, pass connections, and OBV"""
    import ast
    
    # Get list of starting XI player IDs
    starting_player_ids = [p['player']['id'] for p in starting_xi_players]
    starting_player_names = {p['player']['id']: p['player']['name'] for p in starting_xi_players}
    starting_player_ids_to_names = starting_player_names.copy()
    
    # Filter for pass events by this team's starting XI
    pass_events = events_df[
        (events_df['type'] == 'Pass') &
        (events_df['team'] == team_name) &
        (events_df['player_id'].isin(starting_player_ids))
    ].copy()
    
    player_positions = {}
    pass_connections = {}  # Store pass counts between players
    
    for player_id, player_name in starting_player_names.items():
        player_passes = pass_events[pass_events['player_id'] == player_id]
        
        if len(player_passes) > 0:
            # Parse location data and calculate OBV
            locations = []
            total_obv = 0.0
            for _, row in player_passes.iterrows():
                loc_str = row['location']
                if pd.notna(loc_str):
                    try:
                        loc = ast.literal_eval(loc_str)
                        if len(loc) == 2:
                            locations.append(loc)
                    except:
                        pass
                
                # Sum up OBV for this player's passes
                obv_value = row.get('obv_total_net', 0)
                if pd.notna(obv_value):
                    total_obv += float(obv_value)
                
                # Track pass recipients for network
                recipient_id = row.get('pass_recipient_id')
                if pd.notna(recipient_id) and recipient_id in starting_player_ids:
                    recipient_name = starting_player_ids_to_names[recipient_id]
                    key = (player_name, recipient_name)
                    pass_connections[key] = pass_connections.get(key, 0) + 1
            
            if locations:
                avg_x = sum(loc[0] for loc in locations) / len(locations)
                avg_y = sum(loc[1] for loc in locations) / len(locations)
                player_positions[player_name] = {
                    'x': avg_x,
                    'y': avg_y,
                    'passes': len(locations),
                    'obv': total_obv
                }
    
    return player_positions, pass_connections

@st.cache_data
def get_match_dates():
    """Fetch match dates from StatsBomb API"""
    try:
        from statsbombpy import sb
        creds = {"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"}
        season_id = 318
        competition_id = 1522
        
        matches = sb.matches(season_id=season_id, competition_id=competition_id, creds=creds)
        # Return dictionary of match_id: match_date
        return dict(zip(matches['match_id'], matches['match_date']))
    except Exception as e:
        st.warning(f"Could not fetch match dates: {e}")
        return {}

df = load_data()
match_dates = get_match_dates()
team_season_stats = load_team_season_stats()

# Create mapping from match stat columns to season stat columns
# Stats set to None will not show season comparison
MATCH_TO_SEASON_STAT_MAP = {
    "team_match_goals": None,  # No comparison for goals
    "team_match_np_xg": "team_season_np_xg_pg",
    "team_match_np_shots": "team_season_np_shots_pg",
    "team_match_possession": "team_season_possession",
    "team_match_passing_ratio": "team_season_passing_ratio",
    "team_match_passes": "team_season_passes_pg",
    "team_match_successful_passes": "team_season_successful_passes_pg",
    "team_match_pressures": "team_season_pressures_pg",
    "team_match_counterpressures": "team_season_counterpressures_pg",
    "team_match_pressure_regains": "team_season_pressure_regains_pg",
    "team_match_defensive_action_regains": "team_season_defensive_action_regains_pg",
    "team_match_yellow_cards": None,  # No comparison for yellow cards
    "team_match_red_cards": None,  # No comparison for red cards
    # Additional mappings for more comprehensive comparison
    "team_match_op_shots": "team_season_op_shots_pg",
    "team_match_op_xg": "team_season_op_xg_pg",
    "team_match_deep_completions": "team_season_deep_completions_pg",
}

def get_season_avg(team_name, match_col):
    """Get the season average for a team and stat column"""
    if team_season_stats.empty:
        return None
    
    season_col = MATCH_TO_SEASON_STAT_MAP.get(match_col)
    if season_col is None:
        return None
    
    # Find team in season stats
    team_row = team_season_stats[team_season_stats['team_name'] == team_name]
    if team_row.empty or season_col not in team_row.columns:
        return None
    
    return team_row[season_col].iloc[0]

# -------------------------
# CREATE MATCH OPTIONS
# -------------------------
def format_match_option(match_df):
    """Format match as 'Home Team vs Away Team - Date'"""
    # Sort by team_id to ensure consistent ordering (lower team_id = home team)
    match_df_sorted = match_df.sort_values('team_id')
    teams = match_df_sorted["team_name"].tolist()
    
    if len(teams) >= 2:
        home_team = teams[0]
        away_team = teams[1]
    else:
        home_team = teams[0]
        away_team = "TBD"
    
    match_date = match_df["match_date"].iloc[0]
    
    # Format date nicely (e.g., "Jan 25, 2026")
    match_date_str = ""
    try:
        date_obj = pd.to_datetime(match_date)
        match_date_str = f" - {date_obj.strftime('%b %d, %Y')}"
    except:
        match_date_str = f" - {match_date}"
    
    return f"{home_team} vs {away_team}{match_date_str}", match_date

# Create match options
match_options = {}
for match_date in df["match_date"].unique():
    match_df = df[df["match_date"] == match_date]
    label, mdate = format_match_option(match_df)
    match_options[label] = mdate

# -------------------------
# SIDEBAR - MATCH SELECTION
# -------------------------
st.sidebar.title("MATCH SELECTION")
selected_match_label = st.sidebar.selectbox("Select Match", list(match_options.keys()))
selected_match_date = match_options[selected_match_label]

# Get match data - Home team always on left (lower team_id), Ujpest always purple
match_df = df[df["match_date"] == selected_match_date]
match_df_sorted = match_df.sort_values('team_id')
teams = match_df_sorted["team_name"].tolist()

# Home team (lower team_id) is always on the left
if len(teams) >= 2:
    home_team = teams[0]
    away_team = teams[1]
else:
    home_team = teams[0]
    away_team = teams[0]

row_home = match_df[match_df["team_name"] == home_team].iloc[0]
row_away = match_df[match_df["team_name"] == away_team].iloc[0]

# Determine which team is Ujpest for coloring
is_home_ujpest = home_team == "Ujpest"
is_away_ujpest = away_team == "Ujpest"

# Load events data (needed for starting lineups and xG race chart)
events_df = load_events_data(selected_match_date)

# -------------------------
# METRICS TO COMPARE
# -------------------------
# Tuple format: (Display Name, Column Name, Is Percentage?, Season Comparison Enabled?)
# Season comparison is only enabled for Ujpest
all_metrics = [
    ("Goals", "team_match_goals", False, False),
    ("xG (Non Penalty)", "team_match_np_xg", False, True),
    ("xG Conceded", "team_match_np_xg_conceded", False, True),
    ("Shots", "team_match_np_shots", False, True),
    ("Touches in Opp. Box", "team_touches_in_opp_box", False, True),
    ("Crosses into Box", "team_match_crosses_into_box", False, True),
    ("Final 3rd Forward Passes", "team_match_f3_forward_passes", False, True),
    ("Possession %", "team_match_possession", True, True),
    ("Passes per Possession", "passes_per_possession", False, True),
    ("PPDA", "team_match_ppda", False, True),
]

# Map match columns to season columns
MATCH_TO_SEASON_STAT_MAP = {
    "team_match_np_xg": "team_season_np_xg_pg",
    "team_match_np_xg_conceded": "team_season_np_xg_conceded_pg",
    "team_match_np_shots": "team_season_np_shots_pg",
    "team_touches_in_opp_box": None,  # Not available in season stats
    "team_match_crosses_into_box": "team_season_crosses_into_box_pg",
    "team_match_f3_forward_passes": None,  # Not available in season stats
    "team_match_possession": "team_season_possession",
    "passes_per_possession": None,  # Calculated field
    "team_match_ppda": "team_season_ppda",
}

# -------------------------
# HEADER
# -------------------------
# Choose header color based on which team is Ujpest
header_color = UJPEST_COLOR if is_home_ujpest or is_away_ujpest else "#2C3E50"
header_light = UJPEST_LIGHT if is_home_ujpest or is_away_ujpest else "#34495E"

st.markdown(
    f"""
    <div style="background: linear-gradient(135deg, {header_color} 0%, {header_light} 100%); 
                padding: 5px 10px; border-radius: 4px; margin-bottom: 8px;">
        <h2 style="color: white; text-align:center; margin:0; font-size: 1.3em;">
            {home_team} vs {away_team}
        </h2>
        <p style="color: white; text-align:center; margin:2px 0 0 0; opacity: 0.9; font-size: 0.8em;">
            {row_home['competition_name']} | {row_home['season_name']}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# SCORELINE & KEY STATS
# -------------------------
col1, col2, col3 = st.columns([2, 1, 2])

# Home team colors
home_color = UJPEST_COLOR if is_home_ujpest else OPPOSITION_COLOR

with col1:
    st.markdown(
        f"""
        <div style="background: {home_color}; padding: 5px; border-radius: 4px; text-align: center;">
            <div style="color: white; margin: 0; font-size: 1em; font-weight: bold;">{home_team}</div>
            <div style="color: white; margin: 1px 0 0 0; opacity: 0.9; font-size: 0.8em;">Possession: {row_home['team_match_possession']*100:.0f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div style="text-align: center; padding: 5px;">
            <div style="color: {UJPEST_COLOR if (is_home_ujpest or is_away_ujpest) else '#2C3E50'}; margin: 0; font-size: 1.8em; font-weight: bold;">
                {int(row_home['team_match_goals'])} - {int(row_away['team_match_goals'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Away team colors
away_color = UJPEST_COLOR if is_away_ujpest else OPPOSITION_COLOR

with col3:
    st.markdown(
        f"""
        <div style="background: {away_color}; padding: 5px; border-radius: 4px; text-align: center;">
            <div style="color: white; margin: 0; font-size: 1em; font-weight: bold;">{away_team}</div>
            <div style="color: white; margin: 1px 0 0 0; opacity: 0.9; font-size: 0.8em;">Possession: {row_away['team_match_possession']*100:.0f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin: 8px 0;'></div>", unsafe_allow_html=True)

# -------------------------
# COMPREHENSIVE STATISTICS TABLE
# -------------------------
def format_value(value, is_percentage=False):
    """Format values for display"""
    if pd.isna(value):
        return "-"
    if is_percentage:
        return f"{value*100:.1f}%"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(int(value))

def format_value_with_diff(value, season_avg, is_percentage=False, show_diff=True, use_html=False, use_reportlab=False):
    """Format values for display with difference from season average
    
    Args:
        value: The match value
        season_avg: The season average value
        is_percentage: Whether the value is a percentage
        show_diff: Whether to show the difference (only True for Ujpest)
        use_html: If True, return HTML with color styling (for Streamlit)
        use_reportlab: If True, return ReportLab-compatible markup (for PDF)
    """
    if pd.isna(value):
        return "-"
    
    # Format the main value
    if is_percentage:
        main_value = f"{value*100:.1f}%"
    elif isinstance(value, float):
        main_value = f"{value:.2f}"
    else:
        main_value = str(int(value))
    
    # Bold the value
    if use_html:
        main_value = f"<b>{main_value}</b>"
    elif use_reportlab:
        main_value = f"<b>{main_value}</b>"
    
    # If no season average or diff not requested, return just the value
    if not show_diff or season_avg is None or pd.isna(season_avg):
        return main_value
    
    # Calculate the difference
    diff = value - season_avg
    
    # Format the difference
    if is_percentage:
        diff_str = f"{diff*100:+.1f}%"
    elif isinstance(value, float):
        diff_str = f"{diff:+.2f}"
    else:
        diff_str = f"{diff:+.0f}"
    
    # Color code: green for positive (better), red for negative (worse)
    # For most stats, higher is better (except xG conceded and PPDA where lower is better)
    if diff > 0.001:  # Small threshold to avoid floating point issues
        color = "#28a745"  # Green - better than average
    elif diff < -0.001:
        color = "#dc3545"  # Red - worse than average
    else:
        color = "#6c757d"  # Gray - same as average
    
    if use_html:
        return f'{main_value} <span style="color:{color}">({diff_str})</span>'
    elif use_reportlab:
        return f'{main_value} <font color="{color}">({diff_str})</font>'
    else:
        return f"{main_value} ({diff_str})"

st.markdown(
    """
    <div style="text-align: center; margin-bottom: 5px;">
        <h3 style="color: #2C3E50; margin: 0; font-size: 1.1em;">Match Statistics</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

# Build HTML table with colored differences
html_rows = ""
for i, metric_info in enumerate(all_metrics):
    metric_name = metric_info[0]
    metric_col = metric_info[1]
    is_percentage = metric_info[2]
    show_season_comparison = metric_info[3]
    
    # Determine if we should show season comparison for each team
    home_show_diff = show_season_comparison and is_home_ujpest
    away_show_diff = show_season_comparison and is_away_ujpest
    
    # Get season averages
    home_season_avg = get_season_avg(home_team, metric_col) if home_show_diff else None
    away_season_avg = get_season_avg(away_team, metric_col) if away_show_diff else None
    
    home_value = format_value_with_diff(row_home[metric_col], home_season_avg, is_percentage, show_diff=home_show_diff, use_html=True)
    away_value = format_value_with_diff(row_away[metric_col], away_season_avg, is_percentage, show_diff=away_show_diff, use_html=True)
    
    # Alternate row background
    row_bg = "#F8F9FA" if i % 2 == 1 else "white"
    
    # Bold the metric name
    bold_metric_name = f"<b>{metric_name}</b>"
    
    html_rows += f'<tr style="background: {row_bg};"><td style="text-align: right; padding: 6px 10px; font-size: 0.85em;">{home_value}</td><td style="text-align: center; padding: 6px 10px; font-size: 0.85em;">{bold_metric_name}</td><td style="text-align: left; padding: 6px 10px; font-size: 0.85em;">{away_value}</td></tr>'

# Update column headers based on which team is Ujpest
home_header = f"{home_team}" + (" (vs avg)" if is_home_ujpest else "")
away_header = f"{away_team}" + (" (vs avg)" if is_away_ujpest else "")

# Render single HTML table with all stats
table_html = f'<table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 5px;"><thead><tr style="background: #f0f0f0;"><th style="text-align: right; padding: 8px 10px; font-size: 0.8em; border-bottom: 2px solid #ddd;">{home_header}</th><th style="text-align: center; padding: 8px 10px; font-size: 0.8em; border-bottom: 2px solid #ddd;">Statistic</th><th style="text-align: left; padding: 8px 10px; font-size: 0.8em; border-bottom: 2px solid #ddd;">{away_header}</th></tr></thead><tbody>{html_rows}</tbody></table>'
st.markdown(table_html, unsafe_allow_html=True)

st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)

# Statistics Analysis Text Box
stats_analysis = st.text_area(
    label="stats_analysis",
    placeholder="Write your statistics analysis here...",
    height=100,
    key="stats_analysis_input",
    label_visibility="collapsed"
)

# -------------------------
# STARTING LINEUPS VISUALIZATION
# -------------------------
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 5px; margin-top: 15px;">
        <h3 style="color: #2C3E50; margin: 0; font-size: 1.1em;">Starting Lineups - Pass Network & Average Positions</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

# Load events data for starting XI
if events_df is not None and len(events_df) > 0:
    starting_xi = parse_starting_xi(events_df)
    
    if len(starting_xi) >= 2:
        # Get the two teams
        teams_list = list(starting_xi.keys())
        
        # Ensure consistent ordering: home team first, away team second
        if teams_list[0] != home_team:
            teams_list = [teams_list[1], teams_list[0]]
        
        def create_pass_map_plot(team_name, team_data, team_color, avg_positions, pass_connections):
            """Create a pass map visualization with average player positions and pass network"""
            formation = team_data['formation']
            lineup = team_data['lineup']
            
            fig = go.Figure()
            
            # StatsBomb pitch dimensions: 120x80 (vertical orientation)
            # Add pitch outline
            fig.add_shape(type="rect", x0=0, y0=0, x1=80, y1=120,
                         line=dict(color="gray", width=2), fillcolor="rgba(255,255,255,0)")
            
            # Add halfway line (horizontal)
            fig.add_shape(type="line", x0=0, y0=60, x1=80, y1=60,
                         line=dict(color="gray", width=2))
            
            # Add center circle
            fig.add_shape(type="circle", x0=30, y0=50, x1=50, y1=70,
                         line=dict(color="gray", width=2))
            
            # Add penalty areas (both ends)
            # Bottom penalty area (own goal)
            fig.add_shape(type="rect", x0=18, y0=0, x1=62, y1=18,
                         line=dict(color="gray", width=2))
            # Top penalty area (opponent goal)
            fig.add_shape(type="rect", x0=18, y0=102, x1=62, y1=120,
                         line=dict(color="gray", width=2))
            
            # Add goal boxes
            # Bottom goal box
            fig.add_shape(type="rect", x0=30, y0=0, x1=50, y1=6,
                         line=dict(color="gray", width=2))
            # Top goal box
            fig.add_shape(type="rect", x0=30, y0=114, x1=50, y1=120,
                         line=dict(color="gray", width=2))
            
            # Draw pass network lines first (so they appear behind players)
            if pass_connections:
                for (passer, receiver), count in pass_connections.items():
                    if passer in avg_positions and receiver in avg_positions:
                        # Get positions (swap x and y for vertical orientation)
                        passer_pos = avg_positions[passer]
                        receiver_pos = avg_positions[receiver]
                        
                        # More aggressive line width based on pass count
                        # Show lines for 2+ passes (lowered from 3)
                        if count >= 2:
                            # More aggressive scaling: 1px per 3 passes instead of per 10
                            line_width = min(0.8 + count / 3, 8)
                            # More visible opacity
                            line_opacity = min(0.4 + count / 30, 0.9)
                            
                            fig.add_trace(go.Scatter(
                                x=[passer_pos['y'], receiver_pos['y']],  # y becomes x in vertical
                                y=[passer_pos['x'], receiver_pos['x']],  # x becomes y in vertical
                                mode='lines',
                                line=dict(
                                    color=team_color,
                                    width=line_width,
                                ),
                                opacity=line_opacity,
                                hovertext=f"{passer} → {receiver}<br>Passes: {count}",
                                hoverinfo='text',
                                showlegend=False
                            ))
            
            # OBV color scale: red (negative) -> yellow (neutral) -> blue/green (positive)
            # Based on typical OBV range: -0.05 to 0.23+
            OBV_MIN = -0.05
            OBV_MAX = 0.23
            
            def obv_to_color(obv_value):
                """Map OBV value to color using blue-green-yellow-red gradient (red = high/good OBV)"""
                # Normalize to 0-1 range
                normalized = (obv_value - OBV_MIN) / (OBV_MAX - OBV_MIN)
                normalized = max(0, min(1, normalized))  # Clamp to [0, 1]
                
                if normalized < 0.33:
                    # Blue to green (low OBV)
                    t = normalized / 0.33
                    r = int(40 + t * 30)
                    g = int(150 + t * 50)
                    b = int(220 - t * 120)
                elif normalized < 0.66:
                    # Green to yellow (medium OBV)
                    t = (normalized - 0.33) / 0.33
                    r = int(70 + t * 150)
                    g = int(200)
                    b = int(100 - t * 50)
                else:
                    # Yellow to red (high OBV - GOOD!)
                    t = (normalized - 0.66) / 0.34
                    r = int(220)
                    g = int(200 - t * 150)
                    b = int(50)
                
                return f'rgb({r},{g},{b})'
            
            # Plot players at their average positions
            # First, collect all player positions to detect clusters
            player_data = []
            for player in lineup:
                player_name = player['player']['name']
                jersey = player.get('jersey_number', '')
                position_name = player['position']['name']
                
                if player_name in avg_positions:
                    pos_data = avg_positions[player_name]
                    x = pos_data['x']
                    y = pos_data['y']
                    num_passes = pos_data['passes']
                    obv = pos_data.get('obv', 0)
                    
                    # Use only last name
                    name_parts = player_name.split()
                    display_name = name_parts[-1] if len(name_parts) > 1 else player_name
                    
                    marker_size = min(20 + num_passes / 3, 50)
                    
                    player_data.append({
                        'name': player_name,
                        'display_name': display_name,
                        'x': x,
                        'y': y,
                        'jersey': jersey,
                        'position': position_name,
                        'passes': num_passes,
                        'marker_size': marker_size,
                        'obv': obv
                    })
            
            # Plot players with their assigned text positions and OBV-based colors
            for p in player_data:
                marker_color = obv_to_color(p['obv'])
                
                fig.add_trace(go.Scatter(
                    x=[p['y']], y=[p['x']],
                    mode='markers+text',
                    marker=dict(
                        size=p['marker_size'], 
                        color=marker_color, 
                        line=dict(width=2, color='white'),
                        opacity=0.9
                    ),
                    text=p['display_name'],
                    textposition='middle center',  # Place text exactly on the circle
                    textfont=dict(size=8, color='black', family='Arial', weight='bold'),  # Black bold text
                    hovertext=f"{p['name']}<br>#{p['jersey']}<br>{p['position']}<br>Passes: {p['passes']}<br>OBV: {p['obv']:.3f}<br>Avg Position: ({p['x']:.1f}, {p['y']:.1f})",
                    hoverinfo='text',
                    showlegend=False,
                    cliponaxis=False
                ))
            
            # Add a dummy trace for the colorbar legend
            # Create gradient values for colorbar
            colorbar_values = [OBV_MIN + (OBV_MAX - OBV_MIN) * i / 10 for i in range(11)]
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(
                    size=0.1,
                    color=[OBV_MIN],
                    colorscale=[
                        [0, 'rgb(40,150,220)'],      # Blue (negative/low OBV)
                        [0.33, 'rgb(70,200,100)'],   # Green (low-medium OBV)
                        [0.66, 'rgb(220,200,50)'],   # Yellow (medium OBV)
                        [1, 'rgb(220,50,50)']        # Red (high/positive OBV - GOOD!)
                    ],
                    cmin=OBV_MIN,
                    cmax=OBV_MAX,
                    colorbar=dict(
                        title=dict(text='OBV', font=dict(size=10), side='top'),
                        tickvals=[OBV_MIN, 0, 0.1, OBV_MAX],
                        ticktext=[f'{OBV_MIN}', '0', '0.1', f'{OBV_MAX}+'],
                        tickfont=dict(size=8),
                        len=0.4,
                        thickness=12,
                        x=1.02,
                        y=0.5,
                    ),
                    showscale=True
                ),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            # Update layout
            fig.update_layout(
                title=dict(
                    text=f"{team_name}, Starting Eleven<br><sub>Formation: {formation} | Pass network & OBV coloring</sub>",
                    font=dict(size=14, color=team_color),
                    x=0.5,
                    xanchor='center'
                ),
                xaxis=dict(range=[-5, 85], showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(range=[-5, 125], showgrid=False, showticklabels=False, zeroline=False),
                plot_bgcolor='rgba(144, 238, 144, 0.3)',  # Light green for pitch
                paper_bgcolor='white',
                height=600,
                margin=dict(l=20, r=60, t=60, b=20),
                uniformtext=dict(mode='hide', minsize=6)
            )
            
            return fig
        
        # Create two columns for the pass maps
        col_left, col_right = st.columns(2)
        
        with col_left:
            team1_color = home_color
            avg_pos_team1, pass_conn_team1 = calculate_player_average_positions(
                events_df, teams_list[0], starting_xi[teams_list[0]]['lineup']
            )
            fig1 = create_pass_map_plot(teams_list[0], starting_xi[teams_list[0]], team1_color, avg_pos_team1, pass_conn_team1)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_right:
            team2_color = away_color
            avg_pos_team2, pass_conn_team2 = calculate_player_average_positions(
                events_df, teams_list[1], starting_xi[teams_list[1]]['lineup']
            )
            fig2 = create_pass_map_plot(teams_list[1], starting_xi[teams_list[1]], team2_color, avg_pos_team2, pass_conn_team2)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Add legend explanation below the pass maps
        st.markdown(
            """
            <div style="display: flex; justify-content: center; gap: 40px; padding: 10px; background: #f8f9fa; border-radius: 8px; margin: 5px 0; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #888;"></span>
                        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: #888;"></span>
                        <span style="display: inline-block; width: 18px; height: 18px; border-radius: 50%; background: #888;"></span>
                    </div>
                    <span style="font-size: 0.75em; color: #555;">1 → 100+ passes</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <span style="display: inline-block; width: 20px; height: 1px; background: #888;"></span>
                        <span style="display: inline-block; width: 20px; height: 3px; background: #888;"></span>
                        <span style="display: inline-block; width: 20px; height: 6px; background: #888;"></span>
                    </div>
                    <span style="font-size: 0.75em; color: #555;">2 → 40+ passes</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <span style="display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: rgb(40,150,220); border: 1px solid #ccc;"></span>
                        <span style="display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: rgb(70,200,100); border: 1px solid #ccc;"></span>
                        <span style="display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: rgb(220,200,50); border: 1px solid #ccc;"></span>
                        <span style="display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: rgb(220,50,50); border: 1px solid #ccc;"></span>
                    </div>
                    <span style="font-size: 0.75em; color: #555;">-0.05 → 0.23+ OBV (red = better)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("Starting lineup data not available for this match.")
else:
    st.info("Event data not available for this match.")

st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)

# Pass Map Analysis Text Box
passmap_analysis = st.text_area(
    label="passmap_analysis",
    placeholder="Write your pass network analysis here...",
    height=100,
    key="passmap_analysis_input",
    label_visibility="collapsed"
)

# -------------------------
# CUMULATIVE XG RACE CHART
# -------------------------
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 5px; margin-top: 15px;">
        <h3 style="color: #2C3E50; margin: 0; font-size: 1.1em;">Cumulative xG Race</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

if events_df is not None and len(events_df) > 0:
    # Build xG race chart
    def build_step_series(team_shots, match_end_minute):
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
        x.append(match_end_minute)
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
    
    # Get shots with xG
    shots = events_df[
        (events_df["type"] == "Shot") &
        (events_df["shot_statsbomb_xg"].notna())
    ].copy()
    
    shots["shot_xg"] = shots["shot_statsbomb_xg"].round(2)
    
    # Find match end time
    match_end_minute = events_df["time"].max()
    
    # Build series for both teams
    home_shots = shots[shots["team"] == home_team]
    away_shots = shots[shots["team"] == away_team]
    
    series_home = build_step_series(home_shots, match_end_minute)
    series_away = build_step_series(away_shots, match_end_minute)
    
    # Create the plot
    fig_xg = go.Figure()
    
    # Add home team trace
    fig_xg.add_trace(go.Scatter(
        x=series_home["time"],
        y=series_home["cum_xg"],
        mode="lines",
        name=home_team,
        line=dict(color=home_color, width=4),
        hovertemplate=(
            "<b>%{y:.2f} xG</b><br>"
            "Player: %{customdata[0]}<br>"
            "Action: %{customdata[1]}<br>"
            "Shot xG: %{customdata[2]}<extra></extra>"
        ),
        customdata=series_home[["player", "action", "xg"]].values
    ))
    
    # Add away team trace
    fig_xg.add_trace(go.Scatter(
        x=series_away["time"],
        y=series_away["cum_xg"],
        mode="lines",
        name=away_team,
        line=dict(color=away_color, width=4),
        hovertemplate=(
            "<b>%{y:.2f} xG</b><br>"
            "Player: %{customdata[0]}<br>"
            "Action: %{customdata[1]}<br>"
            "Shot xG: %{customdata[2]}<extra></extra>"
        ),
        customdata=series_away[["player", "action", "xg"]].values
    ))
    
    # Add goal markers
    goals = shots[shots["shot_outcome"] == "Goal"].copy()
    
    def add_goal_markers(goals_df, team, color, series_data):
        """Add goal markers to the chart"""
        if len(goals_df) == 0:
            return
        
        team_goals = goals_df[goals_df["team"] == team].copy()
        if len(team_goals) == 0:
            return
        
        # For each goal, find the cumulative xG at that time
        y_values = []
        for _, goal in team_goals.iterrows():
            goal_time = goal["time"]
            cum_xg_at_time = series_data[series_data["time"] <= goal_time]["cum_xg"].iloc[-1] if len(series_data[series_data["time"] <= goal_time]) > 0 else 0
            y_values.append(cum_xg_at_time)
        
        fig_xg.add_trace(go.Scatter(
            x=team_goals["time"],
            y=y_values,
            mode="markers",
            name=f"{team} Goals",
            marker=dict(
                symbol="star",
                size=16,
                color=color,
                line=dict(width=2, color="white")
            ),
            hovertemplate=(
                "<b>GOAL</b><br>"
                "Player: %{customdata[0]}<br>"
                "Minute: %{x:.1f}<extra></extra>"
            ),
            customdata=team_goals[["player"]].values,
            showlegend=True
        ))
    
    add_goal_markers(goals, home_team, home_color, series_home)
    add_goal_markers(goals, away_team, away_color, series_away)
    
    # Layout
    fig_xg.update_layout(
        xaxis=dict(
            title="Minute",
            range=[0, match_end_minute],
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
        margin=dict(l=60, r=40, t=40, b=60),
        height=400
    )
    
    st.plotly_chart(fig_xg, use_container_width=True)
else:
    st.info("Event data not available for this match. xG race chart cannot be displayed.")

st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)

# xG Race Chart Analysis Text Box
xg_analysis = st.text_area(
    label="xg_analysis",
    placeholder="Write your xG analysis here...",
    height=100,
    key="xg_analysis_input",
    label_visibility="collapsed"
)

# -------------------------
# FOOTER & PDF EXPORT
# -------------------------
st.markdown("<div style='margin: 8px 0;'></div>", unsafe_allow_html=True)

# PDF Export Button
def create_pdf_report():
    """Generate a PDF report of the match"""
    buffer = BytesIO()
    
    # Create PDF document in landscape orientation
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor(header_color),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor(header_color),
        spaceAfter=6,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    # Title
    elements.append(Paragraph(f"{home_team} vs {away_team}", title_style))
    elements.append(Paragraph(f"{row_home['competition_name']} | {row_home['season_name']}", subtitle_style))
    
    # Scoreline
    score_text = f"<font size=16><b>{int(row_home['team_match_goals'])} - {int(row_away['team_match_goals'])}</b></font>"
    elements.append(Paragraph(score_text, subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Key Stats Summary
    summary_data = [
        ["", home_team, away_team],
        ["Possession", f"{row_home['team_match_possession']*100:.0f}%", f"{row_away['team_match_possession']*100:.0f}%"],
        ["Non-Penalty xG", f"{row_home['team_match_np_xg']:.2f}", f"{row_away['team_match_np_xg']:.2f}"],
        ["Shots (NP)", f"{int(row_home['team_match_np_shots'])}", f"{int(row_away['team_match_np_shots'])}"],
        ["Passes", f"{int(row_home['team_match_passes'])}", f"{int(row_away['team_match_passes'])}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Detailed Statistics - all in one table without category headers
    # Create a style for table cells that can render HTML-like markup
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
    )
    
    # Use the all_metrics list directly (defined earlier in the file)
    # Update table headers based on which team is Ujpest
    home_header_pdf = f"{home_team}" + (" (vs avg)" if is_home_ujpest else "")
    away_header_pdf = f"{away_team}" + (" (vs avg)" if is_away_ujpest else "")
    
    table_data = [["Statistic", home_header_pdf, away_header_pdf]]
    for metric_info in all_metrics:
        metric_name = metric_info[0]
        metric_col = metric_info[1]
        is_percentage = metric_info[2]
        show_season_comparison = metric_info[3]
        
        # Determine if we should show season comparison for each team
        home_show_diff = show_season_comparison and is_home_ujpest
        away_show_diff = show_season_comparison and is_away_ujpest
        
        # Get season averages
        home_season_avg = get_season_avg(home_team, metric_col) if home_show_diff else None
        away_season_avg = get_season_avg(away_team, metric_col) if away_show_diff else None
        
        # Use ReportLab markup for colored text
        home_value = format_value_with_diff(row_home[metric_col], home_season_avg, is_percentage, show_diff=home_show_diff, use_reportlab=True)
        away_value = format_value_with_diff(row_away[metric_col], away_season_avg, is_percentage, show_diff=away_show_diff, use_reportlab=True)
        
        # Wrap in Paragraph to render the color markup (includes bold formatting)
        # Bold the metric name
        bold_metric_name = f"<b>{metric_name}</b>"
        table_data.append([
            Paragraph(bold_metric_name, cell_style), 
            Paragraph(home_value, cell_style), 
            Paragraph(away_value, cell_style)
        ])
    
    stat_table = Table(table_data, colWidths=[4*inch, 3*inch, 3*inch])
    stat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
    ]))
    elements.append(stat_table)
    
    # Add statistics analysis if provided (directly after tables, no extra spacing)
    if stats_analysis and stats_analysis.strip():
        analysis_style = ParagraphStyle(
            'AnalysisText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceBefore=4,
            spaceAfter=4,
            leading=14,
        )
        elements.append(Paragraph(stats_analysis, analysis_style))
    
    # Add pass maps if available
    if events_df is not None and len(events_df) > 0:
        starting_xi = parse_starting_xi(events_df)
        
        if len(starting_xi) >= 2:
            elements.append(PageBreak())
            
            # Get the two teams
            teams_list = list(starting_xi.keys())
            
            # Ensure consistent ordering: home team first, away team second
            if teams_list[0] != home_team:
                teams_list = [teams_list[1], teams_list[0]]
            
            # Export pass maps as images
            try:
                # Team 1 (Home)
                team1_color = home_color
                avg_pos_team1, pass_conn_team1 = calculate_player_average_positions(
                    events_df, teams_list[0], starting_xi[teams_list[0]]['lineup']
                )
                fig1 = create_pass_map_plot(teams_list[0], starting_xi[teams_list[0]], team1_color, avg_pos_team1, pass_conn_team1)
                
                # Export team 1 pass map (higher resolution for better quality)
                img_bytes1 = fig1.to_image(format="png", width=500, height=750, engine='kaleido')
                img_buffer1 = BytesIO(img_bytes1)
                pil_img1 = PILImage.open(img_buffer1)
                img_buffer1.seek(0)
                
                # Team 2 (Away)
                team2_color = away_color
                avg_pos_team2, pass_conn_team2 = calculate_player_average_positions(
                    events_df, teams_list[1], starting_xi[teams_list[1]]['lineup']
                )
                fig2 = create_pass_map_plot(teams_list[1], starting_xi[teams_list[1]], team2_color, avg_pos_team2, pass_conn_team2)
                
                # Export team 2 pass map (higher resolution for better quality)
                img_bytes2 = fig2.to_image(format="png", width=500, height=750, engine='kaleido')
                img_buffer2 = BytesIO(img_bytes2)
                pil_img2 = PILImage.open(img_buffer2)
                img_buffer2.seek(0)
                
                # Create side-by-side images using Table - full width landscape (10 inches total)
                img1 = RLImage(img_buffer1, width=4.8*inch, height=7*inch)
                img2 = RLImage(img_buffer2, width=4.8*inch, height=7*inch)
                
                # Create a table with team names as headers
                passmap_data = [
                    [Paragraph(f"<b>{teams_list[0]}</b>", subtitle_style), 
                     Paragraph(f"<b>{teams_list[1]}</b>", subtitle_style)],
                    [img1, img2]
                ]
                
                passmap_table = Table(passmap_data, colWidths=[5*inch, 5*inch])
                passmap_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                
                elements.append(passmap_table)
                
                # Add pass map analysis if provided (directly after maps, no extra spacing)
                if passmap_analysis and passmap_analysis.strip():
                    analysis_style = ParagraphStyle(
                        'AnalysisText',
                        parent=styles['Normal'],
                        fontSize=10,
                        textColor=colors.black,
                        spaceBefore=4,
                        spaceAfter=4,
                        leading=14,
                    )
                    elements.append(Paragraph(passmap_analysis, analysis_style))
                    
            except Exception as e:
                # If pass map export fails, add a note
                note_style = ParagraphStyle(
                    'Note',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.grey,
                    alignment=TA_CENTER,
                    spaceAfter=12,
                )
                elements.append(Paragraph(
                    "Pass network maps could not be exported to PDF.",
                    note_style
                ))
                elements.append(Paragraph(
                    f"<i>(Error: {str(e)})</i>",
                    note_style
                ))
    
    # Add xG chart if available
    if events_df is not None and len(events_df) > 0:
        elements.append(PageBreak())
        
        # Export plotly chart as image
        try:
            # Export to bytes buffer instead of file (higher resolution for landscape)
            img_bytes = fig_xg.to_image(format="png", width=1200, height=500, engine='kaleido')
            
            # Create a BytesIO object from the image bytes
            img_buffer = BytesIO(img_bytes)
            
            # Open with PIL to verify it's valid
            pil_img = PILImage.open(img_buffer)
            img_buffer.seek(0)  # Reset buffer position
            
            # Create ReportLab image from buffer - full width landscape
            img = RLImage(img_buffer, width=10*inch, height=4.2*inch)
            elements.append(img)
                
        except Exception as e:
            # If chart export fails, add a note and continue with PDF
            note_style = ParagraphStyle(
                'Note',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=12,
            )
            elements.append(Paragraph(
                "xG Race chart could not be exported to PDF. Please view it in the dashboard.",
                note_style
            ))
            elements.append(Paragraph(
                f"<i>(Install kaleido with: pip install -U kaleido)</i>",
                note_style
            ))
        
        # Add xG analysis if provided (directly after chart, no extra spacing)
        if xg_analysis and xg_analysis.strip():
            analysis_style = ParagraphStyle(
                'AnalysisText',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.black,
                spaceBefore=4,
                spaceAfter=4,
                leading=14,
            )
            elements.append(Paragraph(xg_analysis, analysis_style))
    
    # Footer
    elements.append(Spacer(1, 0.1*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph("Match Report Dashboard | Powered by StatsBomb Data", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Export button
col_export1, col_export2, col_export3 = st.columns([1, 1, 1])
with col_export2:
    if st.button("📄 Export Match Report as PDF", use_container_width=True):
        with st.spinner("Generating PDF..."):
            try:
                pdf_buffer = create_pdf_report()
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_buffer,
                    file_name=f"{home_team}_vs_{away_team}_match_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ PDF generated successfully!")
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
                
                # Provide specific help based on the error
                error_msg = str(e).lower()
                if "kaleido" in error_msg or "write_image" in error_msg or "cannot open resource" in error_msg:
                    st.warning("📊 Chart export issue detected. The xG chart requires the 'kaleido' package.")
                    st.code("pip install -U kaleido", language="bash")
                    st.info("💡 Tip: The PDF will be generated without the chart if kaleido is not available. All statistics will still be included.")
                else:
                    st.info("Please check that all required packages are installed: pip install -r requirements.txt")

st.markdown(
    """
    <hr style="border: 0; border-top: 1px solid #E0E0E0;">
    <p style="text-align:center; color:#7F8C8D; font-size:9px; padding: 3px 0;">
        Match Report Dashboard | Powered by StatsBomb Data
    </p>
    """,
    unsafe_allow_html=True,
)
