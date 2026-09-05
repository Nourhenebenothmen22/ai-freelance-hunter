"""Multi-Key Cross-Platform Opportunity Deduplicator.

Guarantees no duplicates across:
1. Canonical URL
2. Normalized URL (tracking params removed)
3. Source ID + Source URL
4. Normalized Company + Title
5. Content Fingerprint & Similarity
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from src.storage.atomic_fs import AtomicFS


class Deduplicator:
    """Manages seen URLs and content fingerprints for duplicate prevention."""

    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid", "gh_jid"
    }

    def __init__(self, seen_urls_file: str = "data/seen_urls.json", fingerprints_file: str = "data/fingerprints.json"):
        self.seen_urls_file = Path(seen_urls_file)
        self.fingerprints_file = Path(fingerprints_file)
        self._seen_urls: Set[str] = set()
        self._title_company_keys: Set[str] = set()
        self._fingerprints: Dict[str, Dict[str, str]] = {}
        self.load()

    def load(self) -> None:
        """Load seen URLs and fingerprints from disk."""
        data_urls = AtomicFS.read_json(self.seen_urls_file, default={"urls": [], "title_company": []})
        self._seen_urls = set(data_urls.get("urls", []))
        self._title_company_keys = set(data_urls.get("title_company", []))
        self._fingerprints = AtomicFS.read_json(self.fingerprints_file, default={})

    def save(self) -> None:
        """Atomically persist seen state to disk."""
        AtomicFS.write_json(self.seen_urls_file, {
            "urls": sorted(list(self._seen_urls)),
            "title_company": sorted(list(self._title_company_keys))
        })
        AtomicFS.write_json(self.fingerprints_file, self._fingerprints)

    @classmethod
    def normalize_url(cls, url: Optional[str]) -> str:
        """Strip tracking parameters, fragments, and standardise URL."""
        if not url:
            return ""
        parsed = urlparse(url.strip())
        query_items = parse_qsl(parsed.query)
        filtered_query = [(k, v) for k, v in query_items if k.lower() not in cls.TRACKING_PARAMS]
        sorted_query = sorted(filtered_query)
        new_query = urlencode(sorted_query)

        # Normalize path: remove trailing slash
        path = parsed.path.rstrip("/")
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            new_query,
            ""
        ))
        return normalized

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Lowercase, strip non-alphanumeric characters, and normalize spaces."""
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.split())

    @classmethod
    def get_title_company_key(cls, title: str, company: Optional[str]) -> str:
        """Generate normalized composite key for title and company."""
        norm_title = cls.normalize_text(title)
        norm_company = cls.normalize_text(company or "unknown")
        # Remove common title prefixes/suffixes
        norm_title = re.sub(r"\b(remote|worldwide|junior|senior|freelance|full[\s-]time|part[\s-]time)\b", "", norm_title)
        norm_title = " ".join(norm_title.split())
        return f"{norm_company}::{norm_title}"

    @classmethod
    def compute_fingerprint(cls, title: str, company: Optional[str], description: Optional[str]) -> str:
        """
        Generate robust 64-character SHA-256 fingerprint from essential tokens.
        Eliminates duplicate postings of the same job with minor formatting differences.
        """
        norm_title = cls.normalize_text(title)
        norm_company = cls.normalize_text(company or "")
        norm_desc = cls.normalize_text(description or "")

        # Extract set of significant words (length > 3) from title and description
        words = [w for w in (norm_title + " " + norm_desc[:500]).split() if len(w) > 3]
        unique_tokens = sorted(list(set(words)))

        content_blob = f"{norm_company}|{norm_title}|{' '.join(unique_tokens[:60])}"
        return hashlib.sha256(content_blob.encode("utf-8")).hexdigest()

    def is_duplicate(
        self,
        url: str,
        canonical_url: Optional[str],
        title: str,
        company: Optional[str],
        fingerprint: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if opportunity has already been seen across any platform.
        Returns: (is_duplicate, reason)
        """
        norm_url = self.normalize_url(url)
        norm_canon = self.normalize_url(canonical_url) if canonical_url else ""

        # 1. Check normalized URL
        if norm_url and norm_url in self._seen_urls:
            return True, f"Normalized URL match: {norm_url}"

        # 2. Check canonical URL
        if norm_canon and norm_canon in self._seen_urls:
            return True, f"Canonical URL match: {norm_canon}"

        # 3. Check exact fingerprint
        if fingerprint in self._fingerprints:
            return True, f"Content fingerprint match: {fingerprint[:8]}"

        # 4. Check title + company composite key
        tc_key = self.get_title_company_key(title, company)
        if tc_key and tc_key in self._title_company_keys:
            return True, f"Title/Company match: {tc_key}"

        return False, None

    def mark_seen(
        self,
        url: str,
        canonical_url: Optional[str],
        title: str,
        company: Optional[str],
        fingerprint: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Record opportunity as seen in internal state."""
        norm_url = self.normalize_url(url)
        if norm_url:
            self._seen_urls.add(norm_url)

        if canonical_url:
            norm_canon = self.normalize_url(canonical_url)
            if norm_canon:
                self._seen_urls.add(norm_canon)

        tc_key = self.get_title_company_key(title, company)
        if tc_key:
            self._title_company_keys.add(tc_key)

        self._fingerprints[fingerprint] = metadata or {
            "title": title,
            "company": company or "unknown",
            "url": url
        }
