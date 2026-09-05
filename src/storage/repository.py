"""Filesystem Opportunity and State Repository.

Zero-database repository managing:
- opportunities.jsonl
- crawl_state.json
- recovery_state.json
- source_health.json
- sources.json
- runs/<timestamp>.json
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config_loader import config
from src.models import NormalizedOpportunity
from src.storage.atomic_fs import AtomicFS
from src.storage.deduplicator import Deduplicator


class Repository:
    """Central repository for all filesystem data persistence."""

    def __init__(self, data_dir: Optional[str] = None):
        target_dir = data_dir or config.data_dir
        self.data_dir = Path(target_dir)
        
        # If default data_dir, use exact configured paths (which respect .env)
        if data_dir is None or data_dir == config.data_dir:
            self.runs_dir = Path(config.runs_dir)
            self.opportunities_file = Path(config.opportunities_file)
            self.seen_urls_file = Path(config.seen_urls_file)
            self.fingerprints_file = Path(config.fingerprints_file)
            self.notifications_file = Path(config.notifications_file)
            self.sources_file = Path(config.sources_file)
            self.crawl_state_file = Path(config.crawl_state_file)
            self.recovery_state_file = Path(config.recovery_state_file)
            self.source_health_file = Path(config.source_health_file)
        else:
            # When custom data_dir is passed (e.g. in tests with tmp_path)
            self.runs_dir = self.data_dir / "runs"
            self.opportunities_file = self.data_dir / "opportunities.jsonl"
            self.seen_urls_file = self.data_dir / "seen_urls.json"
            self.fingerprints_file = self.data_dir / "fingerprints.json"
            self.notifications_file = self.data_dir / "notifications.json"
            self.sources_file = self.data_dir / "sources.json"
            self.crawl_state_file = self.data_dir / "crawl_state.json"
            self.recovery_state_file = self.data_dir / "recovery_state.json"
            self.source_health_file = self.data_dir / "source_health.json"

        # Initialize directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        self.deduplicator = Deduplicator(
            seen_urls_file=str(self.seen_urls_file),
            fingerprints_file=str(self.fingerprints_file)
        )

    def save_opportunity(self, opp: NormalizedOpportunity) -> bool:
        """
        Deduplicate and append opportunity to opportunities.jsonl.
        Returns True if newly added, False if duplicate.
        """
        is_dup, reason = self.deduplicator.is_duplicate(
            url=opp.source_url,
            canonical_url=opp.canonical_url,
            title=opp.title,
            company=opp.company,
            fingerprint=opp.fingerprint
        )
        if is_dup:
            return False

        # Mark as seen in deduplicator
        self.deduplicator.mark_seen(
            url=opp.source_url,
            canonical_url=opp.canonical_url,
            title=opp.title,
            company=opp.company,
            fingerprint=opp.fingerprint,
            metadata={"title": opp.title, "company": opp.company or "unknown", "score": str(opp.score)}
        )
        self.deduplicator.save()

        # Append to opportunities.jsonl
        AtomicFS.append_jsonl(self.opportunities_file, opp.to_dict())
        return True

    def get_all_opportunities(self) -> List[Dict[str, Any]]:
        """Read all saved opportunities."""
        return AtomicFS.read_jsonl(self.opportunities_file)

    # --- Crawl State ---
    def get_crawl_state(self) -> Dict[str, Any]:
        return AtomicFS.read_json(self.crawl_state_file, default={
            "total_crawls": 0,
            "total_opportunities_found": 0,
            "last_crawl_start": None,
            "last_crawl_end": None,
            "status": "idle"
        })

    def update_crawl_state(self, updates: Dict[str, Any]) -> None:
        state = self.get_crawl_state()
        state.update(updates)
        AtomicFS.write_json(self.crawl_state_file, state)

    # --- Recovery State ---
    def get_recovery_state(self) -> Dict[str, Any]:
        return AtomicFS.read_json(self.recovery_state_file, default={
            "last_shutdown": None,
            "last_heartbeat": None,
            "missed_window_start": None,
            "recovery_needed": False,
            "last_recovery_at": None
        })

    def update_recovery_state(self, updates: Dict[str, Any]) -> None:
        state = self.get_recovery_state()
        state.update(updates)
        AtomicFS.write_json(self.recovery_state_file, state)

    def record_heartbeat(self) -> None:
        """Update heartbeat timestamp for downtime calculation on restart."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.update_recovery_state({"last_heartbeat": now_iso})

    # --- Source Health ---
    def get_source_health(self) -> Dict[str, Any]:
        return AtomicFS.read_json(self.source_health_file, default={})

    def update_source_health(self, source_id: str, success: bool, error_msg: Optional[str] = None, items_found: int = 0) -> None:
        health_data = self.get_source_health()
        now_iso = datetime.now(timezone.utc).isoformat()

        if source_id not in health_data:
            health_data[source_id] = {
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_success": None,
                "last_failure": None,
                "last_error": None,
                "total_items_extracted": 0,
                "status": "healthy"
            }

        rec = health_data[source_id]
        if success:
            rec["success_count"] += 1
            rec["consecutive_failures"] = 0
            rec["last_success"] = now_iso
            rec["total_items_extracted"] += items_found
            rec["status"] = "healthy"
        else:
            rec["failure_count"] += 1
            rec["consecutive_failures"] += 1
            rec["last_failure"] = now_iso
            rec["last_error"] = error_msg
            if rec["consecutive_failures"] >= 3:
                rec["status"] = "degraded"
            if rec["consecutive_failures"] >= 5:
                rec["status"] = "failing"

        AtomicFS.write_json(self.source_health_file, health_data)

    # --- Sources Configuration & Dynamic Registration ---
    def get_sources(self, default_sources: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Get source list, initializing from default_sources if file does not exist."""
        sources = AtomicFS.read_json(self.sources_file, default=None)
        if sources is None or not isinstance(sources, list):
            from src.config_loader import config
            sources = default_sources if default_sources is not None else config.sources
            AtomicFS.write_json(self.sources_file, sources)
        return sources

    def save_sources(self, sources: List[Dict[str, Any]]) -> None:
        AtomicFS.write_json(self.sources_file, sources)

    def register_discovered_source(self, source_dict: Dict[str, Any]) -> bool:
        """Register a new dynamically discovered source into sources.json if not already present."""
        sources = self.get_sources()
        for s in sources:
            if s.get("url") == source_dict.get("url") or s.get("source") == source_dict.get("source"):
                return False
        sources.append(source_dict)
        self.save_sources(sources)
        return True

    # --- Runs Logging ---
    def save_run_summary(self, run_id: str, summary: Dict[str, Any]) -> None:
        run_file = self.runs_dir / f"run_{run_id}.json"
        AtomicFS.write_json(run_file, summary)
