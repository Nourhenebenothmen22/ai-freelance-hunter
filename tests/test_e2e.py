"""End-to-End Test for the Autonomous Opportunity Hunter Pipeline."""

import pytest
from unittest.mock import AsyncMock, patch
from src.classifier.engine import ClassificationEngine
from src.notifier.queue import NotificationQueue
from src.notifier.telegram import TelegramNotifier
from src.orchestration.openclaw_pipeline import OpenClawPipeline
from src.recovery.manager import RecoveryManager
from src.storage.repository import Repository


@pytest.mark.asyncio
async def test_full_pipeline_mock_execution(tmp_path):
    data_dir = tmp_path / "data"
    repo = Repository(data_dir=str(data_dir))
    classifier = ClassificationEngine()
    queue = NotificationQueue(notifications_file=str(data_dir / "notifications.json"))
    notifier = TelegramNotifier(queue=queue)
    notifier.bot_token = ""  # Ensure test queueing isolation from live network
    recovery = RecoveryManager(repo)

    pipeline = OpenClawPipeline(
        repository=repo,
        classifier=classifier,
        notifier=notifier,
        recovery=recovery
    )

    # Mock sample raw items from adapters
    sample_jobs = [
        {
            "title": "Junior Full Stack AI Engineer",
            "description": "Develop full stack web applications with React, Node.js, and RAG chatbots. Remote worldwide, freelance contract.",
            "company": "SmartSaaS",
            "source": "mock_source",
            "source_url": "https://example.com/mock-job-1",
            "remote": True,
            "freelance": True
        },
        {
            "title": "Senior Lead Architect (10+ years)",
            "description": "Enterprise lead architect. Expert only. 10+ years required.",
            "company": "BigLegacy",
            "source": "mock_source",
            "source_url": "https://example.com/mock-job-2",
            "remote": False
        },
        {
            "title": "Junior Python Data Engineer",
            "description": "ETL pipelines with Python, PostgreSQL, and Airflow. Junior friendly entry level.",
            "company": "DataWorks",
            "source": "mock_source",
            "source_url": "https://example.com/mock-job-3",
            "remote": True
        }
    ]

    # Patch discovery, adapter run_safe, and URL reachability to return mock jobs
    with patch.object(pipeline.discovery, "discover_and_evaluate", new_callable=AsyncMock) as mock_disc, \
         patch("src.adapters.base.BaseSourceAdapter.run_safe", new_callable=AsyncMock) as mock_run_safe, \
         patch("src.utils.url_validator.URLValidator.is_live_url", new_callable=AsyncMock) as mock_url:
        mock_disc.return_value = []
        mock_run_safe.return_value = (sample_jobs, None)
        mock_url.return_value = (True, 200)
        summary = await pipeline.run_pipeline()

    # Verify pipeline execution results
    assert summary["total_extracted"] > 0
    assert summary["new_opportunities_saved"] >= 3

    # Check persistence in filesystem opportunities.jsonl
    opps = repo.get_all_opportunities()
    assert len(opps) == 3

    # The AI Junior Full Stack should have highest score
    top_opp = next(o for o in opps if "AI" in o["title"])
    assert top_opp["score"] >= 85
    assert top_opp["hybrid_signal"] is True
    assert top_opp["freelance"] is True

    # The Senior Architect should have low score
    senior_opp = next(o for o in opps if "Senior" in o["title"])
    assert senior_opp["score"] < 50

    # The Python Data Engineer should have solid score
    py_opp = next(o for o in opps if "Python" in o["title"])
    assert py_opp["score"] >= 65
    assert py_opp["python_signal"] is True

    # Verify notification queue has the top scoring opportunity
    pending = queue.get_pending()
    assert any(p["opportunity"]["id"] == top_opp["id"] for p in pending)
