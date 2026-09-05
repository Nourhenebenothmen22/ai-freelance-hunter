"""Telegram Alert Dispatcher with Persistent Queue and Retry Logic."""

import asyncio
import html
import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx

from src.classifier.language_detector import LanguageDetector
from src.config_loader import config
from src.models import NormalizedOpportunity
from src.notifier.queue import NotificationQueue
from src.utils.url_validator import URLValidator

logger = logging.getLogger("AI-Freelance-Hunter.Telegram")


class TelegramNotifier:
    """Delivers opportunity alerts to Telegram chat with zero message loss."""

    def __init__(self, queue: Optional[NotificationQueue] = None):
        self.queue = queue or NotificationQueue()
        self.bot_token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.min_score = config.min_notification_score
        self.timeout = config.telegram_timeout_seconds
        self.rate_limit_delay = config.telegram_rate_limit_delay
        self.max_retries = config.telegram_max_retries

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    @staticmethod
    def format_message(opp: Dict[str, Any]) -> str:
        """Format rich Telegram alert matching project specification."""
        title = html.escape(opp.get("title") or "Opportunity")
        company = html.escape(opp.get("company") or "")
        company_str = f"🏢 <b>{company}</b>\n" if company else ""

        score = opp.get("score", 0)
        source = html.escape(opp.get("source") or "Unknown")
        apply_url = opp.get("source_url") or opp.get("canonical_url") or "#"

        contract_str = "Freelance" if opp.get("freelance") else (opp.get("contract_type") or "Contract / Full-time")
        
        # Location / Remote
        if opp.get("remote"):
            scope = opp.get("remote_scope") or "worldwide"
            loc_str = f"Remote ({scope.capitalize()})"
        else:
            loc_str = opp.get("location") or "On-site"

        # Junior label
        level_str = "Junior-friendly" if opp.get("junior_signal") else (opp.get("experience_level") or "Entry / Junior")

        # Tech breakdown
        skills = opp.get("skills", [])
        web_skills = [s for s in skills if s in ["React", "Next.js", "Node.js", "Express", "MERN", "JavaScript", "TypeScript"]]
        ai_skills = [s for s in skills if s in ["RAG", "LLM", "LangChain", "LlamaIndex", "OpenAI", "AI Agent", "Chatbot", "Machine Learning"]]
        data_skills = [s for s in skills if s in ["Python", "Pandas", "ETL", "FastAPI", "SQL", "PL/SQL", "Oracle", "PostgreSQL"]]

        tech_lines = []
        if ai_skills:
            tech_lines.append(f"🤖 <b>AI:</b> {', '.join(ai_skills[:4])}")
        if web_skills:
            tech_lines.append(f"💻 <b>Web:</b> {', '.join(web_skills[:4])}")
        if data_skills and not ai_skills:
            tech_lines.append(f"📊 <b>Data:</b> {', '.join(data_skills[:4])}")

        tech_summary = "\n".join(tech_lines)
        if tech_summary:
            tech_summary = f"{tech_summary}\n"

        is_realtime = opp.get("is_realtime", False)
        header_str = "⚡ <b>NOUVELLE OPPORTUNITÉ (EN DIRECT)</b>" if is_realtime else "🔥 <b>NEW OPPORTUNITY</b>"
        
        rel_time = opp.get("relative_time")
        time_str = f"⏱️ <b>Publié :</b> {html.escape(rel_time, quote=False)}\n" if rel_time else ""

        message = (
            f"{header_str}\n\n"
            f"<b>{title}</b>\n"
            f"{company_str}"
            f"{time_str}"
            f"🎯 <b>Score:</b> {score}/100\n"
            f"💼 {contract_str}\n"
            f"🌍 {loc_str}\n"
            f"👨💻 {level_str}\n\n"
            f"{tech_summary}"
            f"📌 <b>Source:</b> {source}\n"
            f"🔗 <a href=\"{apply_url}\">Apply / View Details</a>"
        )
        return message

    async def send_single(self, text: str) -> bool:
        """Send message via Telegram Bot API."""
        if not self.is_configured:
            logger.debug("Telegram credentials not configured. Skipping live network dispatch.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                return False

    async def validate_preflight(self, opp_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that the opportunity meets language requirements and has a functional, live URL.
        Returns (is_valid, rejection_reason).
        """
        # 1. Language validation
        lang = opp_dict.get("language") or "en"
        if config.reject_other_languages and not LanguageDetector.is_allowed(lang, config.allowed_languages):
            return False, f"Language '{lang}' is not in allowed list {config.allowed_languages}"

        # 2. URL syntax validation
        url = opp_dict.get("source_url") or opp_dict.get("canonical_url") or ""
        is_valid_syntax, cleaned_url = URLValidator.clean_and_validate_syntax(url)
        if not is_valid_syntax and config.reject_invalid_urls:
            return False, "Opportunity URL is invalid or malformed"

        # 3. Live URL reachability check
        if config.validate_urls_online and is_valid_syntax:
            is_live, status = await URLValidator.is_live_url(
                cleaned_url,
                timeout=config.url_validation_timeout_seconds
            )
            if not is_live and config.reject_invalid_urls:
                return False, f"Opportunity URL {cleaned_url} is unreachable (HTTP {status})"

        return True, ""

    async def notify_opportunity(self, opp: NormalizedOpportunity) -> bool:
        """Enqueue opportunity and attempt immediate delivery if score >= min_score."""
        if opp.score < self.min_score:
            return False

        opp_dict = opp.to_dict()

        # Strict preflight check: language and live URL reachability
        valid, reason = await self.validate_preflight(opp_dict)
        if not valid:
            logger.info(f"Skipping notification for [{opp.title}]: {reason}")
            return False

        queued = self.queue.enqueue(opp_dict)
        if not queued:
            logger.debug(f"Opportunity {opp.id} already alerted or pending. Skipping.")
            return False

        # Attempt immediate dispatch if configured
        if self.is_configured:
            msg_text = self.format_message(opp_dict)
            try:
                success = await self.send_single(msg_text)
                if success:
                    self.queue.mark_sent(opp.id)
                    logger.info(f"Successfully notified Telegram for [{opp.title}] (Score: {opp.score})")
                    return True
                else:
                    self.queue.mark_failed(opp.id, "Telegram API returned non-200 status", max_retries=self.max_retries)
            except Exception as e:
                logger.warning(f"Failed to dispatch Telegram message for {opp.id}: {e}")
                self.queue.mark_failed(opp.id, str(e), max_retries=self.max_retries)
        else:
            logger.info(f"Opportunity {opp.id} saved in pending notifications queue (Telegram unconfigured).")

        return False

    async def dispatch_pending_queue(self) -> int:
        """Process and send all queued pending notifications."""
        if not self.is_configured:
            return 0

        pending_items = self.queue.get_pending()
        if not pending_items:
            return 0

        logger.info(f"Processing {len(pending_items)} pending Telegram notifications...")
        sent_count = 0

        for item in pending_items:
            opp_id = item["id"]
            opp_dict = item["opportunity"]

            # Re-verify language and URL before sending queued item
            valid, reason = await self.validate_preflight(opp_dict)
            if not valid:
                logger.info(f"Discarding queued notification {opp_id}: {reason}")
                self.queue.mark_failed(opp_id, f"Preflight rejected: {reason}", max_retries=1)
                continue

            msg_text = self.format_message(opp_dict)

            try:
                success = await self.send_single(msg_text)
                if success:
                    self.queue.mark_sent(opp_id)
                    sent_count += 1
                    logger.info(f"Dispatched queued notification {opp_id}")
                    await asyncio.sleep(self.rate_limit_delay)
                else:
                    self.queue.mark_failed(opp_id, "HTTP status error during queue dispatch", max_retries=self.max_retries)
            except Exception as e:
                logger.error(f"Error dispatching queued notification {opp_id}: {e}")
                self.queue.mark_failed(opp_id, str(e), max_retries=self.max_retries)

        return sent_count

