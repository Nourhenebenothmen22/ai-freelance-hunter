"""Tests for Opportunity Classification and Detection Engine."""

import pytest
from src.classifier.engine import ClassificationEngine
from src.classifier.rule_detector import RuleDetector
from src.classifier.tech_detector import TechDetector


@pytest.fixture
def classifier():
    return ClassificationEngine()


def test_web_classification(classifier):
    raw = {
        "title": "Junior React Developer",
        "description": "Looking for a frontend developer skilled in React, Next.js, TypeScript and Node.js.",
        "company": "TechCorp",
        "source": "test",
        "source_url": "https://example.com/job1",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.web_signal is True
    assert opp.junior_signal is True
    assert "React" in opp.skills
    assert "Next.js" in opp.skills
    assert opp.score >= 60


def test_ai_classification(classifier):
    raw = {
        "title": "Junior AI Engineer - LLM & RAG",
        "description": "Build intelligent chatbots and AI agents using LangChain, OpenAI, and vector databases.",
        "company": "AI Labs",
        "source": "test",
        "source_url": "https://example.com/job2",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.ai_signal is True
    assert opp.junior_signal is True
    assert "RAG" in opp.skills
    assert "LLM" in opp.skills
    assert opp.score >= 75


def test_hybrid_web_and_ai(classifier):
    raw = {
        "title": "Full Stack AI Developer (React + RAG)",
        "description": "Develop full stack AI SaaS applications using Next.js, Node.js, and OpenAI LLM agents.",
        "company": "NextGen AI",
        "source": "test",
        "source_url": "https://example.com/job3",
        "remote": True,
        "freelance": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.web_signal is True
    assert opp.ai_signal is True
    assert opp.hybrid_signal is True
    assert opp.freelance is True
    # Strong hybrid freelance remote should achieve top score
    assert opp.score >= 90


def test_python_data_classification(classifier):
    raw = {
        "title": "Junior Python Data Engineer",
        "description": "Building ETL data pipelines with Python, Pandas, Airflow and PostgreSQL.",
        "company": "DataHub",
        "source": "test",
        "source_url": "https://example.com/job4",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.python_signal is True
    assert opp.data_signal is True
    assert opp.junior_signal is True
    assert "Python" in opp.skills
    assert opp.score >= 60


def test_sql_and_plsql_classification(classifier):
    raw = {
        "title": "Junior PL/SQL & Oracle Developer",
        "description": "Design database schemas, write stored procedures in PL/SQL and SQL for Oracle DB.",
        "company": "BankCorp",
        "source": "test",
        "source_url": "https://example.com/job5",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.plsql_signal is True
    assert opp.sql_signal is True
    assert "PL/SQL" in opp.skills
    assert opp.score >= 60


def test_r_only_disqualification(classifier):
    """R Developer or R required must be rejected and heavily penalized."""
    raw = {
        "title": "R Developer / R Programmer",
        "description": "R required. Primary language is R programming for statistical modeling.",
        "company": "StatLab",
        "source": "test",
        "source_url": "https://example.com/job6"
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.score < 50  # Must be heavily penalized
    tech = TechDetector.analyze_tech_stack(raw["title"], raw["description"])
    assert tech["is_r_disqualified"] is True


def test_python_with_optional_r_accepted(classifier):
    """Python required with R as a plus must NOT be disqualified and should be accepted."""
    raw = {
        "title": "Junior Python Data Analyst",
        "description": "Python required for data processing with SQL and Pandas. Experience with R is a plus / nice to have.",
        "company": "AnalyticsCorp",
        "source": "test",
        "source_url": "https://example.com/job7",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    tech = TechDetector.analyze_tech_stack(raw["title"], raw["description"])
    assert tech["r_optional"] is True
    assert tech["is_r_disqualified"] is False
    assert opp.python_signal is True
    assert opp.score >= 65


def test_senior_only_penalty(classifier):
    """Positions targeting only senior/principal/lead must be penalized."""
    raw = {
        "title": "Lead Software Architect (10+ years)",
        "description": "Staff engineer with 10+ years experience required. Senior only.",
        "company": "Enterprise Inc",
        "source": "test",
        "source_url": "https://example.com/job8"
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.experience_level in ["Senior / Lead", "Expert"]
    is_senior, is_expert = RuleDetector.detect_senior_only(raw["title"], raw["description"])
    assert is_senior or is_expert
    # Should get severe penalty
    assert opp.score < 50


def test_freelance_and_remote_signals(classifier):
    raw = {
        "title": "Freelance React Developer (Short Term Project)",
        "description": "Contract work, fixed price gig. Work from anywhere worldwide remote.",
        "company": "Startup Studio",
        "source": "test",
        "source_url": "https://example.com/job9"
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.freelance is True
    assert opp.remote is True
    assert opp.remote_scope == "worldwide"
    assert opp.score >= 60


def test_plsql_engineer_detection(classifier):
    """Verify detection of PL/SQL Engineer with Oracle and stored procedures."""
    raw = {
        "title": "Junior PL/SQL Engineer",
        "description": "Looking for entry-level engineer to write PL/SQL packages, stored procedures, and triggers on Oracle Database.",
        "company": "Telecom TN",
        "source": "test",
        "source_url": "https://example.com/job10",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.role == "PL/SQL Engineer"
    assert opp.plsql_signal is True
    assert opp.sql_signal is True
    assert opp.junior_signal is True
    assert "PL/SQL" in opp.skills
    assert "Oracle" in opp.skills
    assert opp.score >= 65


def test_sql_developer_remote_freelance(classifier):
    """Verify SQL developer freelance remote gig detection."""
    raw = {
        "title": "Junior SQL Developer (Freelance Remote)",
        "description": "Contract mission: database query optimization, complex SQL queries, views, and data integrity checks.",
        "company": "DataCorp",
        "source": "test",
        "source_url": "https://example.com/job11",
        "remote": True,
        "freelance": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.role == "SQL Developer"
    assert opp.sql_signal is True
    assert opp.freelance is True
    assert opp.remote is True
    assert opp.score >= 70


def test_data_engineer_sql_and_python(classifier):
    """Verify Data Engineer requiring both Python and SQL."""
    raw = {
        "title": "Junior Data Engineer (Python & SQL)",
        "description": "Build ETL data pipelines using Python, Pandas, Airflow, and PostgreSQL with advanced SQL queries.",
        "company": "DataScale",
        "source": "test",
        "source_url": "https://example.com/job12",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.role == "Python Data Engineer"
    assert opp.python_signal is True
    assert opp.data_signal is True
    assert opp.sql_signal is True
    assert opp.score >= 75


def test_data_analyst_python_only(classifier):
    """Verify Data Analyst using pure Python without R."""
    raw = {
        "title": "Junior Data Analyst - Python",
        "description": "Analyze datasets and create visualizations using Python, Pandas, and NumPy. Remote friendly.",
        "company": "Insights Corp",
        "source": "test",
        "source_url": "https://example.com/job13",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.role == "Python Data Analyst"
    assert opp.python_signal is True
    assert opp.data_signal is True
    assert opp.score >= 65
    assert opp.status == "scored"


def test_r_data_analyst_strictly_disqualified(classifier):
    """Strict Rule: R is strictly prohibited. Data Analyst with R and no Python must be disqualified to 0."""
    raw = {
        "title": "Junior Data Analyst - R",
        "description": "Perform statistical modeling using R language. R required. Statistical analysis with R packages.",
        "company": "BioStat",
        "source": "test",
        "source_url": "https://example.com/job14",
        "remote": True
    }
    opp = classifier.process_raw_opportunity(raw)
    assert opp.score == 0
    assert opp.status == "disqualified"

