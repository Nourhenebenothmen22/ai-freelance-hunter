"""Classification Engine.

Executes the 10-step classification and scoring pipeline:
1. Normalize text
2. Detect role
3. Detect required technologies
4. Detect optional technologies
5. Detect junior signals
6. Detect freelance signals
7. Detect remote signals
8. Detect domain
9. Detect geographic restrictions
10. Calculate relevance
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from src.classifier.date_parser import DateParser
from src.classifier.language_detector import LanguageDetector
from src.classifier.rule_detector import RuleDetector
from src.classifier.scoring import Scorer
from src.classifier.tech_detector import TechDetector
from src.config_loader import config
from src.models import NormalizedOpportunity
from src.storage.deduplicator import Deduplicator
from src.utils.url_validator import URLValidator


class ClassificationEngine:
    """Deterministic opportunity classifier and scorer."""

    def __init__(self, scorer: Optional[Scorer] = None):
        self.scorer = scorer or Scorer()

    def process_raw_opportunity(self, raw: Dict[str, Any]) -> NormalizedOpportunity:
        """
        Transform raw scraped opportunity into fully classified NormalizedOpportunity.
        Missing info = None. Never invent information.
        """
        title = (raw.get("title") or "").strip()
        description = (raw.get("description") or "").strip()
        company = (raw.get("company") or "").strip() or None
        source = raw.get("source") or "unknown"
        source_url = (raw.get("source_url") or "").strip()
        canonical_url = (raw.get("canonical_url") or "").strip() or None
        location = (raw.get("location") or "").strip() or None

        # Validate URL syntax and strip tracking noise
        is_valid_url, cleaned_source_url = URLValidator.clean_and_validate_syntax(source_url)
        if is_valid_url:
            source_url = cleaned_source_url

        if canonical_url:
            _, cleaned_canonical = URLValidator.clean_and_validate_syntax(canonical_url)
            if cleaned_canonical:
                canonical_url = cleaned_canonical
        else:
            canonical_url = source_url if is_valid_url else None

        # Step 1: Normalize text for analysis
        norm_title = Deduplicator.normalize_text(title)
        norm_desc = Deduplicator.normalize_text(description)

        # Step 2: Detect role
        detected_role = RuleDetector.detect_role(title)

        # Step 3 & 4: Detect required & optional technologies & R restrictions
        tech_analysis = TechDetector.analyze_tech_stack(title, description)
        skills = tech_analysis["skills"]

        # Step 5: Detect junior signals & senior penalties
        is_junior = RuleDetector.detect_junior(title, description)
        is_senior_only, is_expert_only = RuleDetector.detect_senior_only(title, description)

        # Experience level string
        if is_junior:
            experience_level = "Junior / Entry Level"
        elif is_senior_only:
            experience_level = "Senior / Lead"
        elif is_expert_only:
            experience_level = "Expert"
        else:
            experience_level = raw.get("experience_level") or "Junior Friendly / Mid"

        # Step 6: Detect freelance signals
        is_freelance = RuleDetector.detect_freelance(title, description) or bool(raw.get("freelance"))
        contract_type = "Freelance / Contract" if is_freelance else (raw.get("contract_type") or "Full-Time / Contract")

        # Step 7: Detect remote signals
        is_remote, remote_scope = RuleDetector.detect_remote(title, description, location)
        if raw.get("remote"):
            is_remote = True
        if raw.get("remote_scope"):
            remote_scope = raw.get("remote_scope")

        is_onsite_only = (not is_remote) and bool(location and "remote" not in location.lower())

        # Step 8: Detect domain signals
        web_signal = tech_analysis["web_signal"]
        ai_signal = tech_analysis["ai_signal"]
        python_signal = tech_analysis["python_signal"]
        data_signal = tech_analysis["data_signal"]
        sql_signal = tech_analysis["sql_signal"]
        plsql_signal = tech_analysis["plsql_signal"]
        hybrid_signal = tech_analysis["hybrid_signal"]

        # Detect unrelated jobs (e.g. Sales, Accounting, HR, or non-tech match)
        is_non_tech = RuleDetector.is_non_tech_role(title)
        has_any_tech = any([web_signal, ai_signal, python_signal, data_signal, sql_signal, plsql_signal])
        is_unrelated = is_non_tech or (not has_any_tech and len(skills) == 0)

        # Detect startup/SME
        is_startup_sme = RuleDetector.detect_startup_sme(title, description, company)

        # Step 9: Detect geographic restrictions
        geo_restrictions = RuleDetector.detect_geographic_restrictions(title, description)
        if geo_restrictions and remote_scope == "worldwide":
            remote_scope = f"remote ({', '.join(geo_restrictions)})"

        # Language detection and filtering
        detected_language = LanguageDetector.detect_language(title, description)
        is_lang_allowed = LanguageDetector.is_allowed(detected_language, config.allowed_languages)
        is_language_disqualified = (not is_lang_allowed) and config.reject_other_languages

        # URL validity check
        is_invalid_url = (not is_valid_url) and config.reject_invalid_urls

        # Step 10: Evaluate publication date & real-time freshness
        max_age_hours = config.freshness_max_age_hours
        reject_expired = config.freshness_reject_expired
        realtime_window_hours = config.freshness_realtime_window_hours

        raw_pub_date = raw.get("publication_date") or raw.get("pub_date")
        freshness = DateParser.evaluate_freshness(
            raw_pub_date,
            max_age_hours=max_age_hours,
            realtime_window_hours=realtime_window_hours
        )

        is_realtime = freshness["is_realtime"]
        is_expired = freshness["is_expired"] and reject_expired
        is_fresh = freshness["is_fresh"]
        age_hours = freshness["age_hours"]
        relative_time = freshness["relative_display"]
        publication_date = freshness["iso_string"]

        # Step 11: Calculate score
        score, category, breakdown = self.scorer.calculate_score(
            web_signal=web_signal,
            ai_signal=ai_signal,
            hybrid_signal=hybrid_signal,
            python_signal=python_signal,
            data_signal=data_signal,
            sql_signal=sql_signal,
            plsql_signal=plsql_signal,
            junior_signal=is_junior,
            remote=is_remote,
            freelance=is_freelance,
            skills_count=len(skills),
            startup_sme=is_startup_sme,
            is_senior_only=is_senior_only,
            is_expert_only=is_expert_only,
            is_onsite_only=is_onsite_only,
            is_unrelated=is_unrelated,
            is_r_disqualified=tech_analysis["is_r_disqualified"],
            realtime_freshness=is_realtime,
            is_expired=is_expired,
            is_language_disqualified=is_language_disqualified,
            is_invalid_url=is_invalid_url
        )

        # Generate robust fingerprint
        fingerprint = Deduplicator.compute_fingerprint(title, company, description)
        now_iso = datetime.now(timezone.utc).isoformat()
        opp_id = f"{source}_{fingerprint[:16]}"

        return NormalizedOpportunity(
            id=opp_id,
            title=title,
            description=description if description else None,
            source=source,
            source_url=source_url,
            canonical_url=canonical_url,
            client=raw.get("client"),
            company=company,
            location=location,
            remote=is_remote,
            remote_scope=remote_scope,
            contract_type=contract_type,
            freelance=is_freelance,
            salary=raw.get("salary"),
            budget=raw.get("budget"),
            currency=raw.get("currency"),
            publication_date=publication_date,
            deadline=raw.get("deadline"),
            skills=skills,
            role=detected_role,
            experience_level=experience_level,
            junior_signal=is_junior,
            web_signal=web_signal,
            ai_signal=ai_signal,
            python_signal=python_signal,
            data_signal=data_signal,
            sql_signal=sql_signal,
            plsql_signal=plsql_signal,
            hybrid_signal=hybrid_signal,
            language=detected_language,
            is_valid_url=is_valid_url,
            is_fresh=is_fresh,
            is_realtime=is_realtime,
            age_hours=age_hours,
            relative_time=relative_time,
            first_seen_at=now_iso,
            last_seen_at=now_iso,
            score=score,
            status="scored" if score > 0 else "disqualified",
            fingerprint=fingerprint
        )
