"""Unit Tests for URL Syntax Cleaning and Live Reachability Checking."""

from unittest.mock import AsyncMock, patch
import pytest
from src.utils.url_validator import URLValidator
from src.notifier.telegram import TelegramNotifier
from src.models import NormalizedOpportunity


def test_url_syntax_validation_and_tracking_strip():
    """Verify valid URLs pass and tracking query parameters are cleanly stripped."""
    dirty_url = (
        "https://jobs.example.com/view/12345"
        "?utm_source=linkedin&utm_medium=job_board&utm_campaign=hiring_2026&fbclid=IwAR123#apply-section"
    )
    is_valid, clean_url = URLValidator.clean_and_validate_syntax(dirty_url)
    assert is_valid is True
    assert "utm_source" not in clean_url
    assert "utm_medium" not in clean_url
    assert "fbclid" not in clean_url
    assert "#apply-section" not in clean_url
    assert clean_url == "https://jobs.example.com/view/12345"


def test_url_relative_resolution():
    """Verify relative paths are resolved when base_url is supplied."""
    rel_url = "/careers/frontend-dev"
    base = "https://weworkremotely.com/jobs"
    is_valid, resolved = URLValidator.clean_and_validate_syntax(rel_url, base_url=base)
    assert is_valid is True
    assert resolved == "https://weworkremotely.com/careers/frontend-dev"


def test_invalid_url_syntax_rejection():
    """Verify malformed and placeholder URLs are rejected."""
    assert URLValidator.clean_and_validate_syntax("")[0] is False
    assert URLValidator.clean_and_validate_syntax("#")[0] is False
    assert URLValidator.clean_and_validate_syntax("javascript:void(0)")[0] is False
    assert URLValidator.clean_and_validate_syntax("mailto:jobs@example.com")[0] is False
    assert URLValidator.clean_and_validate_syntax("not-a-valid-url")[0] is False
    assert URLValidator.clean_and_validate_syntax("http://")[0] is False


@pytest.mark.asyncio
async def test_live_url_check_success():
    """Verify 200 OK HTTP responses mark the URL as live."""
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
        mock_head.return_value.status_code = 200
        is_live, status = await URLValidator.is_live_url("https://example.com/active-job")
        assert is_live is True
        assert status == 200


@pytest.mark.asyncio
async def test_live_url_check_404_dead():
    """Verify 404 responses mark the URL as dead/unreachable."""
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
        mock_head.return_value.status_code = 404
        is_live, status = await URLValidator.is_live_url("https://example.com/dead-job-404")
        assert is_live is False
        assert status == 404


@pytest.mark.asyncio
async def test_telegram_preflight_discards_dead_url():
    """Verify TelegramNotifier preflight check blocks alerting on dead or invalid URLs."""
    notifier = TelegramNotifier()
    
    # 1. Invalid syntax URL
    opp_bad_url = {
        "title": "React Developer",
        "language": "en",
        "source_url": "#"
    }
    valid, reason = await notifier.validate_preflight(opp_bad_url)
    assert valid is False
    assert "URL is invalid" in reason

    # 2. Dead 404 URL
    opp_dead = {
        "title": "Junior Python Dev",
        "language": "en",
        "source_url": "https://example.com/dead-job"
    }
    with patch("src.utils.url_validator.URLValidator.is_live_url", new_callable=AsyncMock) as mock_live:
        mock_live.return_value = (False, 404)
        valid, reason = await notifier.validate_preflight(opp_dead)
        assert valid is False
        assert "unreachable" in reason
