# Dashboard Enhancement: Starting Lineup Pass Maps

## Summary

Successfully added a new visualization section to the Match Report Dashboard that displays **Starting Lineups with Average Pass Positions** for both teams in a side-by-side comparison.

## What Was Implemented

### 1. **Starting XI Parser** (`parse_starting_xi()`)
- Extracts formation and player lineup data from events CSV
- Parses the `tactics` column containing JSON-like formation data
- Returns dictionary with team names as keys containing:
  - Formation number (e.g., 4411, 41212)
  - List of 11 starting players with positions and jersey numbers

### 2. **Average Position Calculator** (`calculate_player_average_positions()`)
- Filters pass events for each starting XI player
- Parses location coordinates from pass events
- Computes mean X and Y coordinates for each player
- Counts total passes made by each player
- Returns dictionary of player positions with pass counts

### 3. **Pass Map Visualizer** (`create_pass_map_plot()`)
- Creates interactive Plotly visualization with horizontal pitch layout
- Displays players at their average pass positions
- Features:
  - **Horizontal pitch**: 120 x 80 yards with halfway line vertical
  - **Player markers**: Sized by pass volume (20-50px)
  - **Color coding**: Ujpest (purple), Opposition (gray)
  - **Labels**: Player names above markers
  - **Hover details**: Full name, jersey #, position, pass count, coordinates
  - **Pitch markings**: Penalty areas, goal boxes, center circle

### 4. **Dashboard Integration**
- Added new section after statistics tables
- Side-by-side display of both teams
- Left column: Home team (lower team_id)
- Right column: Away team (higher team_id)
- Consistent with existing dashboard color scheme

## Key Features

### Visual Design
```
┌─────────────────────────────────────────────────────────┐
│     Starting Lineups - Average Pass Positions           │
├──────────────────────┬──────────────────────────────────┤
│  Team A (Purple)     │  Team B (Gray)                   │
│  Formation: 4411     │  Formation: 41212                │
│                      │                                  │
│  [Horizontal Pitch]  │  [Horizontal Pitch]              │
│  • Players shown at  │  • Players shown at              │
│    avg positions     │    avg positions                 │
│  • Size = pass vol.  │  • Size = pass vol.              │
└──────────────────────┴──────────────────────────────────┘
```

### Data Source
- Input: `match_data/events_{match_id}.csv`
- Required columns:
  - `type`: "Starting XI", "Pass"
  - `tactics`: Formation + lineup JSON
  - `team`: Team name
  - `player_id`: Player identifier
  - `location`: [x, y] coordinates

### Calculation Example
For player "João Nunes":
- Pass 1 at [41.2, 58.1]
- Pass 2 at [42.5, 61.3]
- Pass 3 at [39.8, 55.7]
- **Average position**: [41.17, 58.37]
- **Pass count**: 3
- **Marker size**: 21px (20 + 3/3)

## Technical Implementation

### Code Structure
```
dashboard_app.py
├── parse_starting_xi(events_df)
│   └── Returns: {team_name: {formation, lineup}}
├── calculate_player_average_positions(events_df, team_name, players)
│   └── Returns: {player_name: {x, y, passes}}
└── create_pass_map_plot(team_name, team_data, color, positions)
    └── Returns: Plotly Figure object
```

### Pitch Coordinates (Horizontal Layout)
```
        0 (Own Goal)          60 (Halfway)        120 (Opp Goal)
    0   ┌────────────────────────┬────────────────────────┐
        │ ○                      │                      ○ │
        │                        │                        │
   40   │           ◉            │            ◉           │  (Center)
        │                        │                        │
        │ ○                      │                      ○ │
   80   └────────────────────────┴────────────────────────┘
```

## Usage Instructions

1. **Start the dashboard**:
   ```bash
   cd statsbomb_legacy
   streamlit run dashboard_app.py
   ```

2. **Select a match** from the sidebar dropdown

3. **Scroll down** to "Starting Lineups - Average Pass Positions" section

4. **View both teams** displayed side-by-side:
   - Left: Home team pass map
   - Right: Away team pass map

5. **Interact with the visualization**:
   - Hover over any player to see detailed stats
   - Larger markers = more passes made
   - Position shows where player operated most

## Example Output

### Match: Paksi FC vs Ujpest

**Left Panel (Paksi FC - Gray)**
- Formation: 41212
- 11 players positioned at average pass locations
- Goalkeeper near own goal (low X)
- Forwards near opponent goal (high X)
- Midfielders in center areas

**Right Panel (Ujpest - Purple)**  
- Formation: 4411
- 11 players positioned at average pass locations
- Player markers sized by involvement
- Clear spatial distribution visible

## Files Modified

1. **`statsbomb_legacy/dashboard_app.py`**
   - Added `parse_starting_xi()` function (lines 70-93)
   - Added `calculate_player_average_positions()` function (lines 95-149)
   - Added pass map section (lines 454-601)
   - Moved `events_df` loading earlier (line 180)

## Files Created

1. **`statsbomb_legacy/test_passmap.py`**
   - Test script for validating calculations
   - Prints player positions and pass counts

2. **`statsbomb_legacy/PASSMAP_IMPLEMENTATION.md`**
   - Detailed technical documentation
   - Implementation details and future enhancements

3. **`statsbomb_legacy/PASSMAP_SUMMARY.md`** (this file)
   - High-level overview
   - Usage instructions

## Benefits

1. **Tactical Analysis**: See actual vs theoretical positions
2. **Player Roles**: Understand where players operate
3. **Team Shape**: Visual comparison of team structures
4. **Involvement**: Pass volume indicates player activity
5. **Interactive**: Detailed stats on hover

## Validation

The implementation correctly:
- ✅ Parses starting XI from events data
- ✅ Calculates average positions from pass locations
- ✅ Creates horizontal pitch layout
- ✅ Sizes markers by pass count
- ✅ Maintains team color schemes
- ✅ Displays side-by-side comparison
- ✅ Shows interactive hover information

## Next Steps

To run the dashboard and see the pass maps:

```bash
# Navigate to the statsbomb_legacy folder
cd /Users/botondvarga/downloader_services/statsbomb_legacy

# Run the dashboard
streamlit run dashboard_app.py
```

The pass map will appear below the statistics tables, showing where each starting player made their passes from during the match.
