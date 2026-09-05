"""Deterministic and Lightweight Language Detector.

Zero external dependencies. High-performance linguistic analysis tailored for
job postings and tech opportunity descriptions.
Detects:
- 'en' (English)
- 'fr' (French)
- 'ar' (Arabic)
- 'de' (German)
- 'es' (Spanish)
- 'it' (Italian)
- 'other'
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class LanguageDetector:
    """Fast, accurate language detector using stopwords and orthographic markers."""

    # Distinctive stopwords per language (lowercased)
    STOPWORDS_EN: Set[str] = {
        "the", "and", "of", "to", "in", "is", "you", "that", "it", "he", "was",
        "for", "on", "are", "as", "with", "his", "they", "at", "be", "this",
        "have", "from", "or", "one", "had", "by", "word", "but", "not", "what",
        "all", "were", "we", "when", "your", "can", "said", "there", "use", "an",
        "each", "which", "she", "do", "how", "their", "if", "will", "up", "other",
        "about", "out", "many", "then", "them", "these", "so", "some", "her",
        "would", "make", "like", "him", "into", "time", "has", "look", "two",
        "more", "write", "go", "see", "number", "no", "way", "could", "people",
        "my", "than", "first", "been", "call", "who", "its", "now", "find",
        "down", "day", "did", "get", "come", "made", "may", "part", "looking",
        "responsibilities", "requirements", "candidate", "candidates", "building",
        "join", "skills", "experience", "working", "team", "role", "company",
        "benefits", "opportunity", "stack", "full-time", "contract", "freelance"
    }

    STOPWORDS_FR: Set[str] = {
        "le", "la", "les", "de", "des", "du", "un", "une", "et", "à", "en",
        "pour", "dans", "qui", "que", "par", "sur", "avec", "sont", "est",
        "ce", "cette", "ces", "plus", "pas", "nous", "vous", "ils", "elles",
        "son", "sa", "ses", "comme", "mais", "ou", "si", "leur", "leurs",
        "tout", "tous", "toute", "toutes", "être", "avoir", "fait", "faire",
        "été", "stage", "développeur", "développeuse", "ingénieur", "ingénieure",
        "projet", "entreprise", "compétences", "expérience", "recherche", "équipe",
        "profil", "mission", "télétravail", "salaire", "contrat", "cdi", "cdd",
        "freelance", "alternance", "poste", "niveau", "formation", "travail",
        "postuler", "rejoignez", "notre", "vos", "nos", "candidatures", "atouts",
        "maîtrise", "auprès", "ainsi", "également", "afin", "chez", "dans"
    }

    STOPWORDS_DE: Set[str] = {
        "der", "die", "das", "und", "in", "zu", "den", "nicht", "von", "sie",
        "ist", "des", "sich", "mit", "dem", "dass", "er", "es", "ein", "ich",
        "auf", "so", "eine", "auch", "als", "an", "nach", "wie", "im", "für",
        "man", "aber", "aus", "durch", "wenn", "nur", "war", "noch", "werden",
        "wird", "bei", "oder", "wir", "unter", "um", "während", "diese",
        "diesem", "dieser", "dieses", "festanstellung", "standort", "vollzeit",
        "teilzeit", "bewerbung", "aufgaben", "anforderungen", "kenntnisse",
        "erfahrung", "entwickler", "suchen", "unternehmen", "gehalt", "bereich",
        "unsere", "unserem", "deine", "deinen", "bieten", "ab", "sofort"
    }

    STOPWORDS_ES: Set[str] = {
        "el", "la", "los", "las", "de", "del", "un", "una", "unos", "unas",
        "y", "e", "en", "a", "para", "por", "con", "no", "es", "son", "su",
        "sus", "se", "que", "qué", "como", "cómo", "más", "pero", "o", "u",
        "sobre", "este", "esta", "estos", "estas", "trabajo", "empresa",
        "experiencia", "puesto", "desarrollador", "desarrolladora", "equipo",
        "requisitos", "funciones", "remoto", "salario", "buscamos", "nuestro",
        "nuestra", "vacante", "candidato", "candidata", "ofrecemos"
    }

    STOPWORDS_IT: Set[str] = {
        "il", "lo", "la", "i", "gli", "le", "di", "da", "in", "con", "su",
        "per", "tra", "fra", "un", "uno", "una", "e", "ed", "o", "non", "che",
        "chi", "cui", "quale", "questo", "quello", "sono", "siamo", "hanno",
        "lavoro", "azienda", "sviluppo", "sviluppatore", "esperienza", "requisiti"
    }

    STOPWORDS_AR: Set[str] = {
        "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "تلك", "كان",
        "كانت", "يكون", "أن", "إن", "التي", "الذي", "الذين", "أو", "ثم", "حيث",
        "كل", "ما", "لا", "لم", "لن", "قد", "تم", "بين", "حول", "خلال", "عند",
        "حتى", "غير", "كما", "هو", "هي", "هم", "نحن", "أنا", "أنت", "مطلوب",
        "مشروع", "مبرمج", "مطور", "تطبيق", "موقع", "خدمة", "برمجة", "تصميم",
        "عمل", "أحتاج", "شركة", "وظيفة", "خبرة", "مهارات", "فريق", "صفحة",
        "نظام", "بيانات", "منصة", "بناء", "تطوير", "تقنية", "إدارة", "عن", "بعد",
        "حر", "مستقل", "مبتدئ", "متدرب", "دوام", "عقد", "ساعة", "ساعات", "إنجاز"
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Tokenize text into lowercased alpha words."""
        if not text:
            return []
        return re.findall(r"\b[^\W\d_]{2,}\b", text.lower(), re.UNICODE)

    @classmethod
    def detect_language(cls, title: str, description: Optional[str] = None) -> str:
        """
        Detect primary language of the opportunity text.
        Returns: 'en', 'fr', 'ar', 'de', 'es', 'it', or 'other'.
        """
        combined_text = f"{title or ''} {description or ''}".strip()
        if not combined_text:
            return "en"

        tokens = cls.tokenize(combined_text)
        if not tokens:
            if any('\u0600' <= c <= '\u06FF' for c in combined_text):
                return "ar"
            return "en"

        # Count stopwords match
        score_en = sum(1 for t in tokens if t in cls.STOPWORDS_EN)
        score_fr = sum(1 for t in tokens if t in cls.STOPWORDS_FR)
        score_ar = sum(1 for t in tokens if t in cls.STOPWORDS_AR)
        score_de = sum(1 for t in tokens if t in cls.STOPWORDS_DE)
        score_es = sum(1 for t in tokens if t in cls.STOPWORDS_ES)
        score_it = sum(1 for t in tokens if t in cls.STOPWORDS_IT)

        # Diacritics / orthographic indicators
        lower_raw = combined_text.lower()
        if any(c in lower_raw for c in "éèêëàâçîïôûœ"):
            score_fr += 5
        if any(c in lower_raw for c in "äöüß"):
            score_de += 6
        if any(c in lower_raw for c in "ñ¿¡"):
            score_es += 6

        # Arabic script detection (Unicode range \u0600 - \u06FF)
        ar_char_count = sum(1 for c in combined_text if '\u0600' <= c <= '\u06FF')
        if ar_char_count >= 5:
            score_ar += 5
        if ar_char_count >= 20:
            score_ar += 10

        scores = {
            "en": score_en,
            "fr": score_fr,
            "ar": score_ar,
            "de": score_de,
            "es": score_es,
            "it": score_it
        }

        best_lang, max_score = max(scores.items(), key=lambda item: item[1])

        # If zero or extremely sparse stopwords detected (e.g. 1-2 words total like "Fullstack React Developer")
        if max_score == 0:
            if any('\u0600' <= c <= '\u06FF' for c in title):
                return "ar"
            title_lower = title.lower()
            if any(w in title_lower for w in ["développeur", "ingénieur", "stage", "données", "concepteur"]):
                return "fr"
            if any(w in title_lower for w in ["entwickler", "informatiker", "berater"]):
                return "de"
            if any(w in title_lower for w in ["desarrollador", "ingeniero", "programador"]):
                return "es"
            # Default tech posts with English titles to English
            return "en"

        return best_lang

    @classmethod
    def is_allowed(cls, lang: str, allowed_languages: List[str]) -> bool:
        """Check if detected language is in the allowed languages list."""
        if not allowed_languages:
            return True
        normalized_allowed = [a.lower().strip() for a in allowed_languages if a.strip()]
        return lang.lower().strip() in normalized_allowed
