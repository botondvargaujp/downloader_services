# Pass Map Visualization - Visual Guide

## Horizontal Pitch Layout

```
                     OPPONENT GOAL
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ║                                                              ║
    ║  ┌──┐                                              ┌──┐     ║
    ║  │GK│                                              │GK│     ║
    ║  └──┘                                              └──┘     ║
    ║                                                              ║
    ║        ┌──┐  ┌──┐                        ┌──┐  ┌──┐        ║
    ║        │CB│  │CB│         ◉              │CB│  │CB│        ║
    ║        └──┘  └──┘     HALFWAY            └──┘  └──┘        ║
    ║  ┌──┐                  LINE                          ┌──┐  ║
    ║  │LB│                   |                            │RB│  ║
    ║  └──┘                   |                            └──┘  ║
    ║                         |                                   ║
    ║     ┌──┐  ┌──┐         |           ┌──┐  ┌──┐             ║
    ║     │CM│  │CM│         |           │CM│  │CM│             ║
    ║     └──┘  └──┘         |           └──┘  └──┘             ║
    ║                         |                                   ║
    ║          ┌───┐          |            ┌───┐                 ║
    ║          │CAM│          |            │CAM│                 ║
    ║          └───┘          |            └───┘                 ║
    ║                         |                                   ║
    ║       ┌──┐  ┌──┐       |         ┌──┐  ┌──┐               ║
    ║       │FW│  │FW│       |         │FW│  │FW│               ║
    ║       └──┘  └──┘       |         └──┘  └──┘               ║
    ║                                                              ║
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                      OWN GOAL

    X: 0 ───────────────> 60 ───────────────> 120
    Y: 0 (left) ──────────────────────> 80 (right)
```

## Marker Sizing Logic

```
Number of Passes    →    Marker Size
─────────────────────────────────────
0 passes           →    (not shown)
1-3 passes         →    20-21 px
10 passes          →    23 px
30 passes          →    30 px
60 passes          →    40 px
90+ passes         →    50 px (max)
```

## Player Marker Example

```
     Tomás João
        ◉ ←── Marker (colored by team)
        │
        └─── Name displayed above
        
Hover Info:
┌─────────────────────────┐
│ João Aniceto Nunes      │
│ #30                     │
│ Right Center Back       │
│ Passes: 45              │
│ Avg Position: (42.3, 35.1) │
└─────────────────────────┘
```

## Side-by-Side Display

```
┌───────────────────────────────────┬───────────────────────────────────┐
│                                   │                                   │
│     Paksi FC, Starting Eleven     │    Ujpest, Starting Eleven        │
│      Formation: 41212             │      Formation: 4411              │
│                                   │                                   │
│  [Horizontal Pitch - Gray]        │  [Horizontal Pitch - Purple]      │
│                                   │                                   │
│  • Goalkeeper near left           │  • Goalkeeper near left           │
│  • Defenders spread across back   │  • Defenders spread across back   │
│  • Midfielders in center          │  • Midfielders in center          │
│  • Forwards near right            │  • Forward near right             │
│                                   │                                   │
│  Marker size = pass volume        │  Marker size = pass volume        │
│                                   │                                   │
└───────────────────────────────────┴───────────────────────────────────┘
```

## Color Scheme

```
Ujpest Team:
  Primary:   #6A0DAD (Purple)
  Secondary: #9B4FD4 (Light Purple)

Opposition Team:
  Primary:   #95A5A6 (Gray)
  Secondary: #BDC3C7 (Light Gray)

Pitch:
  Background: rgba(144, 238, 144, 0.3) (Light Green)
  Lines:      Gray
  Border:     Gray (2px)
```

## Data Flow

```
events_4003664.csv
        ↓
┌───────────────────────────────┐
│ parse_starting_xi()           │
│                               │
│ Input: events_df              │
│ Filter: type == "Starting XI" │
│ Extract: tactics column       │
│ Parse: JSON formation data    │
│                               │
│ Output: {                     │
│   "Team A": {                 │
│     formation: 4411,          │
│     lineup: [11 players]      │
│   },                          │
│   "Team B": {...}             │
│ }                             │
└───────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ calculate_player_average_positions()    │
│                                         │
│ Input: events_df, team_name, players   │
│ Filter: type == "Pass"                 │
│         team == team_name               │
│         player_id in starting_xi        │
│                                         │
│ For each player:                        │
│   Extract all pass locations           │
│   Calculate mean X, Y                  │
│   Count total passes                   │
│                                         │
│ Output: {                               │
│   "Player Name": {                      │
│     x: 45.3,                            │
│     y: 38.7,                            │
│     passes: 42                          │
│   },                                    │
│   ...                                   │
│ }                                       │
└─────────────────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ create_pass_map_plot()        │
│                               │
│ Input: team_data, positions   │
│                               │
│ 1. Create Plotly Figure       │
│ 2. Draw pitch (120x80)        │
│ 3. Add markings               │
│ 4. Plot players at avg pos    │
│ 5. Size markers by passes     │
│ 6. Add hover information      │
│                               │
│ Output: Interactive Figure    │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ Streamlit Dashboard           │
│                               │
│ • Display side-by-side        │
│ • Left: Home team             │
│ • Right: Away team            │
│ • Interactive hover           │
└───────────────────────────────┘
```

## Example Player Data Processing

```
Raw Event Data:
┌──────┬──────┬────────┬─────────────┬─────────────┐
│ type │ team │ player │  player_id  │  location   │
├──────┼──────┼────────┼─────────────┼─────────────┤
│ Pass │ UJP  │ João   │    7977     │ [41.2, 58.1]│
│ Pass │ UJP  │ João   │    7977     │ [42.5, 61.3]│
│ Pass │ UJP  │ João   │    7977     │ [39.8, 55.7]│
│ Pass │ UJP  │ Tom    │   68861     │ [55.3, 45.2]│
│ ...  │ ...  │ ...    │     ...     │     ...     │
└──────┴──────┴────────┴─────────────┴─────────────┘

Processed:
┌─────────────────────┬──────┬──────┬────────┐
│     Player Name     │  X   │  Y   │ Passes │
├─────────────────────┼──────┼──────┼────────┤
│ João Nunes          │ 41.2 │ 58.4 │   3    │
│ Tom Lacoux          │ 55.3 │ 45.2 │   1    │
│ Attila Fiola        │ 28.5 │ 22.8 │  12    │
│ ...                 │ ...  │ ...  │  ...   │
└─────────────────────┴──────┴──────┴────────┘
```

## Coordinate System

```
StatsBomb Standard Pitch:
- Length: 120 yards (0 to 120 on X-axis)
- Width: 80 yards (0 to 80 on Y-axis)

Attacking left to right:
  Own goal at X=0
  Opponent goal at X=120

Typical player X positions:
  GK:  5-15
  DEF: 20-35
  MID: 40-65
  FWD: 70-100

Typical player Y positions:
  Left:  10-25
  Center: 35-45
  Right: 55-70
```

This visualization shows players' actual positions based on where they made passes, providing tactical insights into team shape and player roles during the match.
