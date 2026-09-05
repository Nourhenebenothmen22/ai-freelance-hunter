"""RSS and Atom Feed Source Adapter.

Parses public RSS/Atom feeds from open job boards and freelance communities.
Uses resilient XML/HTML parsing.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from src.adapters.base import BaseSourceAdapter


class RSSAdapter(BaseSourceAdapter):
    """Adapter for RSS 2.0 and Atom feeds."""

    async def search(self, queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch and parse RSS/Atom feed items."""
        async with self.get_client() as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
            text = resp.text

        items: List[Dict[str, Any]] = []

        # Try parsing with BeautifulSoup XML mode (tolerant to messy feeds)
        soup = BeautifulSoup(text, "xml")
        xml_items = soup.find_all("item") or soup.find_all("entry")

        for el in xml_items:
            # Extract title
            title_node = el.find("title")
            title = title_node.get_text(strip=True) if title_node else "Untitled"

            # Extract link
            link = ""
            link_node = el.find("link")
            if link_node:
                link = link_node.get("href") or link_node.get_text(strip=True)

            # Extract description / content
            desc_node = el.find("description") or el.find("content") or el.find("summary")
            description = desc_node.get_text(strip=True) if desc_node else ""

            # Extract pubDate
            pub_node = el.find("pubDate") or el.find("published") or el.find("updated")
            pub_date = pub_node.get_text(strip=True) if pub_node else None

            # Optional company tag or dc:creator
            company_node = el.find("company") or el.find("author") or el.find("creator")
            company = company_node.get_text(strip=True) if company_node else None

            # Clean HTML from description
            if description and ("<" in description and ">" in description):
                desc_soup = BeautifulSoup(description, "html.parser")
                description = desc_soup.get_text(separator=" ", strip=True)

            items.append({
                "title": title,
                "url": link,
                "description": description,
                "pub_date": pub_date,
                "company": company,
            })

        return items

    async def fetch_details(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch full job description from listing page if RSS only provides a short summary."""
        desc = raw_item.get("description", "")
        url = raw_item.get("url", "")
        if len(desc) < 150 and url and url.startswith("http"):
            try:
                async with self.get_client() as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        content_el = soup.select_one(
                            ".job-description, #job-details, article, .listing-content, .description, main"
                        )
                        if content_el:
                            full_desc = content_el.get_text(separator=" ", strip=True)
                            if len(full_desc) > len(desc):
                                raw_item["description"] = full_desc
            except Exception:
                pass  # Fall back to existing summary cleanly
        return raw_item

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert feed item into raw opportunity dictionary."""
        title = raw_item.get("title", "")
        company = raw_item.get("company")

        # Parse company from title if structured like "Company: Title" or "Title at Company"
        if not company:
            if " is hiring " in title:
                parts = title.split(" is hiring ")
                company = parts[0].strip()
                title = parts[1].strip()
            elif " at " in title:
                parts = title.split(" at ")
                title = parts[0].strip()
                company = parts[1].strip()

        return {
            "title": title,
            "description": raw_item.get("description"),
            "source": self.source_id,
            "source_url": raw_item.get("url"),
            "canonical_url": raw_item.get("url"),
            "company": company,
            "publication_date": raw_item.get("pub_date"),
            "remote": True,  # Feeds configured are predominantly remote
            "freelance": "freelance" in title.lower() or "contract" in title.lower(),
        }
