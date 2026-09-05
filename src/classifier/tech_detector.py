"""Technology and Skill Detector with Required vs Optional R Logic.

Rules:
- Python is primary data language.
- Reject when R is required/primary ('R Developer', 'R required', 'R programming required').
- Accept when Python is required and R is optional/nice-to-have ('Python required, R is a plus').
"""

import re
from typing import Any, Dict, List, Set, Tuple


class TechDetector:
    """Extracts technologies and verifies required vs optional requirements."""

    TECH_PATTERNS = {
        # Web
        "React": [r"\breact(?:\.js|js)?\b", r"ريأكت", r"رياكت"],
        "Next.js": [r"\bnext(?:\.js|js)?\b", r"نكست"],
        "Node.js": [r"\bnode(?:\.js|js)?\b", r"نود"],
        "Express": [r"\bexpress(?:\.js|js)?\b"],
        "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
        "TypeScript": [r"\btypescript\b", r"\bts\b"],
        "MERN": [r"\bmern\b"],
        "MongoDB": [r"\bmongodb\b", r"\bmongo\b"],
        "REST API": [r"\brest(?:\s+api|ful)?\b"],
        "SaaS": [r"\bsaas\b"],
        "GraphQL": [r"\bgraphql\b"],
        "TailwindCSS": [r"\btailwind(?:css)?\b"],

        # AI
        "RAG": [r"\brag\b", r"\bretrieval[\s-]augmented\b"],
        "LLM": [r"\bllm(?:s)?\b", r"\blarge\s+language\s+models?\b"],
        "LangChain": [r"\blangchain\b"],
        "LlamaIndex": [r"\bllamaindex\b", r"\bllama-index\b"],
        "OpenAI": [r"\bopenai\b", r"\bgpt[- ]?[34o]\b"],
        "Hugging Face": [r"\bhugging\s*face\b"],
        "AI Agent": [r"\bai\s+agents?\b", r"\bautonomous\s+agents?\b", r"وكيل\s+ذكاء\s+اصطناعي", r"وكلاء\s+الذكاء\s+الاصطناعي"],
        "Chatbot": [r"\bchatbot(?:s)?\b", r"\bconversational\s+ai\b", r"شات\s*بوت", r"روبوت\s+محادثة"],
        "Vector DB": [r"\b(?:chromadb|pinecone|qdrant|weaviate|milvus|pgvector)\b"],
        "Generative AI": [r"\bgenerative\s+ai\b", r"\bgenai\b", r"ذكاء\s+اصطناعي\s+توليدي"],
        "Machine Learning": [r"\bmachine\s+learning\b", r"\bml\b", r"تعلم\s+الآلة", r"تعلم\s+آلي"],
        "NLP": [r"\bnlp\b", r"\bnatural\s+language\s+processing\b", r"معالجة\s+اللغات\s+الطبيعية"],

        # Data / Python
        "Python": [r"\bpython(?:3)?\b", r"بايثون"],
        "Pandas": [r"\bpandas\b"],
        "NumPy": [r"\bnumpy\b"],
        "PySpark": [r"\bpyspark\b", r"\bapache\s+spark\b"],
        "Airflow": [r"\bairflow\b"],
        "FastAPI": [r"\bfastapi\b"],
        "Flask": [r"\bflask\b"],
        "ETL": [r"\betl\b", r"\bdata\s+pipelines?\b", r"\bdata\s+engineering\b", r"\bdata\s+analyst\b", r"مهندس\s+بيانات", r"محلل\s+بيانات"],

        # SQL / Database
        "SQL": [r"\bsql\b", r"\bt-sql\b", r"\btransact-sql\b", r"قواعد\s+بيانات", r"قاعدة\s+بيانات"],
        "PL/SQL": [r"\bpl[\s/]?sql\b", r"\bpl-sql\b", r"\boracle\s+pl[\s/]?sql\b", r"بي\s*إل\s*إس\s*كيو\s*إل"],
        "Oracle": [r"\boracle(?:\s+database|\s+db)?\b", r"\boracle\s+sql\b", r"أوراكل"],
        "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
        "MySQL": [r"\bmysql\b"],
        "Stored Procedures": [r"\bstored\s+procedures?\b", r"\btriggers?\b", r"\bprocedures?\s+stockées?\b", r"إجراءات\s+مخزنة"],
    }

    R_PRIMARY_PATTERNS = [
        r"\bR\s+developer\b",
        r"\bR\s+programmer\b",
        r"\bR\s+data\s+engineer\b",
        r"\bR\s+data\s+analyst\b",
        r"\bdata\s+analyst\s+[-–(]?\s*R\b",
        r"\banalyste\s+R\b",
        r"\bR\s+required\b",
        r"\brequires?\s+R\b",
        r"\bexpert\s+in\s+R\b",
        r"\bproficien(?:cy|t)\s+in\s+R\b",
        r"\bprimary\s+language[:\s]+R\b",
        r"\bmust\s+have[:\s]+.*?\bR\b",
        r"\bR\s+programming\s+required\b",
        r"\bstrong\s+knowledge\s+of\s+R\b",
    ]

    R_OPTIONAL_PATTERNS = [
        r"\bR\s+(?:is\s+)?(?:a\s+)?(?:plus|bonus|nice\s+to\s+have|preferred|optional)\b",
        r"(?:plus|bonus|nice\s+to\s+have|preferred|optional)[:\s]+[^\n.]*?\bR\b",
        r"python.*?(?:or|and)\s+r\s+(?:is\s+)?(?:a\s+)?(?:plus|bonus|preferred)",
        r"python\s+(?:required|mandatory).*?r.*?(?:plus|preferred|bonus|optional)",
    ]

    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """Extract matched technologies from title + description."""
        found: Set[str] = set()
        for skill_name, patterns in cls.TECH_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    found.add(skill_name)
                    break
        return sorted(list(found))

    @classmethod
    def evaluate_r_status(cls, title: str, description: str, text: str) -> Tuple[bool, bool, bool]:
        """
        Determine if R is required, optional, or disqualifying.
        Returns: (has_r_mention, r_is_required, r_is_optional)
        """
        # First check title: If job title has 'R Developer' / 'R Programmer' / 'R Data ...', it's always primary
        for pat in [
            r"\bR\s+Developer\b", r"\bR\s+Programmer\b", r"\bR\s+Data\s+Engineer\b",
            r"\bR\s+Data\s+Analyst\b", r"\bData\s+Analyst\s+[-–(]?\s*R\b", r"\bAnalyste\s+R\b"
        ]:
            if re.search(pat, title, re.IGNORECASE):
                return True, True, False

        # Check if R is explicitly mentioned as optional / nice to have
        is_optional = False
        for pat in cls.R_OPTIONAL_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                is_optional = True
                break

        # Check if R is required/primary
        is_required = False
        for pat in cls.R_PRIMARY_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                # If it matched an optional pattern, don't flag as required unless title explicitly specifies
                if not is_optional:
                    is_required = True
                    break

        has_r_mention = is_required or is_optional
        return has_r_mention, is_required, is_optional

    @classmethod
    def analyze_tech_stack(cls, title: str, description: str) -> Dict[str, Any]:
        """Comprehensive analysis of tech stack and signals."""
        full_text = f"{title} {description}"
        skills = cls.extract_skills(full_text)
        skills_set = set(skills)

        # Signals
        web_skills = {"React", "Next.js", "Node.js", "Express", "JavaScript", "TypeScript", "MERN", "MongoDB", "REST API", "SaaS", "GraphQL", "TailwindCSS"}
        ai_skills = {"RAG", "LLM", "LangChain", "LlamaIndex", "OpenAI", "Hugging Face", "AI Agent", "Chatbot", "Vector DB", "Generative AI", "Machine Learning", "NLP"}
        python_skills = {"Python", "Pandas", "NumPy", "PySpark", "Airflow", "FastAPI", "Flask", "ETL"}
        sql_skills = {"SQL", "Stored Procedures", "PostgreSQL", "MySQL"}
        plsql_skills = {"PL/SQL", "Oracle"}

        web_signal = bool(skills_set.intersection(web_skills))
        ai_signal = bool(skills_set.intersection(ai_skills))
        python_signal = bool(skills_set.intersection(python_skills))
        sql_signal = bool(skills_set.intersection(sql_skills))
        plsql_signal = bool(skills_set.intersection(plsql_skills))
        data_signal = python_signal or bool(re.search(r"\b(?:data\s+analyst|data\s+engineer|etl|pipeline)\b", full_text, re.I))

        # Hybrid Web + AI: Strong priority
        hybrid_signal = (web_signal and ai_signal) or bool(
            re.search(r"\b(?:full\s*stack\s*\+\s*ai|react\s*\+\s*ai|next\.?js\s*\+\s*ai|ai[\s-]powered\s+saas|rag\s+web)\b", full_text, re.I)
        )

        # R language evaluation
        has_r, r_required, r_optional = cls.evaluate_r_status(title, description, full_text)

        # Disqualification: R is primary/required and not merely an optional plus alongside Python,
        # or it is a data role where R is present without Python.
        is_r_disqualified = (r_required and not r_optional) or (has_r and not python_signal and data_signal)

        return {
            "skills": skills,
            "web_signal": web_signal,
            "ai_signal": ai_signal,
            "python_signal": python_signal,
            "data_signal": data_signal,
            "sql_signal": sql_signal,
            "plsql_signal": plsql_signal,
            "hybrid_signal": hybrid_signal,
            "has_r": has_r,
            "r_required": r_required,
            "r_optional": r_optional,
            "is_r_disqualified": is_r_disqualified,
        }

