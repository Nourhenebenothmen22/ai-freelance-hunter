"""Tests for Source Failure Isolation and Health Tracking."""

import pytest
from unittest.mock import AsyncMock, patch
from src.adapters.base import BaseSourceAdapter
from src.adapters.discovery import AdapterFactory
from src.storage.repository import Repository


class FailingTestAdapter(BaseSourceAdapter):
    async def search(self, queries=None):
        raise ConnectionResetError("Simulated socket disconnect")

    def normalize(self, raw_item):
        return raw_item


class WorkingTestAdapter(BaseSourceAdapter):
    async def search(self, queries=None):
        return [{"title": "Working Job", "url": "https://example.com/work"}]

    def normalize(self, raw_item):
        return {
            "title": raw_item["title"],
            "source": self.source_id,
            "source_url": raw_item["url"],
            "remote": True
        }


@pytest.mark.asyncio
async def test_failure_isolation():
    failing_cfg = {"source": "fail_src", "url": "https://fail.com", "enabled": True}
    adapter = FailingTestAdapter(failing_cfg)
    
    # run_safe must NOT throw exception
    items, err = await adapter.run_safe()
    assert items == []
    assert "Simulated socket disconnect" in err


def test_source_health_tracking(tmp_path):
    repo = Repository(data_dir=str(tmp_path / "data"))
    
    # Record success
    repo.update_source_health("source_a", success=True, items_found=5)
    health = repo.get_source_health()
    assert health["source_a"]["status"] == "healthy"
    assert health["source_a"]["success_count"] == 1
    assert health["source_a"]["total_items_extracted"] == 5

    # Record 3 failures
    repo.update_source_health("source_a", success=False, error_msg="Timeout 1")
    repo.update_source_health("source_a", success=False, error_msg="Timeout 2")
    repo.update_source_health("source_a", success=False, error_msg="Timeout 3")

    health = repo.get_source_health()
    assert health["source_a"]["status"] == "degraded"
    assert health["source_a"]["consecutive_failures"] == 3


def test_adapter_factory_creates_web_search():
    from src.adapters.web_search_adapter import WebSearchAdapter
    cfg = {"source": "web_test", "adapter": "web_search_adapter", "url": "https://news.google.com/rss"}
    adapter = AdapterFactory.create(cfg)
    assert isinstance(adapter, WebSearchAdapter)


@pytest.mark.asyncio
async def test_web_search_adapter_parsing():
    from src.adapters.web_search_adapter import WebSearchAdapter
    cfg = {"source": "web_test", "adapter": "web_search_adapter", "url": "https://news.google.com/rss"}
    adapter = WebSearchAdapter(cfg)
    
    mock_xml = """<rss version="2.0"><channel>
        <item>
            <title>Junior Full Stack React Developer - InnovateTech</title>
            <link>https://example.com/jobs/react-dev</link>
            <pubDate>Sat, 05 Sep 2026 12:00:00 GMT</pubDate>
            <description>Exciting junior opportunity working with React and Node.js.</description>
        </item>
    </channel></rss>"""

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = mock_xml
        
        items = await adapter.search(["junior full stack developer"])
        assert len(items) == 1
        assert items[0]["title"] == "Junior Full Stack React Developer"
        assert items[0]["company"] == "InnovateTech"
        assert items[0]["url"] == "https://example.com/jobs/react-dev"

        norm = adapter.normalize(items[0])
        assert norm["source"] == "web_test"
        assert norm["remote"] is True

