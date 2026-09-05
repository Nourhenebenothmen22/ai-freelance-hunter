"""OpenClaw Orchestration Pipeline.

Orchestrates the complete opportunity hunting workflow:
Discovery -> Search -> Scraping -> Extraction -> Normalization -> Classification -> Scoring -> Deduplication -> Filesystem Persistence -> Telegram Notification

And the Recovery Workflow:
Startup -> Recovery Detection -> Missed Opportunity Search -> Deduplication -> Scoring -> Telegram
"""

import asyncio
from datetime import datetime, timezone
import logging
import uuid
from typing import Any, Dict, List, Optional
from src.adapters.discovery import AdapterFactory, SourceDiscoveryEngine
from src.classifier.engine import ClassificationEngine
from src.config_loader import config
from src.notifier.telegram import TelegramNotifier
from src.recovery.manager import RecoveryManager
from src.storage.repository import Repository

logger = logging.getLogger("AI-Freelance-Hunter.OpenClaw")


class OpenClawPipeline:
    """Core OpenClaw pipeline orchestrator."""

    def __init__(
        self,
        repository: Optional[Repository] = None,
        classifier: Optional[ClassificationEngine] = None,
        notifier: Optional[TelegramNotifier] = None,
        recovery: Optional[RecoveryManager] = None,
    ):
        self.repo = repository or Repository()
        self.classifier = classifier or ClassificationEngine()
        self.notifier = notifier or TelegramNotifier()
        self.recovery = recovery or RecoveryManager(self.repo)
        self.discovery = SourceDiscoveryEngine(self.repo)

    async def run_pipeline(self, is_recovery: bool = False) -> Dict[str, Any]:
        """
        Executes a complete Opportunity Hunting Cycle.
        Returns execution summary dictionary.
        """
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        start_time = datetime.now(timezone.utc)
        logger.info(f"=== Starting OpenClaw Hunter Pipeline [Run ID: {run_id}] (Recovery={is_recovery}) ===")

        # 1. Update crawl state
        self.repo.update_crawl_state({
            "status": "running",
            "last_crawl_start": start_time.isoformat(),
            "current_run_id": run_id
        })
        self.repo.record_heartbeat()

        # 2. Dynamic source discovery (periodically discovers new RSS/APIs)
        try:
            discovered_sources = await self.discovery.discover_and_evaluate()
            if discovered_sources:
                logger.info(f"Dynamic discovery added {len(discovered_sources)} new sources.")
        except Exception as e:
            logger.warning(f"Discovery phase non-fatal issue: {e}")

        # 3. Load all configured and discovered sources
        sources_list = self.repo.get_sources(default_sources=config.sources)
        active_sources = [s for s in sources_list if s.get("enabled", True)]

        total_extracted = 0
        total_new_saved = 0
        total_notified = 0
        source_results: Dict[str, Any] = {}

        # 4. Search, Scrape & Extract across modular adapters
        for src_cfg in active_sources:
            source_id = src_cfg.get("source", "unknown")
            adapter = AdapterFactory.create(src_cfg)

            # Failure isolation wrapper: an error in one source never breaks others
            raw_items, err = await adapter.run_safe()

            if err:
                self.repo.update_source_health(source_id=source_id, success=False, error_msg=err)
                source_results[source_id] = {"status": "error", "error": err, "count": 0}
                continue

            self.repo.update_source_health(source_id=source_id, success=True, items_found=len(raw_items))
            source_results[source_id] = {"status": "success", "count": len(raw_items)}
            total_extracted += len(raw_items)

            # 5. Normalize, Classify, Score, Deduplicate & Persist
            for raw in raw_items:
                try:
                    opp = self.classifier.process_raw_opportunity(raw)
                    
                    # Deduplicate and save to filesystem (opportunities.jsonl)
                    is_new = self.repo.save_opportunity(opp)
                    if is_new:
                        total_new_saved += 1
                        logger.info(
                            f"Saved new opportunity: [{opp.title}] @ [{opp.company}] "
                            f"| Score: {opp.score} | Remote: {opp.remote} | Freelance: {opp.freelance}"
                        )

                        # 6. Telegram notification for high-scoring items
                        if opp.score >= config.min_notification_score:
                            notified = await self.notifier.notify_opportunity(opp)
                            if notified:
                                total_notified += 1

                except Exception as e:
                    logger.error(f"Error classifying opportunity from {source_id}: {e}", exc_info=True)

        # 7. Drain any queued pending notifications from previous runs/offline retries
        try:
            drained_count = await self.notifier.dispatch_pending_queue()
            total_notified += drained_count
        except Exception as e:
            logger.warning(f"Error dispatching pending notifications: {e}")

        # 8. Record heartbeat and finalize crawl state
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()
        self.repo.record_heartbeat()

        summary = {
            "run_id": run_id,
            "is_recovery": is_recovery,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration_seconds, 2),
            "sources_crawled": len(active_sources),
            "total_extracted": total_extracted,
            "new_opportunities_saved": total_new_saved,
            "notifications_sent": total_notified,
            "source_results": source_results
        }

        self.repo.update_crawl_state({
            "status": "idle",
            "last_crawl_end": end_time.isoformat(),
            "last_run_summary": summary
        })
        self.repo.save_run_summary(run_id, summary)

        logger.info(
            f"=== Completed Run [{run_id}]: Extracted {total_extracted}, "
            f"New Saved {total_new_saved}, Notified {total_notified} in {duration_seconds:.1f}s ==="
        )
        return summary

    async def run_recovery_if_needed(self) -> Optional[Dict[str, Any]]:
        """Checks for previous system downtime and executes recovery crawl if needed."""
        downtime_detected, hours_offline, last_seen = self.recovery.check_downtime()
        if downtime_detected:
            logger.warning(f"Executing Recovery Cycle for {hours_offline:.1f} missed hours...")
            summary = await self.run_pipeline(is_recovery=True)
            self.recovery.mark_recovery_complete(summary.get("new_opportunities_saved", 0))
            return summary
        else:
            logger.info("No significant downtime detected. Standard operation proceeding.")
            return None
