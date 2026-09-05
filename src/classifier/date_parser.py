"""Date and Freshness Evaluation Engine.

Parses publication dates across multiple standards and relative expressions:
- Standard formats (ISO 8601, RFC 2822 / RSS pubDate, Unix timestamps)
- Relative expressions (English, French, Arabic/Tunisian)
- Age calculation and strict expiration/freshness determination
"""

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import re
from typing import Any, Dict, Optional, Tuple


class DateParser:
    """Robust multi-format date parser and freshness evaluator."""

    @classmethod
    def parse_date(cls, val: Any, reference_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Parse raw date value into timezone-aware UTC datetime.
        Supports ISO 8601, RFC 2822, epoch timestamps, and relative expressions.
        """
        if not val:
            return None

        now = reference_time or datetime.now(timezone.utc)

        # 1. If already datetime
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val.astimezone(timezone.utc)

        # 2. If numeric epoch timestamp (int or float)
        if isinstance(val, (int, float)):
            try:
                # Milliseconds vs seconds detection
                ts = val / 1000.0 if val > 1e11 else float(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass

        val_str = str(val).strip()
        if not val_str:
            return None

        # Check if numeric string timestamp
        if re.match(r"^\d{10,13}$", val_str):
            try:
                num = float(val_str)
                ts = num / 1000.0 if num > 1e11 else num
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass

        # 3. ISO 8601 parse (e.g. 2026-09-05T12:00:00Z, 2026-09-05 12:00:00)
        try:
            # Normalize 'Z' to '+00:00'
            iso_candidate = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass

        # 4. RFC 2822 / RSS pubDate (e.g. "Sat, 05 Sep 2026 12:00:00 +0000")
        try:
            dt = parsedate_to_datetime(val_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

        # 5. Relative text expressions (FR / EN / AR)
        lower_str = val_str.lower()

        # Immediate / Just now / À l'instant / توّا
        if any(w in lower_str for w in [
            "just now", "a moment ago", "right now",
            "à l'instant", "a l'instant", "maintenant",
            "توّا", "توا", "الآن", "لحظة"
        ]):
            return now

        # Today / Aujourd'hui / اليوم
        if any(w in lower_str for w in ["today", "aujourd'hui", "اليوم"]):
            return now - timedelta(hours=1)

        # Yesterday / Hier / البارح
        if any(w in lower_str for w in ["yesterday", "hier", "البارح", "أمس"]):
            return now - timedelta(hours=24)

        # Match minutes: "5m ago", "10 min", "il y a 3 minutes", "منذ 15 دقيقة", "قبل 5 دقائق"
        min_match = re.search(r"(?:il\s+y\s+a\s+|منذ\s+|قبل\s+)?(\d+)\s*(?:m|min|mins|minute|minutes|دقائق|دقيقة)\b", lower_str)
        if min_match:
            mins = int(min_match.group(1))
            return now - timedelta(minutes=mins)

        # Match hours: "1h ago", "2 hours", "il y a 3 heures", "منذ ساعتين", "قبل 3 ساعات"
        if "ساعتين" in lower_str:
            return now - timedelta(hours=2)
        if "ساعة" in lower_str and not re.search(r"\d+\s*ساعة", lower_str):
            return now - timedelta(hours=1)

        hr_match = re.search(r"(?:il\s+y\s+a\s+|منذ\s+|قبل\s+)?(\d+)\s*(?:h|hr|hrs|hour|hours|heure|heures|ساعات|ساعة)\b", lower_str)
        if hr_match:
            hrs = int(hr_match.group(1))
            return now - timedelta(hours=hrs)

        # Match days: "1d ago", "2 days", "il y a 2 jours", "منذ 3 أيام"
        day_match = re.search(r"(?:il\s+y\s+a\s+|منذ\s+|قبل\s+)?(\d+)\s*(?:d|day|days|jour|jours|أيام|يوم)\b", lower_str)
        if day_match:
            days = int(day_match.group(1))
            return now - timedelta(days=days)

        return None

    @classmethod
    def calculate_age_hours(cls, dt: Optional[datetime], reference_time: Optional[datetime] = None) -> Optional[float]:
        """Returns age in hours from publication to reference_time."""
        if not dt:
            return None
        now = reference_time or datetime.now(timezone.utc)
        delta = now - dt
        hours = delta.total_seconds() / 3600.0
        return max(0.0, hours)

    @classmethod
    def format_relative_time(cls, dt: Optional[datetime], reference_time: Optional[datetime] = None) -> str:
        """Format human-readable relative time string (e.g. 'À l'instant', 'Il y a 15 min', 'Il y a 2h')."""
        if not dt:
            return "Récemment"

        now = reference_time or datetime.now(timezone.utc)
        delta = now - dt
        total_seconds = int(delta.total_seconds())

        if total_seconds < 120:
            return "À l'instant (En direct)"
        elif total_seconds < 3600:
            mins = total_seconds // 60
            return f"Il y a {mins} min"
        elif total_seconds < 86400:
            hrs = total_seconds // 3600
            return f"Il y a {hrs}h"
        else:
            days = total_seconds // 86400
            return f"Il y a {days}j"

    @classmethod
    def evaluate_freshness(
        cls,
        raw_date: Any,
        max_age_hours: float = 24.0,
        realtime_window_hours: float = 2.0,
        reference_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Complete freshness assessment.
        Returns parsed date, age, fresh flag, realtime flag, expired flag, and display string.
        """
        now = reference_time or datetime.now(timezone.utc)
        parsed_dt = cls.parse_date(raw_date, reference_time=now)

        if parsed_dt is None:
            # If no publication date provided, assume published now
            parsed_dt = now
            age_hours = 0.0
        else:
            age_hours = cls.calculate_age_hours(parsed_dt, reference_time=now)

        is_realtime = (age_hours is not None) and (age_hours <= realtime_window_hours)
        is_expired = (age_hours is not None) and (age_hours > max_age_hours)
        is_fresh = not is_expired

        relative_display = cls.format_relative_time(parsed_dt, reference_time=now)

        return {
            "parsed_dt": parsed_dt,
            "iso_string": parsed_dt.isoformat(),
            "age_hours": round(age_hours, 2),
            "age_minutes": round(age_hours * 60, 1),
            "is_fresh": is_fresh,
            "is_realtime": is_realtime,
            "is_expired": is_expired,
            "relative_display": relative_display
        }
