"""Base Source Adapter Interface and Failure Isolation."""

import abc
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx
from src.config_loader import config

logger = logging.getLogger("AI-Freelance-Hunter.Adapter")


class BaseSourceAdapter(abc.ABC):
    """
    Standard adapter interface:
    search() -> fetch_details() -> normalize() -> health_check()
    """

    def __init__(self, source_config: Dict[str, Any]):
        self.config = source_config
        self.source_id = source_config.get("source", "unknown")
        self.name = source_config.get("name", self.source_id)
        self.url = source_config.get("url", "")
        self.enabled = source_config.get("enabled", True)
        self.priority = source_config.get("priority", 1)
        self.rate_limit = source_config.get("rate_limit", {})
        self.delay = self.rate_limit.get("delay_between_requests_seconds", 2)

    def get_client(self) -> httpx.AsyncClient:
        """Create standard configured httpx AsyncClient with browser User-Agent."""
        user_agent = config.network_user_agent
        timeout = config.network_timeout_seconds
        return httpx.AsyncClient(
            headers={"User-Agent": user_agent, "Accept": "application/json, application/xml, text/html, */*"},
            timeout=httpx.Timeout(timeout),
            follow_redirects=True
        )

    @abc.abstractmethod
    async def search(self, queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search or poll source for raw opportunity cards."""
        pass

    async def fetch_details(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Optional hook to fetch full job descriptions if feed only contains summaries."""
        return raw_item

    @abc.abstractmethod
    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert source-specific raw data into standard dict ready for classifier."""
        pass

    async def health_check(self) -> Tuple[bool, Optional[str]]:
        """Verify endpoint connectivity."""
        try:
            async with self.get_client() as client:
                resp = await client.head(self.url)
                if resp.status_code < 400:
                    return True, None
                # Fallback to GET with small stream if HEAD unsupported
                resp2 = await client.get(self.url)
                return (resp2.status_code < 400), f"Status {resp2.status_code}"
        except Exception as e:
            return False, str(e)

    async def run_safe(self, queries: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Executes adapter crawl with strict failure isolation.
        Errors will never crash the overall pipeline.
        """
        if not self.enabled:
            logger.info(f"Source {self.source_id} is disabled. Skipping.")
            return [], None

        try:
            logger.info(f"Crawling source [{self.name}] -> {self.url}")
            raw_items = await self.search(queries)
            normalized = []
            for item in raw_items:
                detailed = await self.fetch_details(item)
                norm_dict = self.normalize(detailed)
                if norm_dict:
                    normalized.append(norm_dict)
            await asyncio.sleep(self.delay)
            return normalized, None
        except Exception as e:
            logger.error(f"Error crawling source [{self.source_id}]: {e}", exc_info=True)
            return [], str(e)
