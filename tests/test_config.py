"""Tests for Centralized Configuration and .env Overrides."""

import os
from unittest.mock import patch
import pytest
from src.config_loader import ConfigLoader, config


def test_default_config_loading():
    """Verify that default values match the configured schedules and freshness."""
    assert config.app_name == "AI-Freelance-Hunter"
    assert config.crawl_interval_minutes == 2
    assert config.freshness_max_age_hours == 24.0
    assert config.freshness_reject_expired is True
    assert config.freshness_realtime_window_hours == 2.0
    assert config.data_dir == "data"
    assert config.logs_dir == "logs"
    assert config.network_timeout_seconds == 20


def test_env_overrides_schedules(monkeypatch):
    """Verify that environment variables override schedule settings dynamically."""
    monkeypatch.setenv("CRAWL_INTERVAL_MINUTES", "5")
    monkeypatch.setenv("JITTER_SECONDS", "30")
    monkeypatch.setenv("REALTIME_MODE", "false")
    monkeypatch.setenv("DOWNTIME_THRESHOLD_MINUTES", "25.5")

    loader = ConfigLoader()
    assert loader.crawl_interval_minutes == 5
    assert loader.jitter_seconds == 30
    assert loader.realtime_mode is False
    assert loader.downtime_threshold_minutes == 25.5
    assert loader.schedules["crawl_interval_minutes"] == 5


def test_env_overrides_freshness(monkeypatch):
    """Verify that freshness parameters can be set via .env."""
    monkeypatch.setenv("FRESHNESS_MAX_AGE_HOURS", "12.5")
    monkeypatch.setenv("FRESHNESS_REJECT_EXPIRED", "true")
    monkeypatch.setenv("FRESHNESS_REALTIME_BONUS_POINTS", "25")

    loader = ConfigLoader()
    assert loader.freshness_max_age_hours == 12.5
    assert loader.freshness_reject_expired is True
    assert loader.freshness_realtime_bonus_points == 25


def test_env_overrides_telegram(monkeypatch):
    """Verify telegram parameters override via .env."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "998877")
    monkeypatch.setenv("MIN_NOTIFICATION_SCORE", "80")
    monkeypatch.setenv("TELEGRAM_RATE_LIMIT_DELAY", "3.5")
    monkeypatch.setenv("TELEGRAM_TIMEOUT_SECONDS", "25.0")
    monkeypatch.setenv("TELEGRAM_MAX_RETRIES", "8")

    loader = ConfigLoader()
    assert loader.telegram_bot_token == "test_bot_123"
    assert loader.telegram_chat_id == "998877"
    assert loader.min_notification_score == 80
    assert loader.telegram_rate_limit_delay == 3.5
    assert loader.telegram_timeout_seconds == 25.0
    assert loader.telegram_max_retries == 8


def test_env_overrides_scoring_weights(monkeypatch):
    """Verify that bonus and penalty weights can be overridden in .env."""
    monkeypatch.setenv("BONUS_AI", "40")
    monkeypatch.setenv("PENALTY_SENIOR", "-45")
    monkeypatch.setenv("SCORE_EXCELLENT_MIN", "95")

    loader = ConfigLoader()
    scoring_cfg = loader.scoring
    assert scoring_cfg["bonuses"]["ai"] == 40
    assert scoring_cfg["penalties"]["senior_only"] == -45
    assert scoring_cfg["thresholds"]["excellent_min"] == 95


def test_boolean_env_parsing(monkeypatch):
    """Test boolean parser handling true/false/1/0/yes/no."""
    monkeypatch.setenv("TEST_BOOL_1", "true")
    monkeypatch.setenv("TEST_BOOL_2", "1")
    monkeypatch.setenv("TEST_BOOL_3", "yes")
    monkeypatch.setenv("TEST_BOOL_4", "false")
    monkeypatch.setenv("TEST_BOOL_5", "0")
    monkeypatch.setenv("TEST_BOOL_6", "no")

    loader = ConfigLoader()
    assert loader._get_env_bool("TEST_BOOL_1") is True
    assert loader._get_env_bool("TEST_BOOL_2") is True
    assert loader._get_env_bool("TEST_BOOL_3") is True
    assert loader._get_env_bool("TEST_BOOL_4") is False
    assert loader._get_env_bool("TEST_BOOL_5") is False
    assert loader._get_env_bool("TEST_BOOL_6") is False


def test_env_overrides_language_and_url_validation(monkeypatch):
    """Verify that language filtering and URL validation are dynamically configurable."""
    monkeypatch.setenv("ALLOWED_LANGUAGES", "en,fr,es")
    monkeypatch.setenv("REJECT_OTHER_LANGUAGES", "false")
    monkeypatch.setenv("VALIDATE_URLS_ONLINE", "true")
    monkeypatch.setenv("URL_VALIDATION_TIMEOUT_SECONDS", "8.5")
    monkeypatch.setenv("URL_CACHE_TTL_SECONDS", "7200.0")
    monkeypatch.setenv("REJECT_INVALID_URLS", "true")

    loader = ConfigLoader()
    assert loader.allowed_languages == ["en", "fr", "es"]
    assert loader.reject_other_languages is False
    assert loader.validate_urls_online is True
    assert loader.url_validation_timeout_seconds == 8.5
    assert loader.url_cache_ttl_seconds == 7200.0
    assert loader.reject_invalid_urls is True


def test_env_overrides_web_search_and_discovery(monkeypatch):
    """Verify that web search queries and discovery seeds are loaded and configurable."""
    monkeypatch.setenv("WEB_SEARCH_QUERIES", "query one;query two;query three")
    monkeypatch.setenv("WEB_SEARCH_MAX_QUERIES", "6")
    monkeypatch.setenv("WEB_SEARCH_MAX_ITEMS_PER_QUERY", "12")

    loader = ConfigLoader()
    assert loader.web_search_queries == ["query one", "query two", "query three"]
    assert loader.web_search_max_queries == 6
    assert loader.web_search_max_items_per_query == 12
    assert len(loader.discovery_seeds) >= 4
    assert len(loader.non_tech_patterns) > 0

