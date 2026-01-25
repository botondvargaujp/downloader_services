# Match Report Dashboard

A Streamlit-based dashboard for viewing match statistics and xG race charts with PDF export functionality.

## Features

- **Match Selection**: Choose from available matches with team names and dates
- **Comprehensive Statistics**: View detailed match stats organized by category:
  - Attacking
  - Set Pieces
  - Possession & Passing
  - Pressing & Defense
  - Defensive Statistics
  - Dribbles & Cards
- **Cumulative xG Race Chart**: Interactive visualization showing how expected goals accumulated throughout the match
- **PDF Export**: Download a professional match report as PDF

## Installation

Install the required dependencies:

```bash
pip install -r ../requirements.txt
```

## Running the Dashboard

From the `statsbomb_legacy` directory:

```bash
streamlit run dashboard_app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## PDF Export

The PDF export feature requires:
- `reportlab` - for PDF generation
- `kaleido` - for exporting Plotly charts as images

Both are included in the requirements.txt file. If PDF export fails, ensure kaleido is properly installed:

```bash
pip install kaleido==0.2.1
```

## Data Requirements

The dashboard expects:
- Match statistics files in `../match_data/stats_*.csv`
- Event data files in `../match_data/events_*.csv`

## Customization

Colors for your team (Ujpest) can be customized in the CONFIG section:
- `UJPEST_COLOR`: Main team color (default: purple)
- `UJPEST_LIGHT`: Lighter shade for gradients
- `OPPOSITION_COLOR`: Opposition team color (default: gray)
