"""URL Cleaner, Structural Validator, and Asynchronous Live Reachability Checker.

Ensures every opportunity provided to the user has a functional, clean, and
reachable URL, stripping unwanted tracking parameters and discarding dead links (404/410/DNS failure).
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import httpx

logger = logging.getLogger("AI-Freelance-Hunter.URLValidator")


class URLValidator:
    """Validates URL structure, sanitizes tracking noise, and checks live reachability."""

    TRACKING_PARAMS: Set[str] = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "ref", "source", "campaign", "sender", "mc_eid"
    }

    # In-memory cache for live verification: url -> (is_live, status_code, timestamp)
    _LIVE_CACHE: Dict[str, Tuple[bool, Optional[int], float]] = {}

    @classmethod
    def get_cache_ttl(cls) -> float:
        try:
            from src.config_loader import config
            return config.url_cache_ttl_seconds
        except Exception:
            return 3600.0

    @classmethod
    def clean_and_validate_syntax(cls, url: Optional[str], base_url: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate URL syntax and remove tracking junk parameters.
        Returns (is_valid, sanitized_url).
        """
        if not url or not isinstance(url, str):
            return False, ""

        raw = url.strip()
        if not raw or raw == "#" or raw.startswith("javascript:") or raw.startswith("mailto:"):
            return False, ""

        # Resolve relative URLs against base_url if provided
        if base_url and not (raw.startswith("http://") or raw.startswith("https://")):
            raw = urljoin(base_url, raw)

        try:
            parsed = urlparse(raw)
        except Exception:
            return False, ""

        # Check scheme
        if parsed.scheme.lower() not in ("http", "https"):
            return False, ""

        # Check hostname / netloc
        netloc = parsed.netloc.strip().lower()
        if not netloc or "." not in netloc or " " in netloc:
            return False, ""

        # Clean tracking query parameters
        clean_query = ""
        if parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=False)
            filtered_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in cls.TRACKING_PARAMS
            }
            clean_query = urlencode(filtered_params, doseq=True)

        cleaned_url = urlunparse((
            parsed.scheme.lower(),
            netloc,
            parsed.path,
            parsed.params,
            clean_query,
            ""  # Strip fragment (#) to keep apply links direct
        ))

        return True, cleaned_url

    @classmethod
    async def is_live_url(
        cls,
        url: str,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if the URL is reachable online via asynchronous HTTP HEAD (fallback to GET).
        Returns (is_live, status_code).
        """
        is_valid, cleaned_url = cls.clean_and_validate_syntax(url)
        if not is_valid:
            return False, None

        # Check memory cache
        now = time.time()
        if cleaned_url in cls._LIVE_CACHE:
            cached_live, cached_status, cached_time = cls._LIVE_CACHE[cleaned_url]
            if (now - cached_time) < cls.get_cache_ttl():
                return cached_live, cached_status

        # Resolve config-driven timeout and user-agent
        resolved_timeout = timeout
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        try:
            from src.config_loader import config
            if resolved_timeout is None:
                resolved_timeout = config.url_validation_timeout_seconds
            user_agent = config.network_user_agent
        except Exception:
            if resolved_timeout is None:
                resolved_timeout = 5.0

        req_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        if headers:
            req_headers.update(headers)

        is_live = False
        status_code = None

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=req_headers,
                verify=False  # Avoid rejecting self-signed or minor SSL edge cases
            ) as client:
                # 1. Try lightweight HEAD request
                try:
                    resp = await client.head(cleaned_url)
                    status_code = resp.status_code
                    if status_code in (200, 201, 202, 204, 301, 302, 303, 307, 308):
                        is_live = True
                    elif status_code in (405, 403, 400):
                        # Some servers block HEAD or demand full GET
                        resp_get = await client.get(cleaned_url)
                        status_code = resp_get.status_code
                        # Even if 403 / Cloudflare challenge, the URL exists and is live
                        is_live = status_code in (200, 201, 202, 204, 301, 302, 303, 307, 308, 403)
                    elif status_code in (404, 410):
                        is_live = False
                except (httpx.RequestError, httpx.HTTPStatusError):
                    # Fallback to GET stream
                    try:
                        resp_get = await client.get(cleaned_url)
                        status_code = resp_get.status_code
                        is_live = status_code in (200, 201, 202, 204, 301, 302, 303, 307, 308, 403)
                    except Exception:
                        is_live = False

        except Exception as e:
            logger.debug(f"URL live check failed for {cleaned_url}: {e}")
            is_live = False

        cls._LIVE_CACHE[cleaned_url] = (is_live, status_code, now)
        return is_live, status_code
