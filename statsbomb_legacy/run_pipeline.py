"""Weekly StatsBomb pipeline entry point.

Runs the full fetch -> enrich pipeline in one shot:
  1. Scan NB1 for Ujpest games whose data is newly available and download them.
  2. Refresh season-level stats.
  3. Recompute derived per-match / per-season aggregates.

Designed to be run every Sunday and Monday (weekend games, plus a Monday pass to
catch data that lands late). Scheduled via launchd -- see com.ujpest.statsbomb.plist.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("statsbomb.pipeline")

# Sibling modules (this file's directory is on sys.path when run as a script).
from statsbomb_data_downloader import download_new_games, download_season_stats
from get_aggregate_stats_for_games import enrich


def main() -> int:
    started = datetime.now()
    log.info("=== Pipeline start (%s) ===", started.strftime("%A %Y-%m-%d %H:%M"))
    try:
        downloaded = download_new_games()
        log.info("Refreshing season stats...")
        download_season_stats()
        log.info("Enriching match + season aggregates...")
        enrich()
        log.info("=== Pipeline done: %d new game(s), took %s ===",
                 downloaded, datetime.now() - started)
        return 0
    except Exception:
        log.exception("Pipeline failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
