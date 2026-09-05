"""Rule, Role, Junior, Freelance, and Remote Detector."""

import re
from typing import Any, Dict, List, Optional, Tuple


class RuleDetector:
    """Extracts role, junior level, work type, remote scope, and geographic restrictions."""

    JUNIOR_PATTERNS = [
        r"\bjunior\b",
        r"\bjr\.?\b",
        r"\bentry[\s-]level\b",
        r"\bbeginner\b",
        r"\bgraduate\b",
        r"\bstudent\b",
        r"\bintern(?:ship)?\b",
        r"\bstage\b",
        r"\bpfe\b",
        r"\b0[-–]1\s+years?\b",
        r"\b0[-–]2\s+years?\b",
        r"\b1[-–]2\s+years?\b",
        r"\bless\s+than\s+2\s+years?\b",
        r"\bno\s+experience\s+required\b",
        r"\bexperience\s+preferred\b",
        r"\bjunior[- ]friendly\b",
        r"\bearly[- ]career\b",
        r"\btraining\s+provided\b",
        r"\bdébutant\b",
    ]

    SENIOR_ONLY_PATTERNS = [
        r"\bsenior\b",
        r"\bsr\.?\b",
        r"\blead\b",
        r"\bprincipal\b",
        r"\bstaff\b",
        r"\bexpert\s+only\b",
        r"\b(?:8|9|10)\+?\s+years?\s+(?:of\s+)?experience\b",
        r"\barchitect\b",
        r"\bhead\s+of\b",
        r"\bdirector\b",
        r"\bvp\b",
    ]

    NON_TECH_ROLE_PATTERNS = [
        r"\baccount\s+executive\b",
        r"\bsales\b",
        r"\bmarketing\b",
        r"\bbusiness\s+development\b",
        r"\brecruiter\b",
        r"\btalent\s+acquisition\b",
        r"\bcustomer\s+success\b",
        r"\bhuman\s+resources\b",
        r"\bhr\s+manager\b",
        r"\baccountant\b",
        r"\baccounting\b",
        r"\bfinancial\s+analyst\b",
        r"\blegal\b",
        r"\bcopywriter\b",
        r"\bcommunity\s+manager\b",
        r"\bformer\s+founder\b",
        r"\barea\s+vice\s+president\b",
        r"\benablement\s+manager\b",
        r"\bchief\s+revenue\s+officer\b",
        r"\bcommercial\b",
    ]


    FREELANCE_TITLE_PATTERNS = [
        r"\bfreelance\b",
        r"\bcontract\b",
        r"\bcontractor\b",
        r"\bfixed[\s-]price\b",
        r"\bproject[\s-]based\b",
        r"\bgig\b",
        r"\bmission\b",
        r"\bconsultant\b",
        r"\bconsulting\b",
        r"\bshort[\s-]term\b",
        r"\bpart[\s-]time\b",
        r"\bprestation\b",
    ]

    FREELANCE_DESC_PATTERNS = [
        r"\bfreelance\b",
        r"\bindependent\s+contractor\b",
        r"\bfixed[\s-]price\b",
        r"\bproject[\s-]based\b",
        r"\bshort[\s-]term\s+(?:contract|project|mission)\b",
        r"\blong[\s-]term\s+contract\b",
        r"\bcontract\s+(?:work|role|position|basis|opportunity)\b",
        r"\bremote\s+freelance\b",
        r"\bpart[\s-]time\s+remote\b",
        r"\bprestation\b",
        r"\bb2b\s+contract\b",
    ]

    REMOTE_PATTERNS = [
        r"\bremote\b",
        r"\bfully\s+remote\b",
        r"\bremote\s+worldwide\b",
        r"\bwork\s+from\s+anywhere\b",
        r"\bdistributed\b",
        r"\btélétravail\b",
        r"\btelecommute\b",
        r"\banywhere\b",
    ]

    STARTUP_SME_PATTERNS = [
        r"\bstartup\b",
        r"\bearly[\s-]stage\b",
        r"\bseed\b",
        r"\bseries[\s-][ab]\b",
        r"\bsmall\s+company\b",
        r"\bsme\b",
        r"\bpme\b",
        r"\bsoftware\s+agency\b",
        r"\bdigital\s+agency\b",
        r"\bsmall\s+team\b",
        r"\bboutique\b",
    ]

    GEOGRAPHIC_RESTRICTIONS = {
        "us_only": [r"\bus\s+only\b", r"\bunited\s+states\s+only\b", r"\bmust\s+be\s+located\s+in\s+the\s+us\b", r"\bus\s+citizens?\s+only\b"],
        "eu_only": [r"\beu\s+only\b", r"\beurope\s+only\b", r"\bbased\s+in\s+europe\b"],
        "tunisia_only": [r"\btunisia\s+only\b", r"\bbasé\s+en\s+tunisie\b"],
        "timezone_restriction": [r"\b(?:est|pst|cst|cet|gmt)\s+time\s*zone\b", r"\btimezone\s+overlap\b"],
    }

    @classmethod
    def detect_role(cls, title: str) -> Optional[str]:
        """Detect standardized role name from title."""
        t_low = title.lower()
        if "full stack" in t_low or "fullstack" in t_low:
            return "Full Stack Developer"
        elif "react" in t_low:
            return "React Developer"
        elif "next" in t_low:
            return "Next.js Developer"
        elif "node" in t_low:
            return "Node.js Developer"
        elif "ai" in t_low or "artificial intelligence" in t_low or "machine learning" in t_low or "ml" in t_low:
            return "AI Engineer"
        elif "rag" in t_low or "llm" in t_low or "chatbot" in t_low:
            return "RAG / LLM Developer"
        elif "data engineer" in t_low or "etl" in t_low:
            return "Python Data Engineer"
        elif "data analyst" in t_low:
            return "Python Data Analyst"
        elif "pl/sql" in t_low or "plsql" in t_low or "pl-sql" in t_low:
            if "engineer" in t_low or "ingénieur" in t_low:
                return "PL/SQL Engineer"
            return "PL/SQL Developer"
        elif "oracle" in t_low:
            if "engineer" in t_low or "ingénieur" in t_low:
                return "Oracle Engineer"
            return "PL/SQL Developer"
        elif "sql" in t_low:
            if "engineer" in t_low or "ingénieur" in t_low:
                return "SQL Engineer"
            return "SQL Developer"
        elif "database" in t_low:
            if "engineer" in t_low or "ingénieur" in t_low:
                return "Database Engineer"
            return "Database Developer"

        elif "frontend" in t_low or "front-end" in t_low:
            return "Frontend Developer"
        elif "backend" in t_low or "back-end" in t_low:
            return "Backend Developer"
        elif "web" in t_low:
            return "Web Developer"
        return "Software Developer"

    @classmethod
    def detect_junior(cls, title: str, description: str) -> bool:
        """Detect strong positive junior / entry-level signals."""
        full_text = f"{title} {description}"
        for pat in cls.JUNIOR_PATTERNS:
            if re.search(pat, full_text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def detect_senior_only(cls, title: str, description: str) -> Tuple[bool, bool]:
        """
        Detect senior-only and expert-only signals.
        Returns: (is_senior_only, is_expert_only)
        """
        full_text = f"{title} {description}"
        is_senior = False
        is_expert = False

        if re.search(r"\bexpert\s+only\b", full_text, re.I) or re.search(r"\b10\+\s+years\b", full_text, re.I):
            is_expert = True

        # If title explicitly has junior/intern/student signals, do NOT flag as senior
        has_junior_title = bool(re.search(r"\b(?:junior|entry|intern|stage|student|débutant)\b", title, re.I))
        if not has_junior_title:
            for pat in cls.SENIOR_ONLY_PATTERNS:
                if re.search(pat, title, re.IGNORECASE):
                    is_senior = True
                    break

            if not is_senior:
                if re.search(r"\bsenior\s+only\b", full_text, re.I) or re.search(r"\b(?:7|8|9|10)\+?\s+years\b", full_text, re.I):
                    is_senior = True

        return is_senior, is_expert

    @classmethod
    def detect_freelance(cls, title: str, description: str) -> bool:
        """Detect freelance, contract, or gig work signals."""
        for pat in cls.FREELANCE_TITLE_PATTERNS:
            if re.search(pat, title, re.IGNORECASE):
                return True
        for pat in cls.FREELANCE_DESC_PATTERNS:
            if re.search(pat, description, re.IGNORECASE):
                return True
        return False

    @classmethod
    def detect_remote(cls, title: str, description: str, location: Optional[str]) -> Tuple[bool, str]:
        """
        Detect remote availability and remote scope.
        Returns: (is_remote, remote_scope)
        """
        loc_str = location or ""
        combined = f"{title} {description} {loc_str}"

        is_remote = False
        remote_scope = "unspecified"

        if re.search(r"\b(?:worldwide|anywhere|global)\b", combined, re.I):
            is_remote = True
            remote_scope = "worldwide"
        elif re.search(r"\b(?:europe|eu|emea)\b", combined, re.I):
            is_remote = True
            remote_scope = "europe"
        elif re.search(r"\b(?:tunisia|tunisie)\b", combined, re.I):
            is_remote = True
            remote_scope = "tunisia"
        elif re.search(r"\b(?:us|united states|north america)\b", combined, re.I):
            is_remote = True
            remote_scope = "us_only"
        else:
            for pat in cls.REMOTE_PATTERNS:
                if re.search(pat, combined, re.IGNORECASE):
                    is_remote = True
                    remote_scope = "remote"
                    break

        return is_remote, remote_scope

    @classmethod
    def detect_geographic_restrictions(cls, title: str, description: str) -> List[str]:
        """Extract stored geographic restrictions rather than blindly rejecting."""
        full_text = f"{title} {description}"
        restrictions = []
        for r_name, patterns in cls.GEOGRAPHIC_RESTRICTIONS.items():
            for pat in patterns:
                if re.search(pat, full_text, re.IGNORECASE):
                    restrictions.append(r_name)
                    break
        return restrictions

    @classmethod
    def detect_startup_sme(cls, title: str, description: str, company: Optional[str]) -> bool:
        """Detect startup, SME/PME, or small engineering team."""
        combined = f"{title} {company or ''} {description}"
        for pat in cls.STARTUP_SME_PATTERNS:
            if re.search(pat, combined, re.IGNORECASE):
                return True
        return False

    @classmethod
    def is_non_tech_role(cls, title: str) -> bool:
        """Check if title represents a non-engineering/non-developer job (e.g. Sales, Marketing, HR)."""
        if not title:
            return False
        patterns = cls.NON_TECH_ROLE_PATTERNS
        try:
            from src.config_loader import config
            configured = config.non_tech_patterns
            if configured:
                patterns = configured
        except Exception:
            pass

        for pat in patterns:
            if re.search(pat, title, re.IGNORECASE):
                return True
        return False


