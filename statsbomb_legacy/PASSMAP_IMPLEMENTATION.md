# Pass Map Implementation Summary

## Overview
Added a new "Starting Lineups - Average Pass Positions" visualization to the dashboard that shows where each starting XI player made their passes from during the match.

## Features Implemented

### 1. Parse Starting XI Data
- Extracts formation and lineup information from the events CSV file
- Uses the `tactics` column which contains formation and player position data
- Supports both teams in a match

### 2. Calculate Average Pass Positions
- Analyzes all pass events for each starting XI player
- Computes the average X,Y coordinates where each player made passes
- Tracks the total number of passes per player
- Only includes starting XI players (excludes substitutes)

### 3. Horizontal Pitch Layout
- Changed from vertical to horizontal pitch orientation
- Pitch dimensions: 120 x 80 yards (StatsBomb standard)
- Halfway line is now vertical (splitting left/right halves)
- Both penalty areas and goal boxes are shown

### 4. Interactive Visualization
- Player markers sized based on number of passes (more passes = larger marker)
- Player names displayed above their markers
- Hover to see:
  - Full player name
  - Jersey number
  - Position
  - Number of passes made
  - Average position coordinates
- Team colors maintained (Ujpest = Purple, Opposition = Gray)

### 5. Side-by-Side Comparison
- Both teams displayed in two columns
- Left column: Home team (lower team_id)
- Right column: Away team (higher team_id)
- Maintains consistent Ujpest color scheme

## Data Requirements

### Input Data
- `events_{match_id}.csv` file in the `match_data/` folder
- Must contain:
  - Starting XI events with `tactics` column (formation + lineup)
  - Pass events with `location` field ([x, y] coordinates)
  - Player IDs to link passes to starting XI players

### Key Columns Used
- `type`: Filter for "Starting XI" and "Pass" events
- `tactics`: Contains formation and lineup data (dict as string)
- `team`: Team name
- `player_id`: Links passes to specific players
- `location`: Pass origin coordinates [x, y]

## Technical Details

### Position Calculation
```python
avg_x = sum(all_pass_x_coords) / num_passes
avg_y = sum(all_pass_y_coords) / num_passes
```

### Marker Sizing
```python
marker_size = min(20 + num_passes / 3, 50)
```
- Minimum: 20 pixels
- Maximum: 50 pixels
- Scales linearly with pass count

### Pitch Coordinates
- X-axis: 0 (own goal) to 120 (opponent goal)
- Y-axis: 0 (left sideline) to 80 (right sideline)
- Halfway line: X = 60

## Usage

1. Run the Streamlit dashboard:
   ```bash
   cd statsbomb_legacy
   streamlit run dashboard_app.py
   ```

2. Select a match from the sidebar

3. Scroll down to the "Starting Lineups - Average Pass Positions" section

4. View both teams' pass maps side by side

5. Hover over players to see detailed statistics

## Benefits

1. **Tactical Insight**: Shows actual player positions vs. theoretical formation
2. **Spatial Analysis**: Identifies which areas of the pitch each player operated in
3. **Comparison**: Easy side-by-side team comparison
4. **Pass Volume**: Visual indication of player involvement through marker size
5. **Interactive**: Hover for detailed player statistics

## Example Output

For a match with Ujpest vs Opponent:
- Left panel: Opponent team formation with average pass positions
- Right panel: Ujpest team formation (in purple) with average pass positions
- Each player marker shows their name and average location
- Marker size reflects pass volume

## Future Enhancements

Potential additions:
1. Pass network lines showing connections between players
2. Pass completion rate color coding
3. Progressive pass markers
4. Heat maps overlaid on pass positions
5. Filter by match phase (first half, second half)
6. Animation showing position changes over time
