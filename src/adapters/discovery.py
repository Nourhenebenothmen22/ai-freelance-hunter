"""Dynamic Source Discovery and Adapter Factory.

Discovers new public feeds/boards and dynamically registers healthy sources into data/sources.json.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from src.adapters.api_adapter import APIAdapter
from src.adapters.base import BaseSourceAdapter
from src.adapters.facebook_adapter import FacebookGroupAdapter
from src.adapters.html_adapter import HTMLScraperAdapter
from src.adapters.rss_adapter import RSSAdapter
from src.adapters.web_search_adapter import WebSearchAdapter
from src.config_loader import config
from src.storage.repository import Repository

logger = logging.getLogger("AI-Freelance-Hunter.Discovery")


class AdapterFactory:
    """Instantiates the appropriate source adapter based on configuration."""

    @staticmethod
    def create(source_cfg: Dict[str, Any]) -> BaseSourceAdapter:
        adapter_type = source_cfg.get("adapter", "rss_adapter")
        if adapter_type == "rss_adapter":
            return RSSAdapter(source_cfg)
        elif adapter_type == "api_adapter":
            return APIAdapter(source_cfg)
        elif adapter_type == "html_adapter":
            return HTMLScraperAdapter(source_cfg)
        elif adapter_type == "facebook_adapter":
            return FacebookGroupAdapter(source_cfg)
        elif adapter_type == "web_search_adapter":
            return WebSearchAdapter(source_cfg)
        # Default fallback to RSS
        return RSSAdapter(source_cfg)


class SourceDiscoveryEngine:
    """Discovers public opportunity sources (RSS/APIs/Boards) and registers them."""

    def __init__(self, repository: Repository):
        self.repo = repository

    async def discover_and_evaluate(self) -> List[Dict[str, Any]]:
        """Evaluate seed candidates and discover RSS links from target sites."""
        discovered: List[Dict[str, Any]] = []
        candidates = config.discovery_seeds

        for candidate in candidates:

            source_cfg = {
                "source": candidate["source"],
                "name": candidate["name"],
                "url": candidate["url"],
                "type": candidate["type"],
                "enabled": True,
                "priority": 2,
                "adapter": candidate["adapter"],
                "search_strategy": "feed_filter",
                "rate_limit": {"requests_per_minute": 15, "delay_between_requests_seconds": 3},
                "pagination": {"supported": False, "max_pages": 1},
                "health": "healthy",
                "last_success": None,
                "last_failure": None,
            }
            # Health check before registering
            adapter = AdapterFactory.create(source_cfg)
            is_healthy, err = await adapter.health_check()
            if is_healthy:
                added = self.repo.register_discovered_source(source_cfg)
                if added:
                    logger.info(f"Dynamically discovered & registered healthy source: {candidate['name']}")
                    discovered.append(source_cfg)
            else:
                logger.warning(f"Candidate source {candidate['name']} unreachable ({err}), skipping.")

        return discovered
