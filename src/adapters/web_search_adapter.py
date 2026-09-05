"""Dynamic Web Search Opportunity Adapter.

Performs live search queries across the open web for Tunisian & international
freelance gigs, junior dev roles, and remote opportunities using real-time web search feeds.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from src.adapters.base import BaseSourceAdapter
from src.config_loader import config
from src.utils.url_validator import URLValidator

logger = logging.getLogger("AI-Freelance-Hunter.WebSearch")


class WebSearchAdapter(BaseSourceAdapter):
    """Adapter that executes live dynamic web searches for newly posted tech opportunities."""

    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.queries = source_config.get("queries") or config.web_search_queries

    async def search(self, queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Execute dynamic queries against live web search endpoints.
        Aggregates results into raw opportunity dicts.
        """
        active_queries = queries or self.queries
        items: List[Dict[str, Any]] = []

        headers = {
            "User-Agent": config.network_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        async with self.get_client() as client:
            for q in active_queries[:config.web_search_max_queries]:
                encoded_q = quote_plus(q)
                # Google News / Alerts live search RSS
                if "tunisie" in q.lower():
                    search_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=fr&gl=TN&ceid=TN:fr"
                else:
                    search_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"

                try:
                    resp = await client.get(search_url, headers=headers)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "xml")
                    xml_items = soup.find_all("item")

                    for item in xml_items[:config.web_search_max_items_per_query]:

                        title = item.find("title")
                        link = item.find("link")
                        pub_date = item.find("pubDate")
                        desc = item.find("description")

                        raw_title = title.get_text(strip=True) if title else ""
                        raw_link = link.get_text(strip=True) if link else ""
                        raw_date = pub_date.get_text(strip=True) if pub_date else None
                        raw_desc = desc.get_text(separator=" ", strip=True) if desc else ""

                        # Strip publisher suffix if present (e.g. "Title - Publisher")
                        company = None
                        if " - " in raw_title:
                            parts = raw_title.rsplit(" - ", 1)
                            raw_title = parts[0].strip()
                            company = parts[1].strip()

                        if raw_title and raw_link:
                            items.append({
                                "title": raw_title,
                                "url": raw_link,
                                "company": company or "Web Posting",
                                "description": raw_desc or raw_title,
                                "pub_date": raw_date,
                                "location": "Tunisia / Remote" if "tunisie" in q.lower() else "Remote",
                                "remote": True,
                                "freelance": "freelance" in q.lower()
                            })

                except Exception as e:
                    logger.debug(f"Web search query [{q}] non-fatal error: {e}")

        return items

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw web search result item."""
        is_freelance = bool(raw_item.get("freelance")) or ("freelance" in raw_item.get("title", "").lower())
        
        return {
            "title": raw_item.get("title", ""),
            "description": raw_item.get("description", ""),
            "source": self.source_id,
            "source_url": raw_item.get("url", ""),
            "canonical_url": raw_item.get("url", ""),
            "company": raw_item.get("company"),
            "location": raw_item.get("location"),
            "remote": raw_item.get("remote", True),
            "freelance": is_freelance,
            "publication_date": str(raw_item.get("pub_date") or ""),
        }
