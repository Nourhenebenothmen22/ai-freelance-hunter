"""Persistent Notification Queue.

Manages data/notifications.json to guarantee:
1. Every high-scoring opportunity is queued.
2. Failed alerts are preserved with retry count.
3. No opportunity is ever notified more than once.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.storage.atomic_fs import AtomicFS


class NotificationQueue:
    """Zero-loss persistent notification queue."""

    def __init__(self, notifications_file: str = "data/notifications.json"):
        self.file_path = Path(notifications_file)
        self.load()

    def load(self) -> Dict[str, Any]:
        data = AtomicFS.read_json(self.file_path, default={"pending": [], "sent": [], "failed": []})
        if not isinstance(data, dict):
            data = {"pending": [], "sent": [], "failed": []}
        return data

    def save(self, data: Dict[str, Any]) -> None:
        AtomicFS.write_json(self.file_path, data)

    def is_already_notified(self, opp_id: str) -> bool:
        """Check if opportunity was already sent or is already pending."""
        data = self.load()
        sent_ids = {item["id"] for item in data.get("sent", [])}
        if opp_id in sent_ids:
            return True
        pending_ids = {item["id"] for item in data.get("pending", [])}
        return opp_id in pending_ids

    def enqueue(self, opp_dict: Dict[str, Any]) -> bool:
        """Add opportunity to pending queue if not previously sent/queued."""
        opp_id = opp_dict["id"]
        if self.is_already_notified(opp_id):
            return False

        data = self.load()
        data.setdefault("pending", []).append({
            "id": opp_id,
            "opportunity": opp_dict,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
            "last_error": None
        })
        self.save(data)
        return True

    def get_pending(self) -> List[Dict[str, Any]]:
        """Retrieve all items currently awaiting delivery."""
        data = self.load()
        return data.get("pending", [])

    def mark_sent(self, opp_id: str) -> None:
        """Move item from pending to sent."""
        data = self.load()
        pending = data.get("pending", [])
        sent = data.get("sent", [])

        remaining_pending = []
        for item in pending:
            if item["id"] == opp_id:
                item["sent_at"] = datetime.now(timezone.utc).isoformat()
                sent.append(item)
            else:
                remaining_pending.append(item)

        data["pending"] = remaining_pending
        data["sent"] = sent
        self.save(data)

    def mark_failed(self, opp_id: str, error_msg: str, max_retries: int = 5) -> None:
        """Increment retry count or move to permanent failed list if retries exhausted."""
        data = self.load()
        pending = data.get("pending", [])
        failed = data.get("failed", [])

        remaining_pending = []
        for item in pending:
            if item["id"] == opp_id:
                item["retry_count"] = item.get("retry_count", 0) + 1
                item["last_error"] = error_msg
                item["last_retry_at"] = datetime.now(timezone.utc).isoformat()
                if item["retry_count"] >= max_retries:
                    failed.append(item)
                else:
                    remaining_pending.append(item)
            else:
                remaining_pending.append(item)

        data["pending"] = remaining_pending
        data["failed"] = failed
        self.save(data)
