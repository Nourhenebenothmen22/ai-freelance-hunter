"""HTML Web Scraping Adapter using httpx, BeautifulSoup, and lxml."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from src.adapters.base import BaseSourceAdapter


class HTMLScraperAdapter(BaseSourceAdapter):
    """Adapter for structured HTML opportunity boards."""

    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.selectors = source_config.get("selectors", {})
        self.card_selector = self.selectors.get("card", ".job-card, .listing, article")
        self.title_selector = self.selectors.get("title", "h2, h3, .title")
        self.link_selector = self.selectors.get("link", "a")
        self.company_selector = self.selectors.get("company", ".company, .employer")
        self.desc_selector = self.selectors.get("description", ".description, .summary, p")

    async def search(self, queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Scrape HTML listing pages."""
        async with self.get_client() as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
            html_text = resp.text

        soup = BeautifulSoup(html_text, "lxml")
        cards = soup.select(self.card_selector)
        items: List[Dict[str, Any]] = []

        for card in cards:
            title_el = card.select_one(self.title_selector)
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            link_el = card.select_one(self.link_selector) or (card if card.name == "a" else None)
            href = link_el.get("href", "") if link_el else ""
            full_url = urljoin(self.url, href) if href else self.url

            company_el = card.select_one(self.company_selector)
            company = company_el.get_text(strip=True) if company_el else None

            desc_el = card.select_one(self.desc_selector)
            description = desc_el.get_text(separator=" ", strip=True) if desc_el else ""

            items.append({
                "title": title,
                "url": full_url,
                "company": company,
                "description": description,
            })

        return items

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize extracted HTML item."""
        title = raw_item.get("title", "")
        desc = raw_item.get("description", "")
        is_freelance = self.source_config.get("freelance", True) or bool(
            re.search(r"\b(?:freelance|contract|مستقل|عمل حر|مشروع)\b", f"{title} {desc}", re.I)
        )
        return {
            "title": title,
            "description": desc,
            "source": self.source_id,
            "source_url": raw_item.get("url", ""),
            "canonical_url": raw_item.get("url", ""),
            "company": raw_item.get("company"),
            "remote": True,
            "freelance": is_freelance,
        }
