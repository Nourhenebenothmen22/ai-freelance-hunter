"""Continuous Daemon Scheduler with Graceful Shutdown."""

import asyncio
import logging
import random
import signal
import sys
from typing import Optional
from src.config_loader import config
from src.orchestration.openclaw_pipeline import OpenClawPipeline

logger = logging.getLogger("AI-Freelance-Hunter.Scheduler")


class SchedulerDaemon:
    """Runs periodic hunting cycles with graceful shutdown and recovery."""

    def __init__(self, pipeline: Optional[OpenClawPipeline] = None):
        self.pipeline = pipeline or OpenClawPipeline()
        self._running = False
        self.crawl_interval_minutes = config.crawl_interval_minutes
        self.jitter_seconds = config.jitter_seconds

    def _setup_signal_handlers(self) -> None:
        """Register SIGINT and SIGTERM handlers for graceful shutdown."""
        def handle_exit(signum, frame):
            logger.info(f"Shutdown signal received ({signum}). Initiating graceful termination...")
            self._running = False
            self.pipeline.recovery.record_clean_shutdown()

        try:
            signal.signal(signal.SIGINT, handle_exit)
            signal.signal(signal.SIGTERM, handle_exit)
        except (ValueError, AttributeError):
            # Windows or non-main-thread fallback
            pass

    async def run_forever(self) -> None:
        """Start daemon loop."""
        self._running = True
        self._setup_signal_handlers()

        logger.info(f"Starting AI-Freelance-Hunter Daemon (Cycle every {self.crawl_interval_minutes}m)...")

        # Step 1: Startup Recovery check
        try:
            await self.pipeline.run_recovery_if_needed()
        except Exception as e:
            logger.error(f"Error during startup recovery check: {e}", exc_info=True)

        # Step 2: Main continuous loop
        while self._running:
            try:
                await self.pipeline.run_pipeline()
            except Exception as e:
                logger.error(f"Unexpected error in pipeline run: {e}", exc_info=True)

            if not self._running:
                break

            # Calculate sleep duration with jitter
            base_sleep = self.crawl_interval_minutes * 60
            jitter = random.randint(-self.jitter_seconds, self.jitter_seconds)
            sleep_time = max(30, base_sleep + jitter)

            logger.info(f"Sleeping for {sleep_time // 60}m {sleep_time % 60}s until next cycle...")

            # Sleep in chunks to allow fast response to SIGINT/SIGTERM
            for _ in range(sleep_time):
                if not self._running:
                    break
                await asyncio.sleep(1)

        logger.info("Scheduler daemon shut down cleanly.")
