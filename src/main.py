"""AI-Freelance-Hunter CLI and Service Entrypoint."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from src.adapters.discovery import AdapterFactory
from src.config_loader import config
from src.orchestration.openclaw_pipeline import OpenClawPipeline
from src.orchestration.scheduler import SchedulerDaemon
from src.storage.repository import Repository


def setup_logging(log_level: str = "INFO"):
    """Configure structured logging to console and file."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "hunter.log"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


async def cmd_run():
    """Execute a single pipeline hunting cycle."""
    pipeline = OpenClawPipeline()
    summary = await pipeline.run_pipeline()
    print("\n--- Pipeline Execution Summary ---")
    for k, v in summary.items():
        if k != "source_results":
            print(f"{k}: {v}")


async def cmd_daemon():
    """Start continuous scheduled daemon."""
    daemon = SchedulerDaemon()
    await daemon.run_forever()


async def cmd_recover():
    """Force recovery execution."""
    pipeline = OpenClawPipeline()
    summary = await pipeline.run_pipeline(is_recovery=True)
    pipeline.recovery.mark_recovery_complete(summary.get("new_opportunities_saved", 0))
    print(f"\n--- Recovery Complete: {summary.get('new_opportunities_saved', 0)} new opportunities processed ---")


async def cmd_test_sources():
    """Test connectivity and health of all configured sources."""
    repo = Repository()
    sources = repo.get_sources(default_sources=config.sources)
    print(f"\nTesting {len(sources)} sources...\n")
    for s in sources:
        adapter = AdapterFactory.create(s)
        healthy, err = await adapter.health_check()
        status = "✅ HEALTHY" if healthy else f"❌ ERROR ({err})"
        print(f"[{s.get('source')}] {s.get('name')}: {status}")


def cmd_stats():
    """Display filesystem persistence summary statistics."""
    repo = Repository()
    opps = repo.get_all_opportunities()
    crawl_state = repo.get_crawl_state()
    rec_state = repo.get_recovery_state()
    sources_health = repo.get_source_health()

    print("\n==========================================")
    print("   AI-FREELANCE-HUNTER SYSTEM STATUS")
    print("==========================================")
    print(f"Total Stored Opportunities: {len(opps)}")
    print(f"Seen URLs Tracked: {len(repo.deduplicator._seen_urls)}")
    print(f"Fingerprints Tracked: {len(repo.deduplicator._fingerprints)}")
    print(f"Last Crawl Start: {crawl_state.get('last_crawl_start')}")
    print(f"Last Heartbeat: {rec_state.get('last_heartbeat')}")
    print("\n--- Domain Breakdown ---")
    web_cnt = sum(1 for o in opps if o.get("web_signal"))
    ai_cnt = sum(1 for o in opps if o.get("ai_signal"))
    hybrid_cnt = sum(1 for o in opps if o.get("hybrid_signal"))
    py_cnt = sum(1 for o in opps if o.get("python_signal"))
    sql_cnt = sum(1 for o in opps if o.get("sql_signal") or o.get("plsql_signal"))
    junior_cnt = sum(1 for o in opps if o.get("junior_signal"))
    freelance_cnt = sum(1 for o in opps if o.get("freelance"))
    remote_cnt = sum(1 for o in opps if o.get("remote"))

    print(f"Web Development:   {web_cnt}")
    print(f"AI / Intelligent:  {ai_cnt}")
    print(f"Hybrid Web + AI:   {hybrid_cnt}")
    print(f"Python / Data:     {py_cnt}")
    print(f"SQL / PL/SQL:      {sql_cnt}")
    print(f"Junior-Friendly:   {junior_cnt}")
    print(f"Freelance / Gig:   {freelance_cnt}")
    print(f"Remote:            {remote_cnt}")

    if opps:
        print("\n--- Top Scored Opportunities ---")
        sorted_opps = sorted(opps, key=lambda x: x.get("score", 0), reverse=True)[:5]
        for o in sorted_opps:
            print(f"[{o.get('score')}/100] {o.get('title')} ({o.get('company')}) - {o.get('source')}")
    print("==========================================\n")


def main():
    parser = argparse.ArgumentParser(description="AI-Freelance-Hunter Autonomous Opportunity Hunter")
    parser.add_argument("command", choices=["run", "daemon", "recover", "test-sources", "stats"], help="Command to execute")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()
    setup_logging(args.log_level)

    if args.command == "run":
        asyncio.run(cmd_run())
    elif args.command == "daemon":
        asyncio.run(cmd_daemon())
    elif args.command == "recover":
        asyncio.run(cmd_recover())
    elif args.command == "test-sources":
        asyncio.run(cmd_test_sources())
    elif args.command == "stats":
        cmd_stats()


if __name__ == "__main__":
    main()
