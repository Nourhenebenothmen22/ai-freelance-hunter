# AI-Freelance-Hunter: Architecture & Implementation Status Plan

## 1. System Overview

**AI-Freelance-Hunter** is an autonomous opportunity hunting system designed to maximize real, accessible opportunities for a junior / beginner / final-year engineering student in Tunisia and worldwide remote markets.

The system is orchestrated following the **OpenClaw** workflow pattern, operates in **Docker** with automatic restart, relies entirely on **free and open-source tools**, and uses **zero database engines** (pure atomic filesystem persistence with file locking).

---

## 2. Implemented Architecture

### A. Centralized Configuration (`config/`)
All domain boundaries, role titles, technology synonyms, query generators, scoring weights, notification formats, and schedules are strictly externalized in YAML files:
- `profile.yaml`: Target candidate qualifications, target markets, languages (EN/FR).
- `roles.yaml`: Standardized role definitions for Web Development, AI / Intelligent Systems, Hybrid Web+AI, Python Data, and SQL / PL/SQL.
- `technologies.yaml`: Tech stack mappings, primary vs optional designations, and strict R rejection rules (`disallowed_primary_patterns` vs `optional_r_patterns`).
- `search_queries.yaml`: Dynamic query templates generating bilingual queries without combinatorial explosion.
- `sources.yaml`: Source definitions (RemoteOK, WeWorkRemotely, Jobspresso, Remotive, Arbeitnow, Hacker News) with adapter types and rate limits.
- `filters.yaml`: Regex patterns for junior positive signals, senior-only negative penalties, freelance signals, remote signals, and geographic restrictions.
- `scoring.yaml`: Scoring matrix (Bonuses: AI +25, Web +20, Hybrid +20, Python Data +20, SQL +15, Junior +20, Remote +15, Freelance +15; Penalties: Senior -30, Expert -35, Onsite -30, Unrelated -50, R-only -50; Thresholds: 90-100 Excellent, 75-89 Strong, 60-74 Relevant, <60 Ignore).
- `notifications.yaml`: Telegram HTML alert templates, score thresholds, retry delays, and batch limits.
- `schedules.yaml`: Crawl frequencies (30m), jitter (+/- 60s), and downtime window calculation limits (72h).
- `system.yaml`: File paths, network timeouts, backoff multipliers, and browser User-Agent headers.

### B. Filesystem Persistence & Deduplication (`src/storage/`)
- **Strictly No Database**: Uses `AtomicFS` with cross-platform file locking (`portalocker`) and atomic tempfile replacement with `fsync`.
- **Multi-Key Deduplication (`Deduplicator`)**:
  1. Normalized URL (strips tracking parameters: `utm_*`, `ref`, `source`, `fbclid`, `gclid`).
  2. Canonical URL matching.
  3. Normalized Title + Company composite key.
  4. Content Fingerprinting (SHA-256 token set hash and SimHash fallback).
- **Filesystem Layout**:
  - `data/opportunities.jsonl`: Append-only normalized opportunities.
  - `data/seen_urls.json`: Set of observed URLs and title-company pairs.
  - `data/fingerprints.json`: Mapping of content fingerprints.
  - `data/notifications.json`: State machine for pending, sent, and failed notifications.
  - `data/sources.json`: Dynamic source registry.
  - `data/crawl_state.json`: Active run metrics and historical crawls.
  - `data/recovery_state.json`: Heartbeat, shutdown, and downtime window tracking.
  - `data/source_health.json`: Per-source health and failure isolation logs.
  - `data/runs/`: Detailed JSON run reports per crawl cycle.

### C. Modular Source Adapters (`src/adapters/`)
- Pluggable interface: `SourceAdapter -> search() -> fetch_details() -> normalize() -> health_check()`.
- Resilient implementations:
  - `RSSAdapter`: High-efficiency XML parsing for open feeds.
  - `APIAdapter`: Zero-key JSON API consumption (Remotive, Arbeitnow).
  - `HTMLScraperAdapter`: Async HTTP + BeautifulSoup4/lxml scraper for structured web listings.
  - `FacebookGroupAdapter`: Public Facebook groups scraper with contact extraction (phone, WhatsApp, email) for Tunisian & remote freelance missions.
  - `SourceDiscoveryEngine`: Dynamic feed discoverer and validator.
- **Failure Isolation**: An error or timeout in one source is recorded in `source_health.json` and will never crash the hunting pipeline.

### D. Classification & Scoring Engine (`src/classifier/`)
- **10-Step Deterministic Pipeline**: Text normalization -> Role identification -> Tech stack extraction -> Required vs Optional evaluation -> Junior signal detection -> Freelance detection -> Remote detection -> Domain validation -> Geographic restrictions -> Relevance scoring.
- **R Language Rule**:
  - "R Developer", "R required", "primary language: R" -> `is_r_disqualified = True`, heavily penalized (-50) and dropped to "Ignore".
  - "Python required, R is a plus" -> `r_optional = True`, accepted with high priority.

### E. Offline & Restart Recovery (`src/recovery/`)
- Tracks heartbeats in `recovery_state.json`.
- On container or PC reboot, detects offline duration.
- Initiates prioritized crawl for missed window, deduplicates against stored fingerprints and seen URLs, and pushes unnotified high-value opportunities.
- Prevents duplicate alerts on restart.

### F. Real-Time Telegram Dispatcher (`src/notifier/`)
- Dispatches formatted alerts with emojis, score breakdown, tags, and apply links.
- If network fails or credentials are not yet set, notifications are safely enqueued in `data/notifications.json` and retried automatically.

### G. OpenClaw Orchestration & Docker (`src/orchestration/`, `src/main.py`)
- Standardized execution loop with graceful shutdown signal handling (`SIGINT`, `SIGTERM`).
- Dockerized deployment via `Dockerfile` and `docker-compose.yml` mounting `./config`, `./data`, `./logs`.

---

## 3. Implementation Status

| Component | Status | Verification Result |
|-----------|--------|---------------------|
| Centralized Config (`config/*.yaml`) | ✅ Completed | 10/10 YAML configuration files created |
| Data Model (`src/models.py`) | ✅ Completed | Exact 35-field schema matching Section 10 |
| Storage & Locking (`src/storage/`) | ✅ Completed | Atomic writes, file locks, JSON/JSONL |
| Deduplication Engine | ✅ Completed | Canonical URL, Normalized URL, Title+Company, Fingerprint |
| Classifier & R Rules | ✅ Completed | Web, AI, Hybrid, Python Data, SQL, R rejection |
| Scoring Engine | ✅ Completed | Normalized 0-100 with category thresholds |
| Source Adapters & Discovery | ✅ Completed | RSS, JSON API, HTML Scraper, Dynamic Discoverer |
| Failure Isolation | ✅ Completed | Isolated runs with per-source health tracking |
| Offline & Restart Recovery | ✅ Completed | Downtime calculation, missed-window recovery |
| Telegram Alerts & Queue | ✅ Completed | Zero-loss retry queue and formatted alerts |
| OpenClaw Orchestrator & CLI | ✅ Completed | `run`, `daemon`, `recover`, `test-sources`, `stats` |
| Docker & Compose | ✅ Completed | Volumes, healthcheck, `unless-stopped` restart |
| Test Suite (`tests/`) | ✅ Completed | 7 test modules covering all specifications |
