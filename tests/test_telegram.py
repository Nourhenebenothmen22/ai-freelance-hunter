"""Tests for Telegram Notifications and Persistent Queue."""

import pytest
from src.models import NormalizedOpportunity
from src.notifier.queue import NotificationQueue
from src.notifier.telegram import TelegramNotifier


@pytest.fixture
def temp_queue(tmp_path):
    q_file = tmp_path / "notifications.json"
    return NotificationQueue(notifications_file=str(q_file))


def test_telegram_message_formatting():
    opp_dict = {
        "title": "Junior Full Stack AI Developer",
        "company": "Innovate AI",
        "score": 94,
        "source": "remoteok",
        "source_url": "https://remoteok.com/job/123",
        "freelance": True,
        "remote": True,
        "remote_scope": "worldwide",
        "junior_signal": True,
        "skills": ["React", "Node.js", "RAG", "LLM"]
    }
    msg = TelegramNotifier.format_message(opp_dict)
    assert "🔥 <b>NEW OPPORTUNITY</b>" in msg
    assert "Junior Full Stack AI Developer" in msg
    assert "Score:</b> 94/100" in msg
    assert "Freelance" in msg
    assert "Remote (Worldwide)" in msg
    assert "Junior-friendly" in msg
    assert "AI:</b>" in msg
    assert "Web:</b>" in msg


def test_notification_queue_lifecycle(temp_queue):
    opp = {
        "id": "test_opp_123",
        "title": "React Developer",
        "score": 85
    }

    # 1. Enqueue
    enqueued = temp_queue.enqueue(opp)
    assert enqueued is True
    assert len(temp_queue.get_pending()) == 1

    # 2. Prevent duplicate enqueue
    dup_enqueued = temp_queue.enqueue(opp)
    assert dup_enqueued is False

    # 3. Mark as sent
    temp_queue.mark_sent("test_opp_123")
    assert len(temp_queue.get_pending()) == 0
    data = temp_queue.load()
    assert len(data.get("sent", [])) == 1

    # 4. Enqueue after sent must be rejected
    assert temp_queue.enqueue(opp) is False


def test_notification_queue_retry_and_failure(temp_queue):
    opp = {
        "id": "test_opp_fail",
        "title": "Node Dev",
        "score": 80
    }
    temp_queue.enqueue(opp)

    # Fail 2 times
    temp_queue.mark_failed("test_opp_fail", "Network Timeout", max_retries=3)
    pending = temp_queue.get_pending()
    assert len(pending) == 1
    assert pending[0]["retry_count"] == 1

    # Fail 3rd time (max retries reached)
    temp_queue.mark_failed("test_opp_fail", "Permanent 403", max_retries=2)
    assert len(temp_queue.get_pending()) == 0
    data = temp_queue.load()
    assert len(data.get("failed", [])) == 1
