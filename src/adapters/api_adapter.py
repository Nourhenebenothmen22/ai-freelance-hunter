"""Public REST API Source Adapter (Remotive, Arbeitnow, etc.)."""

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from src.adapters.base import BaseSourceAdapter


class APIAdapter(BaseSourceAdapter):
    """Adapter for free public job board APIs."""

    async def search(self, queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch listings from public REST API."""
        async with self.get_client() as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
            data = resp.json()

        items: List[Dict[str, Any]] = []

        # Remotive & Jobicy response structure: {"jobs": [...]}
        if "jobs" in data and isinstance(data["jobs"], list):
            for job in data["jobs"]:
                title = job.get("jobTitle") or job.get("title")
                url = job.get("url")
                company = job.get("companyName") or job.get("company_name")
                desc = job.get("jobDescription") or job.get("description")
                location = job.get("jobGeo") or job.get("candidate_required_location")
                salary = str(job.get("annualSalaryMin") or job.get("salary") or "")
                pub_date = job.get("pubDate") or job.get("publication_date")
                job_type = str(job.get("jobType") or job.get("job_type") or "")
                category = job.get("jobCategory") or job.get("category")

                if title and url:
                    items.append({
                        "title": title,
                        "url": url,
                        "company": company,
                        "description": desc,
                        "location": location,
                        "salary": salary if salary else None,
                        "pub_date": pub_date,
                        "category": category,
                        "job_type": job_type,
                    })


        # Arbeitnow response structure: {"data": [...]}
        elif "data" in data and isinstance(data["data"], list):
            for job in data["data"]:
                items.append({
                    "title": job.get("title"),
                    "url": job.get("url"),
                    "company": job.get("company_name"),
                    "description": job.get("description"),
                    "location": job.get("location"),
                    "remote": job.get("remote", False),
                    "pub_date": job.get("created_at"),
                    "job_types": job.get("job_types", []),
                })

        # List of job dicts (e.g. RemoteOK API)
        elif isinstance(data, list):
            for job in data:
                if isinstance(job, dict) and (job.get("position") or job.get("title")):
                    items.append({
                        "title": job.get("position") or job.get("title"),
                        "url": job.get("url") or (f"https://remoteok.com/remote-jobs/{job.get('id')}" if job.get("id") else ""),
                        "company": job.get("company"),
                        "description": job.get("description"),
                        "location": job.get("location"),
                        "pub_date": str(job.get("date") or ""),
                    })

        return items

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize API payload."""
        desc = raw_item.get("description", "")
        # Strip HTML tags from description if present
        if desc and "<" in desc and ">" in desc:
            desc = BeautifulSoup(desc, "html.parser").get_text(separator=" ", strip=True)

        job_type = str(raw_item.get("job_type") or raw_item.get("job_types") or "")
        is_freelance = any(k in job_type.lower() for k in ["freelance", "contract", "contractor"])

        return {
            "title": raw_item.get("title", ""),
            "description": desc,
            "source": self.source_id,
            "source_url": raw_item.get("url", ""),
            "canonical_url": raw_item.get("url", ""),
            "company": raw_item.get("company"),
            "location": raw_item.get("location"),
            "remote": True,
            "freelance": is_freelance,
            "salary": raw_item.get("salary"),
            "publication_date": str(raw_item.get("pub_date") or ""),
        }
