"""Offline and System Restart Recovery Manager.

Handles detection of PC shutdowns/downtime, calculation of missed time windows,
prioritized recovery crawls, and duplicate-safe notification restoration.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, Optional, Tuple
from src.config_loader import config
from src.storage.repository import Repository

logger = logging.getLogger("AI-Freelance-Hunter.Recovery")


class RecoveryManager:
    """Detects missed operational windows and guides recovery execution."""

    def __init__(self, repository: Repository):
        self.repo = repository
        self.max_window_hours = config.max_missed_window_hours
        self.downtime_threshold_minutes = config.downtime_threshold_minutes

    def check_downtime(self) -> Tuple[bool, float, Optional[str]]:
        """
        Detects if system was offline/shut down based on last heartbeat or shutdown timestamp.
        Returns: (downtime_detected, hours_missed, last_seen_timestamp)
        """
        rec_state = self.repo.get_recovery_state()
        last_heartbeat_str = rec_state.get("last_heartbeat") or rec_state.get("last_shutdown")
        now = datetime.now(timezone.utc)

        if not last_heartbeat_str:
            logger.info("First run detected. No prior shutdown or downtime recorded.")
            self.repo.record_heartbeat()
            return False, 0.0, None

        try:
            last_time = datetime.fromisoformat(last_heartbeat_str)
            # Ensure timezone-aware
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            delta = now - last_time
            minutes_offline = delta.total_seconds() / 60.0
            hours_offline = min(delta.total_seconds() / 3600.0, self.max_window_hours)

            if minutes_offline >= self.downtime_threshold_minutes:
                logger.warning(
                    f"Downtime detected! System was offline for {hours_offline:.1f} hours "
                    f"(since {last_heartbeat_str})."
                )
                self.repo.update_recovery_state({
                    "recovery_needed": True,
                    "missed_window_start": last_heartbeat_str,
                    "hours_offline": hours_offline
                })
                return True, hours_offline, last_heartbeat_str

            return False, 0.0, last_heartbeat_str

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse recovery timestamp: {e}")
            return False, 0.0, None

    def mark_recovery_complete(self, opportunities_recovered: int) -> None:
        """Update recovery state once missed opportunities have been processed."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.repo.update_recovery_state({
            "recovery_needed": False,
            "last_recovery_at": now_iso,
            "last_recovered_count": opportunities_recovered
        })
        self.repo.record_heartbeat()
        logger.info(f"Recovery completed successfully. {opportunities_recovered} missed opportunities processed.")

    def record_clean_shutdown(self) -> None:
        """Called on SIGINT / SIGTERM for graceful shutdown."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.repo.update_recovery_state({
            "last_shutdown": now_iso,
            "clean_shutdown": True
        })
        logger.info("Clean shutdown recorded in recovery state.")
