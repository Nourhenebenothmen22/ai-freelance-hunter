"""Centralized, Typed, and Cascading Configuration Loader.

Cascading Resolution Order:
1. Environment variables (.env or system env) -> Highest priority
2. YAML configuration (config/*.yaml) -> Structured domain fallback
3. Typed defaults -> Zero runtime failures
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from dotenv import load_dotenv

# Load .env file at import time
load_dotenv()


class ConfigLoader:
    """Centralized configuration loader with typed getters and .env priority."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Any] = {}
        self.load_all()

    def load_all(self) -> None:
        """Load all YAML files from the configuration directory."""
        if not self.config_dir.exists():
            # Fallback to parent config if running from subfolder
            alt_dir = Path(__file__).parent.parent / "config"
            if alt_dir.exists():
                self.config_dir = alt_dir
            else:
                raise FileNotFoundError(f"Config directory not found: {self.config_dir}")

        for file_path in self.config_dir.glob("*.yaml"):
            key = file_path.stem
            with open(file_path, "r", encoding="utf-8") as f:
                self._configs[key] = yaml.safe_load(f) or {}

    def get(self, section: str, default: Any = None) -> Any:
        """Get an entire configuration file dict."""
        return self._configs.get(section, default)

    # ------------------------------------------------------------------
    # Type-safe environment variable helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_env_str(key: str, default: str = "") -> str:
        val = os.getenv(key)
        return val.strip() if val is not None else default

    @staticmethod
    def _get_env_int(key: str, default: int = 0) -> int:
        val = os.getenv(key)
        if val is not None and val.strip():
            try:
                return int(val.strip())
            except ValueError:
                pass
        return default

    @staticmethod
    def _get_env_float(key: str, default: float = 0.0) -> float:
        val = os.getenv(key)
        if val is not None and val.strip():
            try:
                return float(val.strip())
            except ValueError:
                pass
        return default

    @staticmethod
    def _get_env_bool(key: str, default: bool = False) -> bool:
        val = os.getenv(key)
        if val is not None:
            return val.strip().lower() in ("true", "1", "yes", "on", "t")
        return default

    # ------------------------------------------------------------------
    # 1. System Properties
    # ------------------------------------------------------------------
    @property
    def app_name(self) -> str:
        return self._get_env_str(
            "APP_NAME",
            self.get("system", {}).get("system", {}).get("app_name", "AI-Freelance-Hunter")
        )

    @property
    def log_level(self) -> str:
        return self._get_env_str(
            "LOG_LEVEL",
            self.get("system", {}).get("system", {}).get("log_level", "INFO")
        )

    @property
    def environment(self) -> str:
        return self._get_env_str("ENVIRONMENT", "production")

    @property
    def system(self) -> Dict[str, Any]:
        return self.get("system", {}).get("system", {})

    # ------------------------------------------------------------------
    # 2. Persistence & File Paths
    # ------------------------------------------------------------------
    @property
    def data_dir(self) -> str:
        return self._get_env_str(
            "DATA_DIR",
            self.get("system", {}).get("system", {}).get("paths", {}).get("data_dir", "data")
        )

    @property
    def logs_dir(self) -> str:
        return self._get_env_str(
            "LOGS_DIR",
            self.get("system", {}).get("system", {}).get("paths", {}).get("logs_dir", "logs")
        )

    @property
    def opportunities_file(self) -> str:
        return self._get_env_str("OPPORTUNITIES_FILE", f"{self.data_dir}/opportunities.jsonl")

    @property
    def seen_urls_file(self) -> str:
        return self._get_env_str("SEEN_URLS_FILE", f"{self.data_dir}/seen_urls.json")

    @property
    def fingerprints_file(self) -> str:
        return self._get_env_str("FINGERPRINTS_FILE", f"{self.data_dir}/fingerprints.json")

    @property
    def notifications_file(self) -> str:
        return self._get_env_str("NOTIFICATIONS_FILE", f"{self.data_dir}/notifications.json")

    @property
    def sources_file(self) -> str:
        return self._get_env_str("SOURCES_FILE", f"{self.data_dir}/sources.json")

    @property
    def crawl_state_file(self) -> str:
        return self._get_env_str("CRAWL_STATE_FILE", f"{self.data_dir}/crawl_state.json")

    @property
    def recovery_state_file(self) -> str:
        return self._get_env_str("RECOVERY_STATE_FILE", f"{self.data_dir}/recovery_state.json")

    @property
    def source_health_file(self) -> str:
        return self._get_env_str("SOURCE_HEALTH_FILE", f"{self.data_dir}/source_health.json")

    @property
    def runs_dir(self) -> str:
        return self._get_env_str("RUNS_DIR", f"{self.data_dir}/runs")

    # ------------------------------------------------------------------
    # 3. Network Settings
    # ------------------------------------------------------------------
    @property
    def network_timeout_seconds(self) -> int:
        return self._get_env_int(
            "NETWORK_TIMEOUT_SECONDS",
            self.get("system", {}).get("system", {}).get("network", {}).get("timeout_seconds", 20)
        )

    @property
    def network_max_retries(self) -> int:
        return self._get_env_int(
            "NETWORK_MAX_RETRIES",
            self.get("system", {}).get("system", {}).get("network", {}).get("max_retries", 3)
        )

    @property
    def network_backoff_factor(self) -> float:
        return self._get_env_float(
            "NETWORK_BACKOFF_FACTOR",
            float(self.get("system", {}).get("system", {}).get("network", {}).get("backoff_factor", 2.0))
        )

    @property
    def network_user_agent(self) -> str:
        default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 AI-Freelance-Hunter/1.0"
        return self._get_env_str(
            "NETWORK_USER_AGENT",
            self.get("system", {}).get("system", {}).get("network", {}).get("user_agent", default_ua)
        )

    # ------------------------------------------------------------------
    # 4. Schedules & Real-time Cadence
    # ------------------------------------------------------------------
    @property
    def schedules(self) -> Dict[str, Any]:
        """Returns schedules dict with any .env overrides applied."""
        base = dict(self.get("schedules", {}).get("schedules", {}))
        base["crawl_interval_minutes"] = self.crawl_interval_minutes
        base["jitter_seconds"] = self.jitter_seconds
        base["realtime_mode"] = self.realtime_mode
        base["recovery_on_startup"] = self.recovery_on_startup
        base["downtime_threshold_minutes"] = self.downtime_threshold_minutes
        base["max_missed_window_hours"] = self.max_missed_window_hours
        base["source_cooldown_minutes"] = self.source_cooldown_minutes
        base["healthcheck_interval_minutes"] = self.healthcheck_interval_minutes
        return base

    @property
    def crawl_interval_minutes(self) -> int:
        return self._get_env_int(
            "CRAWL_INTERVAL_MINUTES",
            self.get("schedules", {}).get("schedules", {}).get("crawl_interval_minutes", 2)
        )

    @property
    def jitter_seconds(self) -> int:
        return self._get_env_int(
            "JITTER_SECONDS",
            self.get("schedules", {}).get("schedules", {}).get("jitter_seconds", 15)
        )

    @property
    def realtime_mode(self) -> bool:
        return self._get_env_bool(
            "REALTIME_MODE",
            self.get("schedules", {}).get("schedules", {}).get("realtime_mode", True)
        )

    @property
    def recovery_on_startup(self) -> bool:
        return self._get_env_bool(
            "RECOVERY_ON_STARTUP",
            self.get("schedules", {}).get("schedules", {}).get("recovery_on_startup", True)
        )

    @property
    def downtime_threshold_minutes(self) -> float:
        return self._get_env_float(
            "DOWNTIME_THRESHOLD_MINUTES",
            float(self.get("schedules", {}).get("schedules", {}).get("downtime_threshold_minutes", 15.0))
        )

    @property
    def max_missed_window_hours(self) -> float:
        return self._get_env_float(
            "MAX_MISSED_WINDOW_HOURS",
            float(self.get("schedules", {}).get("schedules", {}).get("max_missed_window_hours", 72.0))
        )

    @property
    def source_cooldown_minutes(self) -> int:
        return self._get_env_int(
            "SOURCE_COOLDOWN_MINUTES",
            self.get("schedules", {}).get("schedules", {}).get("source_cooldown_minutes", 10)
        )

    @property
    def healthcheck_interval_minutes(self) -> int:
        return self._get_env_int(
            "HEALTHCHECK_INTERVAL_MINUTES",
            self.get("schedules", {}).get("schedules", {}).get("healthcheck_interval_minutes", 60)
        )

    # ------------------------------------------------------------------
    # 5. Freshness & Recency Filters
    # ------------------------------------------------------------------
    @property
    def freshness_max_age_hours(self) -> float:
        return self._get_env_float(
            "FRESHNESS_MAX_AGE_HOURS",
            float(self.get("filters", {}).get("freshness", {}).get("max_age_hours", 24.0))
        )

    @property
    def freshness_reject_expired(self) -> bool:
        return self._get_env_bool(
            "FRESHNESS_REJECT_EXPIRED",
            self.get("filters", {}).get("freshness", {}).get("reject_expired", True)
        )

    @property
    def freshness_realtime_window_hours(self) -> float:
        return self._get_env_float(
            "FRESHNESS_REALTIME_WINDOW_HOURS",
            float(self.get("filters", {}).get("freshness", {}).get("realtime_window_hours", 2.0))
        )

    @property
    def freshness_realtime_bonus_points(self) -> int:
        return self._get_env_int(
            "FRESHNESS_REALTIME_BONUS_POINTS",
            self.get("filters", {}).get("freshness", {}).get("realtime_bonus_points", 15)
        )

    # ------------------------------------------------------------------
    # 6. Telegram Notifications
    # ------------------------------------------------------------------
    @property
    def telegram_bot_token(self) -> str:
        return self._get_env_str("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_chat_id(self) -> str:
        return self._get_env_str("TELEGRAM_CHAT_ID", "")

    @property
    def min_notification_score(self) -> int:
        return self._get_env_int(
            "MIN_NOTIFICATION_SCORE",
            self.get("notifications", {}).get("notifications", {}).get("telegram", {}).get("min_score", 75)
        )

    @property
    def telegram_rate_limit_delay(self) -> float:
        return self._get_env_float("TELEGRAM_RATE_LIMIT_DELAY", 2.0)

    @property
    def telegram_timeout_seconds(self) -> float:
        return self._get_env_float("TELEGRAM_TIMEOUT_SECONDS", 15.0)

    @property
    def telegram_max_retries(self) -> int:
        return self._get_env_int("TELEGRAM_MAX_RETRIES", 5)

    @property
    def notifications(self) -> Dict[str, Any]:
        return self.get("notifications", {}).get("notifications", {})

    # ------------------------------------------------------------------
    # 7. Scoring Weights & Thresholds
    # ------------------------------------------------------------------
    @property
    def scoring(self) -> Dict[str, Any]:
        """Returns scoring dict with .env overrides applied."""
        base = dict(self.get("scoring", {}).get("scoring", {}))
        bonuses = dict(base.get("bonuses", {}))
        penalties = dict(base.get("penalties", {}))
        thresholds = dict(base.get("thresholds", {}))

        # Dynamic overrides for bonuses
        bonuses["ai"] = self._get_env_int("BONUS_AI", bonuses.get("ai", 25))
        bonuses["web"] = self._get_env_int("BONUS_WEB", bonuses.get("web", 20))
        bonuses["web_and_ai_hybrid"] = self._get_env_int("BONUS_HYBRID", bonuses.get("web_and_ai_hybrid", 20))
        bonuses["python_data"] = self._get_env_int("BONUS_PYTHON_DATA", bonuses.get("python_data", 20))
        bonuses["sql_plsql"] = self._get_env_int("BONUS_SQL_PLSQL", bonuses.get("sql_plsql", 15))
        bonuses["junior"] = self._get_env_int("BONUS_JUNIOR", bonuses.get("junior", 20))
        bonuses["remote"] = self._get_env_int("BONUS_REMOTE", bonuses.get("remote", 15))
        bonuses["freelance"] = self._get_env_int("BONUS_FREELANCE", bonuses.get("freelance", 15))
        bonuses["strong_skill_overlap"] = self._get_env_int("BONUS_SKILL_OVERLAP", bonuses.get("strong_skill_overlap", 15))
        bonuses["startup_sme"] = self._get_env_int("BONUS_STARTUP_SME", bonuses.get("startup_sme", 10))
        bonuses["realtime_freshness"] = self._get_env_int("FRESHNESS_REALTIME_BONUS_POINTS", bonuses.get("realtime_freshness", 15))

        # Dynamic overrides for penalties
        penalties["senior_only"] = self._get_env_int("PENALTY_SENIOR", penalties.get("senior_only", -30))
        penalties["expert_only"] = self._get_env_int("PENALTY_EXPERT", penalties.get("expert_only", -35))
        penalties["onsite_only"] = self._get_env_int("PENALTY_ONSITE", penalties.get("onsite_only", -30))
        penalties["unrelated"] = self._get_env_int("PENALTY_UNRELATED", penalties.get("unrelated", -50))
        penalties["r_only_data"] = self._get_env_int("PENALTY_R_ONLY", penalties.get("r_only_data", -50))

        # Dynamic overrides for thresholds
        thresholds["excellent_min"] = self._get_env_int("SCORE_EXCELLENT_MIN", thresholds.get("excellent_min", 90))
        thresholds["strong_min"] = self._get_env_int("SCORE_STRONG_MIN", thresholds.get("strong_min", 75))
        thresholds["relevant_min"] = self._get_env_int("SCORE_RELEVANT_MIN", thresholds.get("relevant_min", 60))
        thresholds["ignore_below"] = self._get_env_int("SCORE_IGNORE_BELOW", thresholds.get("ignore_below", 60))

        base["bonuses"] = bonuses
        base["penalties"] = penalties
        base["thresholds"] = thresholds
        return base

    # ------------------------------------------------------------------
    # Structured YAML Collections (sources, filters, rules)
    # ------------------------------------------------------------------
    @property
    def sources(self) -> List[Dict[str, Any]]:
        return self.get("sources", {}).get("sources", [])

    @property
    def filters(self) -> Dict[str, Any]:
        return self.get("filters", {})

    @property
    def profile(self) -> Dict[str, Any]:
        return self.get("profile", {}).get("profile", {})

    @property
    def roles(self) -> Dict[str, Any]:
        return self.get("roles", {}).get("domains", {})

    @property
    def technologies(self) -> Dict[str, Any]:
        return self.get("technologies", {}).get("technologies", {})

    @property
    def technology_rules(self) -> Dict[str, Any]:
        return self.get("technologies", {}).get("rules", {})

    @property
    def search_queries(self) -> Dict[str, Any]:
        return self.get("search_queries", {})

    # ------------------------------------------------------------------
    # 8. Language Selection & URL Validation
    # ------------------------------------------------------------------
    @property
    def allowed_languages(self) -> List[str]:
        env_val = self._get_env_str("ALLOWED_LANGUAGES", "")
        if env_val:
            return [lang.strip().lower() for lang in env_val.split(",") if lang.strip()]
        yaml_val = self.get("filters", {}).get("language", {}).get("allowed_languages", ["en", "fr"])
        if isinstance(yaml_val, list):
            return [str(l).strip().lower() for l in yaml_val]
        return ["en", "fr"]

    @property
    def reject_other_languages(self) -> bool:
        return self._get_env_bool(
            "REJECT_OTHER_LANGUAGES",
            self.get("filters", {}).get("language", {}).get("reject_other_languages", True)
        )

    @property
    def validate_urls_online(self) -> bool:
        return self._get_env_bool(
            "VALIDATE_URLS_ONLINE",
            self.get("filters", {}).get("url_validation", {}).get("validate_online", True)
        )

    @property
    def url_validation_timeout_seconds(self) -> float:
        return self._get_env_float(
            "URL_VALIDATION_TIMEOUT_SECONDS",
            float(self.get("filters", {}).get("url_validation", {}).get("timeout_seconds", 5.0))
        )

    @property
    def reject_invalid_urls(self) -> bool:
        return self._get_env_bool(
            "REJECT_INVALID_URLS",
            self.get("filters", {}).get("url_validation", {}).get("reject_invalid", True)
        )

    @property
    def url_cache_ttl_seconds(self) -> float:
        return self._get_env_float(
            "URL_CACHE_TTL_SECONDS",
            float(self.get("filters", {}).get("url_validation", {}).get("cache_ttl_seconds", 3600.0))
        )

    # ------------------------------------------------------------------
    # 9. Dynamic Web Search & Discovery
    # ------------------------------------------------------------------
    @property
    def web_search_queries(self) -> List[str]:
        env_val = self._get_env_str("WEB_SEARCH_QUERIES", "")
        if env_val:
            delimiter = ";" if ";" in env_val else ","
            return [q.strip() for q in env_val.split(delimiter) if q.strip()]
        for s in self.sources:
            if s.get("source") == "web_search_hunter" and "queries" in s:
                return s["queries"]
        predefined = self.get("search_queries", {}).get("predefined_high_priority_queries", [])
        if predefined:
            return predefined[:6]
        return [
            "freelance developpeur react tunisie",
            "recrutement developpeur web junior tunisie",
            "stage pfe developpeur full stack tunisie",
            "junior full stack developer remote freelance",
            "junior ai agent engineer remote",
            "remote junior react python developer"
        ]

    @property
    def web_search_max_queries(self) -> int:
        return self._get_env_int("WEB_SEARCH_MAX_QUERIES", 4)

    @property
    def web_search_max_items_per_query(self) -> int:
        return self._get_env_int("WEB_SEARCH_MAX_ITEMS_PER_QUERY", 8)

    @property
    def discovery_seeds(self) -> List[Dict[str, Any]]:
        seeds = self.get("sources", {}).get("discovery_seeds", [])
        if seeds:
            return seeds
        return [
            {"source": "jobicy", "name": "Jobicy Remote API", "url": "https://jobicy.com/api/v2/remote-jobs?count=20", "type": "json_api", "adapter": "api_adapter"},
            {"source": "weworkremotely_ai", "name": "WeWorkRemotely AI", "url": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss", "type": "rss", "adapter": "rss_adapter"},
            {"source": "authentic_jobs", "name": "Authentic Jobs Feed", "url": "https://authenticjobs.com/feed/", "type": "rss", "adapter": "rss_adapter"},
            {"source": "euremotejobs", "name": "EU Remote Jobs", "url": "https://euremotejobs.com/feed/", "type": "rss", "adapter": "rss_adapter"},
            {"source": "hn_freelance", "name": "HackerNews Freelance RSS", "url": "https://hnrss.org/whoishiring/freelance", "type": "rss", "adapter": "rss_adapter"},
        ]

    @property
    def non_tech_patterns(self) -> List[str]:
        return self.get("filters", {}).get("non_tech_signals", {}).get("patterns", [])


# Global singleton instance
config = ConfigLoader()

