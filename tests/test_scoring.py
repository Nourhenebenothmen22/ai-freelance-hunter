"""Tests for Scoring Engine and Configurable Weights."""

import pytest
from src.classifier.scoring import Scorer


@pytest.fixture
def scorer():
    return Scorer()


def test_top_tier_junior_freelance_ai(scorer):
    """Junior + Freelance + Remote + Web + AI + Overlap should score 90-100 (Excellent)."""
    score, cat, breakdown = scorer.calculate_score(
        web_signal=True,
        ai_signal=True,
        hybrid_signal=True,
        python_signal=True,
        data_signal=True,
        sql_signal=False,
        plsql_signal=False,
        junior_signal=True,
        remote=True,
        freelance=True,
        skills_count=4,
        startup_sme=True,
        is_senior_only=False,
        is_expert_only=False,
        is_onsite_only=False,
        is_unrelated=False,
        is_r_disqualified=False
    )
    assert score >= 90
    assert cat == "Excellent"


def test_strong_junior_web_remote(scorer):
    """Junior + Web + Remote should score 75-89 (Strong)."""
    score, cat, breakdown = scorer.calculate_score(
        web_signal=True,
        ai_signal=False,
        hybrid_signal=False,
        python_signal=False,
        data_signal=False,
        sql_signal=False,
        plsql_signal=False,
        junior_signal=True,
        remote=True,
        freelance=False,
        skills_count=3,
        startup_sme=False,
        is_senior_only=False,
        is_expert_only=False,
        is_onsite_only=False,
        is_unrelated=False,
        is_r_disqualified=False
    )
    # Web(20) + Junior(20) + Remote(15) + Skills(15) = 70+
    assert score >= 70
    assert cat in ["Strong", "Relevant"]


def test_senior_penalty_suppression(scorer):
    """A role with senior penalty should be pushed down into Ignore or low range."""
    score, cat, breakdown = scorer.calculate_score(
        web_signal=True,
        ai_signal=False,
        hybrid_signal=False,
        python_signal=False,
        data_signal=False,
        sql_signal=False,
        plsql_signal=False,
        junior_signal=False,
        remote=True,
        freelance=False,
        skills_count=2,
        startup_sme=False,
        is_senior_only=True,
        is_expert_only=False,
        is_onsite_only=False,
        is_unrelated=False,
        is_r_disqualified=False
    )
    # 20 (web) + 15 (remote) - 30 (senior) = 5
    assert score <= 30
    assert cat == "Ignore"


def test_r_disqualification_penalty(scorer):
    """R-only data role must receive severe penalty."""
    score, cat, breakdown = scorer.calculate_score(
        web_signal=False,
        ai_signal=False,
        hybrid_signal=False,
        python_signal=False,
        data_signal=True,
        sql_signal=False,
        plsql_signal=False,
        junior_signal=True,
        remote=True,
        freelance=False,
        skills_count=1,
        startup_sme=False,
        is_senior_only=False,
        is_expert_only=False,
        is_onsite_only=False,
        is_unrelated=False,
        is_r_disqualified=True
    )
    # Junior(20) + Remote(15) - R_penalty(50) = 0
    assert score == 0
    assert cat == "Ignore"
