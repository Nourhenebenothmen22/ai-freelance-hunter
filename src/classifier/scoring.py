"""Configurable Opportunity Scoring Engine.

Loads exact weights from config/scoring.yaml and normalizes to 0-100.
90-100 = Excellent
75-89  = Strong
60-74  = Relevant
<60    = Ignore
"""

from typing import Any, Dict, List, Tuple
from src.config_loader import config


class Scorer:
    """Calculates relevance score based on detected features."""

    def __init__(self, scoring_cfg: Dict[str, Any] = None):
        cfg = scoring_cfg or config.scoring
        self.bonuses = cfg.get("bonuses", {
            "ai": 25,
            "web": 20,
            "web_and_ai_hybrid": 20,
            "python_data": 20,
            "sql_plsql": 15,
            "junior": 20,
            "remote": 15,
            "freelance": 15,
            "strong_skill_overlap": 15,
            "startup_sme": 10,
        })
        self.penalties = cfg.get("penalties", {
            "senior_only": -30,
            "expert_only": -35,
            "onsite_only": -30,
            "unrelated": -50,
            "r_only_data": -50,
        })
        self.thresholds = cfg.get("thresholds", {
            "excellent_min": 90,
            "strong_min": 75,
            "relevant_min": 60,
            "ignore_below": 60,
        })

    def calculate_score(
        self,
        web_signal: bool,
        ai_signal: bool,
        hybrid_signal: bool,
        python_signal: bool,
        data_signal: bool,
        sql_signal: bool,
        plsql_signal: bool,
        junior_signal: bool,
        remote: bool,
        freelance: bool,
        skills_count: int,
        startup_sme: bool,
        is_senior_only: bool,
        is_expert_only: bool,
        is_onsite_only: bool,
        is_unrelated: bool,
        is_r_disqualified: bool,
        realtime_freshness: bool = False,
        is_expired: bool = False,
        is_language_disqualified: bool = False,
        is_invalid_url: bool = False
    ) -> Tuple[int, str, List[str]]:
        """
        Calculate normalized score (0-100), category, and score breakdown.
        """
        raw_score = 0
        breakdown = []

        # Target Domain Bonuses
        if ai_signal:
            pts = self.bonuses.get("ai", 25)
            raw_score += pts
            breakdown.append(f"AI (+{pts})")

        if web_signal:
            pts = self.bonuses.get("web", 20)
            raw_score += pts
            breakdown.append(f"Web (+{pts})")

        if hybrid_signal:
            pts = self.bonuses.get("web_and_ai_hybrid", 20)
            raw_score += pts
            breakdown.append(f"Hybrid Web+AI (+{pts})")

        if python_signal and data_signal:
            pts = self.bonuses.get("python_data", 20)
            raw_score += pts
            breakdown.append(f"Python Data (+{pts})")

        if sql_signal or plsql_signal:
            pts = self.bonuses.get("sql_plsql", 15)
            raw_score += pts
            breakdown.append(f"SQL/PLSQL (+{pts})")

        # Junior Bonus
        if junior_signal:
            pts = self.bonuses.get("junior", 20)
            raw_score += pts
            breakdown.append(f"Junior-friendly (+{pts})")

        # Remote Bonus
        if remote:
            pts = self.bonuses.get("remote", 15)
            raw_score += pts
            breakdown.append(f"Remote (+{pts})")

        # Freelance Bonus
        if freelance:
            pts = self.bonuses.get("freelance", 15)
            raw_score += pts
            breakdown.append(f"Freelance (+{pts})")

        # Skill overlap
        if skills_count >= 3:
            pts = self.bonuses.get("strong_skill_overlap", 15)
            raw_score += pts
            breakdown.append(f"Strong skill overlap (+{pts})")

        # Startup/SME
        if startup_sme:
            pts = self.bonuses.get("startup_sme", 10)
            raw_score += pts
            breakdown.append(f"Startup/SME (+{pts})")

        # Real-time Freshness Bonus (< 2h / brand new post)
        if realtime_freshness:
            pts = self.bonuses.get("realtime_freshness", 15)
            raw_score += pts
            breakdown.append(f"Real-time Fresh (+{pts})")

        # Penalties
        if is_senior_only:
            pts = self.penalties.get("senior_only", -30)
            raw_score += pts
            breakdown.append(f"Senior only ({pts})")

        if is_expert_only:
            pts = self.penalties.get("expert_only", -35)
            raw_score += pts
            breakdown.append(f"Expert only ({pts})")

        if is_onsite_only:
            pts = self.penalties.get("onsite_only", -30)
            raw_score += pts
            breakdown.append(f"Onsite only ({pts})")

        if is_unrelated:
            pts = self.penalties.get("unrelated", -50)
            raw_score += pts
            breakdown.append(f"Unrelated ({pts})")

        if is_r_disqualified:
            pts = self.penalties.get("r_only_data", -50)
            raw_score += pts
            breakdown.append(f"Disqualified: R-required / R-only data role ({pts})")

        if is_expired:
            raw_score -= 60
            breakdown.append("Expired / Outdated post (-60)")

        # Disqualifications
        if is_language_disqualified:
            raw_score = 0
            breakdown.append("Disqualified: Language not permitted (French/English only)")

        if is_invalid_url:
            raw_score = 0
            breakdown.append("Disqualified: Invalid or dead URL")

        # Clamp score between 0 and 100
        final_score = max(0, min(100, raw_score))

        # Disqualified (Language, Dead URL, Unrelated, R-only/required) cannot be recommended or alerted
        if is_language_disqualified or is_invalid_url or is_unrelated or is_r_disqualified:
            final_score = 0
        elif is_senior_only or is_expert_only or is_expired:
            final_score = min(final_score, self.thresholds.get("ignore_below", 60) - 1)



        # Categorize
        if final_score >= self.thresholds.get("excellent_min", 90):
            category = "Excellent"
        elif final_score >= self.thresholds.get("strong_min", 75):
            category = "Strong"
        elif final_score >= self.thresholds.get("relevant_min", 60):
            category = "Relevant"
        else:
            category = "Ignore"

        return final_score, category, breakdown

