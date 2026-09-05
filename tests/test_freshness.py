"""Tests for Real-time Freshness Evaluation and Stale Rejection."""

from datetime import datetime, timezone, timedelta
import pytest
from src.classifier.date_parser import DateParser
from src.classifier.engine import ClassificationEngine
from src.classifier.scoring import Scorer
from src.notifier.telegram import TelegramNotifier


def test_date_parser_standards():
    ref_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)

    # ISO 8601
    dt_iso = DateParser.parse_date("2026-09-05T11:45:00Z", reference_time=ref_time)
    assert dt_iso is not None
    assert dt_iso.minute == 45
    assert dt_iso.hour == 11

    # RFC 2822
    dt_rfc = DateParser.parse_date("Sat, 05 Sep 2026 11:30:00 +0000", reference_time=ref_time)
    assert dt_rfc is not None
    assert dt_rfc.minute == 30

    # Epoch timestamp
    ts = ref_time.timestamp() - 600  # 10 minutes ago
    dt_ts = DateParser.parse_date(ts, reference_time=ref_time)
    assert dt_ts is not None
    assert dt_ts.minute == 50


def test_relative_date_parser_multilingual():
    ref_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)

    # English
    dt_en_min = DateParser.parse_date("5m ago", reference_time=ref_time)
    assert dt_en_min == ref_time - timedelta(minutes=5)

    dt_en_hr = DateParser.parse_date("2 hours ago", reference_time=ref_time)
    assert dt_en_hr == ref_time - timedelta(hours=2)

    dt_en_now = DateParser.parse_date("just now", reference_time=ref_time)
    assert dt_en_now == ref_time

    # French
    dt_fr_min = DateParser.parse_date("il y a 15 minutes", reference_time=ref_time)
    assert dt_fr_min == ref_time - timedelta(minutes=15)

    dt_fr_instant = DateParser.parse_date("à l'instant", reference_time=ref_time)
    assert dt_fr_instant == ref_time

    dt_fr_hr = DateParser.parse_date("il y a 3 heures", reference_time=ref_time)
    assert dt_fr_hr == ref_time - timedelta(hours=3)

    # Arabic / Tunisian
    dt_ar_min = DateParser.parse_date("منذ 10 دقائق", reference_time=ref_time)
    assert dt_ar_min == ref_time - timedelta(minutes=10)

    dt_ar_now = DateParser.parse_date("توّا", reference_time=ref_time)
    assert dt_ar_now == ref_time


def test_freshness_evaluation_fresh_vs_expired():
    ref_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)

    # Brand new: 5 minutes ago
    fresh_5m = DateParser.evaluate_freshness(
        "5m ago",
        max_age_hours=24.0,
        realtime_window_hours=2.0,
        reference_time=ref_time
    )
    assert fresh_5m["is_fresh"] is True
    assert fresh_5m["is_realtime"] is True
    assert fresh_5m["is_expired"] is False
    assert "Il y a 5 min" in fresh_5m["relative_display"]

    # 4 hours old: fresh (< 24h) but not realtime (> 2h)
    fresh_4h = DateParser.evaluate_freshness(
        "il y a 4 heures",
        max_age_hours=24.0,
        realtime_window_hours=2.0,
        reference_time=ref_time
    )
    assert fresh_4h["is_fresh"] is True
    assert fresh_4h["is_realtime"] is False
    assert fresh_4h["is_expired"] is False
    assert "Il y a 4h" in fresh_4h["relative_display"]

    # Expired: 3 days ago (> 24h)
    expired_3d = DateParser.evaluate_freshness(
        "3 days ago",
        max_age_hours=24.0,
        realtime_window_hours=2.0,
        reference_time=ref_time
    )
    assert expired_3d["is_fresh"] is False
    assert expired_3d["is_realtime"] is False
    assert expired_3d["is_expired"] is True


def test_expired_opportunity_scoring_rejection():
    engine = ClassificationEngine()

    # Brand-new junior job
    raw_fresh = {
        "title": "Junior Full Stack Developer",
        "company": "TechStart",
        "source": "remoteok",
        "source_url": "https://remoteok.com/job/fresh",
        "description": "React and Node.js junior developer. Remote work.",
        "publication_date": "just now",
        "remote": True
    }
    opp_fresh = engine.process_raw_opportunity(raw_fresh)
    assert opp_fresh.is_fresh is True
    assert opp_fresh.is_realtime is True
    assert opp_fresh.score >= 75  # High score, qualified for alert

    # Outdated job from 15 days ago (should be rejected/suppressed)
    raw_old = {
        "title": "Junior Full Stack Developer",
        "company": "OldCorp",
        "source": "remoteok",
        "source_url": "https://remoteok.com/job/old",
        "description": "React and Node.js junior developer. Remote work.",
        "publication_date": "15 days ago",
        "remote": True
    }
    opp_old = engine.process_raw_opportunity(raw_old)
    assert opp_old.is_fresh is False
    assert opp_old.is_realtime is False
    # Score must be capped below 60 so it is completely ignored and never alerted
    assert opp_old.score < 60


def test_realtime_telegram_alert_badge():
    opp_realtime = {
        "title": "React Freelance Mission",
        "company": "StartUp Hub",
        "score": 92,
        "source": "facebook_freelance_tn",
        "source_url": "https://facebook.com/groups/freelance/post/1",
        "freelance": True,
        "remote": True,
        "junior_signal": True,
        "is_realtime": True,
        "relative_time": "À l'instant (En direct)",
        "skills": ["React", "TypeScript"]
    }
    msg = TelegramNotifier.format_message(opp_realtime)
    assert "⚡ <b>NOUVELLE OPPORTUNITÉ (EN DIRECT)</b>" in msg
    assert "⏱️ <b>Publié :</b> À l'instant (En direct)" in msg
    assert "React Freelance Mission" in msg
