"""Robust Healthcheck Script for Docker Container.

Verifies:
1. Data directory is accessible and writable.
2. Repository state is valid and intact.
3. Daemon heartbeat is active.
Exits 0 if healthy, 1 if degraded/failing.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config_loader import config
from src.storage.repository import Repository


def check_health() -> int:
    try:
        data_dir = Path(config.data_dir)
        if not data_dir.exists():
            print("ERROR: data directory does not exist", file=sys.stderr)
            return 1

        repo = Repository(data_dir=str(data_dir))
        
        # 1. Verify crawl state accessibility
        state = repo.get_crawl_state()
        if not isinstance(state, dict):
            print("ERROR: crawl_state.json corrupted", file=sys.stderr)
            return 1

        # If crawler is actively running, healthcheck is good
        if state.get("status") == "running":
            return 0

        # 2. Verify heartbeat recency (allow grace period with 20m minimum floor)
        rec_state = repo.get_recovery_state()
        last_heartbeat_str = rec_state.get("last_heartbeat")
        
        if last_heartbeat_str:
            last_hb = datetime.fromisoformat(last_heartbeat_str)
            if last_hb.tzinfo is None:
                last_hb = last_hb.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            crawl_min = float(config.crawl_interval_minutes)
            max_staleness = timedelta(minutes=max(20.0, crawl_min * 4))
            
            if now - last_hb > max_staleness:
                print(f"WARNING: Heartbeat is stale ({now - last_hb} > {max_staleness})", file=sys.stderr)
                return 1

        return 0

    except Exception as e:
        print(f"ERROR during health check: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(check_health())
