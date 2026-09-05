"""Normalized Opportunity Data Model."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class NormalizedOpportunity(BaseModel):
    """
    Exact normalized opportunity schema matching specification.
    Missing information = None (serialized to null).
    Never invent information.
    """
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    description: Optional[str] = None
    source: str
    source_url: str
    canonical_url: Optional[str] = None
    client: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    remote_scope: Optional[str] = None
    contract_type: Optional[str] = None
    freelance: bool = False
    salary: Optional[str] = None
    budget: Optional[str] = None
    currency: Optional[str] = None
    publication_date: Optional[str] = None
    deadline: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    role: Optional[str] = None
    experience_level: Optional[str] = None
    junior_signal: bool = False
    web_signal: bool = False
    ai_signal: bool = False
    python_signal: bool = False
    data_signal: bool = False
    sql_signal: bool = False
    plsql_signal: bool = False
    hybrid_signal: bool = False
    language: Optional[str] = None
    is_valid_url: bool = True
    is_fresh: bool = True
    is_realtime: bool = False
    age_hours: Optional[float] = None
    relative_time: Optional[str] = None
    first_seen_at: str
    last_seen_at: str
    score: int = 0
    status: str = "discovered"  # discovered, classified, scored, queued, notified, archived
    fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON/JSONL serialization."""
        return self.model_dump()
