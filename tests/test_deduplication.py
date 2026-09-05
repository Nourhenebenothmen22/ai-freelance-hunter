"""Tests for Multi-Key Deduplication and Filesystem Atomic Locking."""

import tempfile
from pathlib import Path
import pytest
from src.storage.atomic_fs import AtomicFS
from src.storage.deduplicator import Deduplicator


@pytest.fixture
def temp_deduplicator(tmp_path):
    seen_urls_file = tmp_path / "seen_urls.json"
    fingerprints_file = tmp_path / "fingerprints.json"
    return Deduplicator(seen_urls_file=str(seen_urls_file), fingerprints_file=str(fingerprints_file))


def test_url_normalization():
    url1 = "https://example.com/jobs/123/?utm_source=twitter&utm_medium=social&ref=feed"
    url2 = "https://example.com/jobs/123"
    assert Deduplicator.normalize_url(url1) == Deduplicator.normalize_url(url2)


def test_duplicate_exact_url(temp_deduplicator):
    url = "https://example.com/job/dev-1"
    fingerprint = "fp_abc123"
    
    is_dup, _ = temp_deduplicator.is_duplicate(url, None, "React Dev", "Acme", fingerprint)
    assert is_dup is False

    temp_deduplicator.mark_seen(url, None, "React Dev", "Acme", fingerprint)
    temp_deduplicator.save()

    # Re-check same URL
    is_dup, reason = temp_deduplicator.is_duplicate(url, None, "React Dev", "Acme", fingerprint)
    assert is_dup is True
    assert "URL match" in reason


def test_duplicate_tracking_parameters(temp_deduplicator):
    url_base = "https://example.com/job/dev-2"
    url_with_utm = "https://example.com/job/dev-2?utm_campaign=winter&utm_source=newsletter"
    fingerprint = "fp_xyz987"

    temp_deduplicator.mark_seen(url_base, None, "Full Stack Dev", "Corp", fingerprint)
    
    is_dup, reason = temp_deduplicator.is_duplicate(url_with_utm, None, "Full Stack Dev", "Corp", "different_fp")
    assert is_dup is True
    assert "URL match" in reason


def test_cross_platform_duplicate_by_fingerprint_and_company(temp_deduplicator):
    """The same opportunity posted on Source A and Source B must be deduplicated."""
    title = "Junior AI Engineer (Remote)"
    company = "GenAI Inc"
    desc = "We are seeking a junior AI engineer with Python and RAG experience to build chatbots."
    
    fp = Deduplicator.compute_fingerprint(title, company, desc)
    
    # Seen on Source A
    temp_deduplicator.mark_seen(
        url="https://source-a.com/job/101",
        canonical_url=None,
        title=title,
        company=company,
        fingerprint=fp
    )

    # Arrives from Source B with different URL but same title, company, and content
    is_dup, reason = temp_deduplicator.is_duplicate(
        url="https://source-b.org/post/999",
        canonical_url=None,
        title="Junior AI Engineer Remote",  # slight variation in title
        company="GenAI Inc",
        fingerprint=fp
    )
    assert is_dup is True
    assert "fingerprint match" in reason or "Title/Company match" in reason


def test_atomic_filesystem_operations(tmp_path):
    test_file = tmp_path / "test_data.json"
    data = {"key": "value", "count": 42}
    
    AtomicFS.write_json(test_file, data)
    read_data = AtomicFS.read_json(test_file)
    assert read_data == data

    # Test atomic JSONL
    jsonl_file = tmp_path / "test.jsonl"
    AtomicFS.append_jsonl(jsonl_file, {"id": "1", "name": "item1"})
    AtomicFS.append_jsonl(jsonl_file, {"id": "2", "name": "item2"})

    lines = AtomicFS.read_jsonl(jsonl_file)
    assert len(lines) == 2
    assert lines[0]["id"] == "1"
    assert lines[1]["name"] == "item2"
