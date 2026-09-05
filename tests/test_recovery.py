"""Tests for Offline and System Restart Recovery."""

from datetime import datetime, timezone, timedelta
import pytest
from src.recovery.manager import RecoveryManager
from src.storage.repository import Repository


@pytest.fixture
def temp_repo(tmp_path):
    return Repository(data_dir=str(tmp_path / "data"))


def test_downtime_detection(temp_repo):
    recovery_mgr = RecoveryManager(temp_repo)
    
    # Simulate a downtime of 6 hours ago
    past_time = datetime.now(timezone.utc) - timedelta(hours=6)
    temp_repo.update_recovery_state({
        "last_heartbeat": past_time.isoformat(),
        "clean_shutdown": True
    })

    downtime_detected, hours_missed, last_seen = recovery_mgr.check_downtime()
    assert downtime_detected is True
    assert 5.9 <= hours_missed <= 6.1
    assert last_seen == past_time.isoformat()


def test_no_downtime_when_heartbeat_recent(temp_repo):
    recovery_mgr = RecoveryManager(temp_repo)
    
    # Heartbeat 5 minutes ago
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    temp_repo.update_recovery_state({
        "last_heartbeat": recent_time.isoformat()
    })

    downtime_detected, hours_missed, _ = recovery_mgr.check_downtime()
    assert downtime_detected is False
    assert hours_missed == 0.0


def test_recovery_completion(temp_repo):
    recovery_mgr = RecoveryManager(temp_repo)
    recovery_mgr.mark_recovery_complete(opportunities_recovered=8)
    
    state = temp_repo.get_recovery_state()
    assert state.get("recovery_needed") is False
    assert state.get("last_recovered_count") == 8
    assert state.get("last_recovery_at") is not None
