#!/usr/bin/env bash
# Install (or reinstall) the weekly StatsBomb pipeline as a launchd agent.
# Runs run_pipeline.py every Sunday and Monday at 10:00 local time.
set -euo pipefail

PLIST_SRC="/Users/botondvarga/downloader_services/statsbomb_legacy/com.ujpest.statsbomb.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.ujpest.statsbomb.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

# Reload cleanly (ignore errors if it wasn't loaded yet).
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Installed. Scheduled runs:"
launchctl list | grep com.ujpest.statsbomb || true
echo
echo "Run once now to test:   launchctl start com.ujpest.statsbomb"
echo "Watch the log:          tail -f /Users/botondvarga/downloader_services/statsbomb_legacy/logs/pipeline.log"
echo "Uninstall:              launchctl unload $PLIST_DST && rm $PLIST_DST"
