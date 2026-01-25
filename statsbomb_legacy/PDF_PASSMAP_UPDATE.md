# PDF Export Update - Pass Maps Added

## What Was Changed

Updated the `create_pdf_report()` function to include the pass network visualizations in the exported PDF.

## Changes Made

### 1. Added Pass Map Export Section
- Inserted between statistics tables and xG race chart
- Creates a new page break for pass maps
- Exports both teams' pass networks

### 2. Pass Map Generation in PDF
For each team:
1. Parses starting XI from events data
2. Calculates player average positions
3. Generates pass network connections
4. Creates the pass map visualization
5. Exports as PNG image (500x750px)
6. Embeds in PDF (3.5" x 5.25")

### 3. Error Handling
- Try-catch block for pass map export
- Falls back gracefully if kaleido is not installed
- Shows error message in PDF if export fails

## PDF Structure (Updated)

```
┌─────────────────────────────────────┐
│ PAGE 1: Match Overview              │
│  • Title & Score                    │
│  • Key Stats Summary Table          │
│  • Match Overview Stats             │
│  • Pressing & Defense Stats         │
│  • Discipline Stats                 │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ PAGE 2: Pass Networks               │
│  • Section Header                   │
│  • Home Team Pass Map               │
│    - Vertical pitch                 │
│    - Player positions               │
│    - Pass network lines             │
│  • Away Team Pass Map               │
│    - Vertical pitch                 │
│    - Player positions               │
│    - Pass network lines             │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ PAGE 3: xG Race Chart               │
│  • Cumulative xG Race               │
│  • Goal markers                     │
│  • Both teams timeline              │
└─────────────────────────────────────┘
```

## Technical Details

### Image Export Settings
```python
# Pass map export
width=500px, height=750px (vertical orientation)
format="png"
engine='kaleido'

# PDF image size
width=3.5 inches, height=5.25 inches
```

### Dependencies
- **kaleido**: Required for Plotly image export
- Falls back gracefully if not installed
- Shows installation instructions in error message

### Code Location
- Function: `create_pdf_report()` (line ~793)
- Pass map section: After statistics tables, before xG chart
- Lines: ~908-975 (approximate)

## Usage

1. Open the dashboard
2. Select a match
3. Scroll to bottom
4. Click "📄 Export Match Report as PDF"
5. Click "⬇️ Download PDF" when ready

## What's Included in PDF

✅ Match header with score
✅ Key statistics summary
✅ Detailed match statistics
✅ **Pass network maps (NEW)** - Both teams
✅ Cumulative xG race chart
✅ Footer

## Benefits

1. **Complete report**: All visualizations in one PDF
2. **Team comparison**: Both pass maps included
3. **Professional format**: Clean layout on separate page
4. **Portable**: Share tactical analysis easily
5. **Offline viewing**: No dashboard needed

## Notes

- Pass maps are exported in vertical orientation
- Each team gets its own pass map on the same page
- Colors are preserved (Ujpest = purple, Opposition = gray)
- Player names and pass network lines are visible
- High resolution (500x750px) ensures clarity

## Error Messages

If kaleido is not installed:
```
Pass network maps could not be exported to PDF.
(Install kaleido with: pip install -U kaleido)
```

The PDF will still be generated with all other content.

---

**Status**: ✅ Complete - Pass maps now included in PDF exports!
