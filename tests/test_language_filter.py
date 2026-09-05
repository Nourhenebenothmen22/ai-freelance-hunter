"""Unit Tests for Language Detection and French/English Filtering."""

import pytest
from src.classifier.language_detector import LanguageDetector
from src.classifier.engine import ClassificationEngine
from src.config_loader import config


def test_english_language_detection():
    """Verify English job descriptions are correctly detected."""
    title = "Junior Full Stack Developer (React & Node.js)"
    desc = (
        "We are looking for a Junior Full Stack Developer to join our growing remote team. "
        "You will build modern web applications using React, TypeScript, and Node.js. "
        "The ideal candidate has strong problem-solving skills and experience with REST APIs."
    )
    lang = LanguageDetector.detect_language(title, desc)
    assert lang == "en"
    assert LanguageDetector.is_allowed(lang, ["en", "fr"]) is True


def test_french_language_detection():
    """Verify French job descriptions are correctly detected."""
    title = "Développeur Web Junior - Full Stack React / Node.js"
    desc = (
        "Nous recherchons un développeur web junior passionné pour rejoindre notre équipe. "
        "Vous participerez à la conception et au développement de nos applications avec React et Express. "
        "Profil recherché : formation en informatique, maîtrise de JavaScript, télétravail possible."
    )
    lang = LanguageDetector.detect_language(title, desc)
    assert lang == "fr"
    assert LanguageDetector.is_allowed(lang, ["en", "fr"]) is True


def test_german_language_detection_and_rejection():
    """Verify German job listings (e.g. from Arbeitnow) are detected and flagged as not allowed."""
    title = "Junior Frontend Entwickler (m/w/d)"
    desc = (
        "Für unseren Standort in Berlin suchen wir ab sofort einen motivierten Junior Webentwickler. "
        "Deine Aufgaben umfassen die Entwicklung moderner Benutzeroberflächen mit React und TypeScript. "
        "Wir bieten flexible Arbeitszeiten, Festanstellung und ein tolles Team."
    )
    lang = LanguageDetector.detect_language(title, desc)
    assert lang == "de"
    assert LanguageDetector.is_allowed(lang, ["en", "fr"]) is False


def test_spanish_language_detection_and_rejection():
    """Verify Spanish job descriptions are detected and rejected."""
    title = "Desarrollador Full Stack Junior Remoto"
    desc = (
        "Buscamos un desarrollador full stack con ganas de aprender y crecer en nuestro equipo. "
        "Requisitos: conocimientos en React, Node.js y bases de datos SQL. Trabajo 100% remoto."
    )
    lang = LanguageDetector.detect_language(title, desc)
    assert lang == "es"
    assert LanguageDetector.is_allowed(lang, ["en", "fr"]) is False


def test_classification_engine_disqualifies_german_job():
    """Verify ClassificationEngine sets score to 0 and status to disqualified for non-en/fr jobs."""
    engine = ClassificationEngine()
    german_raw = {
        "title": "Junior Python Entwickler (m/w/d)",
        "description": "Wir suchen einen Entwickler für Datenverarbeitung mit Python und SQL. Standort Berlin, Vollzeit.",
        "company": "TechGmbH",
        "source": "arbeitnow",
        "source_url": "https://example.com/german-job",
        "remote": True
    }
    opp = engine.process_raw_opportunity(german_raw)
    assert opp.language == "de"
    assert opp.score == 0
    assert opp.status == "disqualified"


def test_classification_engine_accepts_french_job():
    """Verify ClassificationEngine scores and accepts French junior jobs."""
    engine = ClassificationEngine()
    french_raw = {
        "title": "Stage Développeur Full Stack React / Node",
        "description": "Offre de stage / junior pour jeune diplômé en informatique. Télétravail, développement web.",
        "company": "StartupTN",
        "source": "facebook_group",
        "source_url": "https://example.com/french-job",
        "remote": True,
        "freelance": True
    }
    opp = engine.process_raw_opportunity(french_raw)
    assert opp.language == "fr"
    assert opp.score >= 60
    assert opp.status == "scored"


def test_arabic_language_detection():
    """Verify Arabic opportunity descriptions are correctly detected."""
    title = "مطلوب مبرمج رياكت وبايثون لبناء منصة ويب"
    desc = "مشروع عمل حر لتطوير تطبيق ويب متكامل بالاعتماد على بايثون وقواعد البيانات. العمل عن بعد ومتاح للمبتدئين."
    lang = LanguageDetector.detect_language(title, desc)
    assert lang == "ar"
    assert LanguageDetector.is_allowed(lang, ["en", "fr", "ar"]) is True
    assert LanguageDetector.is_allowed(lang, ["en", "fr"]) is False


def test_classification_engine_accepts_arabic_tech_job():
    """Verify ClassificationEngine scores and accepts Arabic tech opportunities when 'ar' is allowed."""
    engine = ClassificationEngine()
    arabic_raw = {
        "title": "مطلوب مبرمج رياكت وبايثون عن بعد",
        "description": "نبحث عن مبرمج فريلانس مبتدئ أو حديث التخرج للعمل عن بعد على تطوير واجهة React و Backend Python.",
        "company": "منصة خمسات",
        "source": "khamsat_requests",
        "source_url": "https://khamsat.com/community/requests/123456",
        "remote": True,
        "freelance": True
    }
    opp = engine.process_raw_opportunity(arabic_raw)
    assert opp.language == "ar"
    assert opp.score >= 75
    assert opp.status == "scored"
    assert opp.junior_signal is True
    assert opp.remote is True
    assert opp.freelance is True


def test_classification_engine_disqualifies_arabic_non_tech_job():
    """Verify ClassificationEngine disqualifies non-tech Arabic posts (e.g. content writing, video editing)."""
    engine = ClassificationEngine()
    non_tech_raw = {
        "title": "مطلوب كاتب محتوى ومونتير فيديو إعلاني احترافي",
        "description": "أحتاج مونتير فيديو محترف وتصميم إعلانات سوشيال ميديا وكتابة مقالات تسويقية.",
        "company": "متجر إلكتروني",
        "source": "khamsat_requests",
        "source_url": "https://khamsat.com/community/requests/99999",
        "remote": True,
        "freelance": True
    }
    opp = engine.process_raw_opportunity(non_tech_raw)
    assert opp.language == "ar"
    assert opp.score == 0
    assert opp.status == "disqualified"

