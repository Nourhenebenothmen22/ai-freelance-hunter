"""Facebook Public Groups Scraper Adapter.

Scrapes public freelance and tech job groups (e.g. Tunisian freelance groups,
IT developer communities, PFE projects) with contact info extraction
(Phone, WhatsApp, Email) and strict failure isolation.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from src.adapters.base import BaseSourceAdapter

logger = logging.getLogger("AI-Freelance-Hunter.Facebook")


class FacebookGroupAdapter(BaseSourceAdapter):
    """Adapter for scraping public Facebook groups and community feeds."""

    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.group_id = source_config.get("group_id", "")
        self.group_name = source_config.get("group_name", self.name)

    @staticmethod
    def extract_contacts(text: str) -> Dict[str, List[str]]:
        """Extract phone numbers, emails, and WhatsApp links from post text."""
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        
        # Tunisian and international phone patterns (e.g. +216 20 123 456, 98 123 456, etc.)
        phones = re.findall(r"(?:\+?216\s*)?[2459]\d[\s.-]?\d{3}[\s.-]?\d{3}\b", text)
        
        # WhatsApp links
        wa_links = re.findall(r"(?:https?://)?(?:wa\.me|api\.whatsapp\.com/send\?phone=)\S+", text)

        return {
            "emails": list(set(emails)),
            "phones": list(set(phones)),
            "whatsapp": list(set(wa_links)),
        }

    async def search(self, queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch public posts from target group URL.
        Uses lightweight mobile web / public preview headers.
        """
        items: List[Dict[str, Any]] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            async with self.get_client() as client:
                resp = await client.get(self.url, headers=headers)
                
                # Check for login redirection or restrictions
                if "login" in str(resp.url).lower() or resp.status_code in [301, 302, 403]:
                    logger.info(
                        f"Facebook group [{self.name}] requires authentication or redirected to login wall. "
                        f"Skipping gracefully via failure isolation."
                    )
                    return []

                html_text = resp.text
                soup = BeautifulSoup(html_text, "html.parser")

                # Parse post elements from public HTML / feed
                posts = soup.select("article, div[role='article'], .userContentWrapper, div.story_body_container")
                if not posts:
                    # Fallback to general content containers if Facebook rendered simplified markup
                    posts = soup.select("div[data-testid='post_message'], div.feed, div._5pcr")

                for idx, post in enumerate(posts[:25]):
                    text = post.get_text(separator="\n", strip=True)
                    if not text or len(text) < 30:
                        continue

                    # Extract permalink or post link if available
                    link_node = post.select_one("a[href*='/permalink/'], a[href*='/posts/'], a[href*='story_fbid']")
                    post_url = link_node.get("href", "") if link_node else f"{self.url}#post-{idx}"
                    if post_url.startswith("/"):
                        post_url = f"https://www.facebook.com{post_url}"

                    # Extract author if available
                    author_node = post.select_one("strong, h3, h4, .actor")
                    author = author_node.get_text(strip=True) if author_node else "Client / Membre"

                    # First meaningful line as title
                    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
                    title = lines[0] if lines else f"Opportunité {self.name}"
                    if len(title) > 90:
                        title = title[:87] + "..."

                    # Extract timestamp / relative time
                    pub_date = None
                    abbr_node = post.select_one("abbr[data-utime], abbr, time, span.timestamp")
                    if abbr_node:
                        pub_date = abbr_node.get("data-utime") or abbr_node.get("title") or abbr_node.get_text(strip=True)
                    if not pub_date:
                        for l in lines[:4]:
                            if re.search(r"\b(?:\d+\s*(?:m|min|mins|h|hr|hrs|d|day)|hier|yesterday|just now|à l'instant|منذ|توّا)\b", l, re.I):
                                pub_date = l.strip()
                                break

                    items.append({
                        "title": title,
                        "description": text,
                        "url": post_url,
                        "author": author,
                        "pub_date": pub_date,
                    })

        except Exception as e:
            logger.warning(f"Notice: Facebook public fetch for [{self.name}] encounter: {e}")

        return items

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Facebook group post with contacts extraction."""
        text = raw_item.get("description", "")
        title = raw_item.get("title", "")
        author = raw_item.get("author", "Client")
        url = raw_item.get("url", self.url)

        contacts = self.extract_contacts(text)
        contact_str = ""
        if contacts["emails"]:
            contact_str += f" | Email: {', '.join(contacts['emails'])}"
        if contacts["phones"]:
            contact_str += f" | Tél: {', '.join(contacts['phones'])}"
        if contacts["whatsapp"]:
            contact_str += f" | WhatsApp: {', '.join(contacts['whatsapp'])}"

        full_desc = f"{text}\n\n[Coordonnées de contact direct: {contact_str.strip(' |')}]" if contact_str else text

        # Check for Tunisian location indicators
        is_tunisia = bool(
            re.search(r"\b(?:tunisie|tunisia|tunis|sfax|sousse|ariana|monastir|nabeul|\+216)\b", text, re.I)
        )
        location = "Tunisia / Remote" if is_tunisia else "Remote"

        # Check freelance indicators in Arabic/French/English
        is_freelance = bool(
            re.search(
                r"\b(?:freelance|projet|mission|besoin|cherche\s+développeur|recherche\s+développeur|contract|prestataire|pfe)\b",
                f"{title} {text}",
                re.I
            )
        )

        return {
            "title": title,
            "description": full_desc,
            "source": self.source_id,
            "source_url": url,
            "canonical_url": url,
            "company": f"{author} ({self.group_name})",
            "client": author,
            "location": location,
            "remote": True,
            "freelance": is_freelance,
            "publication_date": raw_item.get("pub_date"),
        }
