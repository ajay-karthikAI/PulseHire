import os
import httpx
import asyncio
from typing import List, Dict, Any


class JobSearcher:
    SERPER_JOBS_URL = "https://google.serper.dev/jobs"
    SERPER_SEARCH_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.serper_key = os.getenv("SERPER_API_KEY", "")

    async def search(self, prefs) -> List[Dict]:
        jobs: List[Dict] = []
        queries = self._build_job_queries(prefs)
        ats_queries = self._build_ats_queries(prefs)

        async with httpx.AsyncClient(timeout=30) as client:
            # Google Jobs via Serper
            tasks = [self._serper_jobs(client, q, prefs) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    jobs.extend(r)

            # ATS board search (Greenhouse, Lever) via regular search
            ats_tasks = [self._serper_search(client, q) for q in ats_queries]
            ats_results = await asyncio.gather(*ats_tasks, return_exceptions=True)
            for r in ats_results:
                if isinstance(r, list):
                    jobs.extend(r)

        return self._deduplicate(jobs)

    def _build_job_queries(self, prefs) -> List[str]:
        loc = prefs.location or "United States"
        remote_prefix = "remote " if prefs.remote_preference == "remote" else ""

        return [
            f"{remote_prefix}AI machine learning engineer healthcare startup LLM agentic {loc}",
            f"{remote_prefix}data scientist AI healthcare startup {loc}",
            f"{remote_prefix}AI architect health tech startup LLM {loc}",
            f"{remote_prefix}LLM engineer generative AI healthcare startup {loc}",
            f"{remote_prefix}machine learning healthcare series A seed startup {loc}",
            f"{remote_prefix}AI specialist clinical NLP healthcare startup {loc}",
        ]

    def _build_ats_queries(self, prefs) -> List[str]:
        loc = prefs.location or "United States"
        return [
            f'site:boards.greenhouse.io (AI OR "machine learning" OR LLM) healthcare {loc}',
            f'site:jobs.lever.co (AI OR "machine learning" OR LLM) healthcare {loc}',
            f'site:wellfound.com/jobs ("machine learning" OR "data scientist" OR LLM) healthcare',
        ]

    async def _serper_jobs(self, client: httpx.AsyncClient, query: str, prefs) -> List[Dict]:
        try:
            resp = await client.post(
                self.SERPER_JOBS_URL,
                headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                json={"q": query, "location": prefs.location, "gl": "us", "hl": "en", "num": 20},
            )
            resp.raise_for_status()
            return self._parse_jobs_response(resp.json())
        except Exception as e:
            print(f"[scraper] serper_jobs error ({query[:40]}): {e}")
            return []

    async def _serper_search(self, client: httpx.AsyncClient, query: str) -> List[Dict]:
        try:
            resp = await client.post(
                self.SERPER_SEARCH_URL,
                headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                json={"q": query, "gl": "us", "hl": "en", "num": 10},
            )
            resp.raise_for_status()
            return self._parse_search_response(resp.json())
        except Exception as e:
            print(f"[scraper] serper_search error: {e}")
            return []

    def _parse_jobs_response(self, data: Dict) -> List[Dict]:
        jobs = []
        for j in data.get("jobs", []):
            ext = j.get("detectedExtensions", {})
            # Flatten highlights into description supplement
            highlights = j.get("highlights", {})
            qualifications = " | ".join(highlights.get("Qualifications", []))
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("companyName", ""),
                "location": j.get("location", ""),
                "posted_date": ext.get("postedAt", "Recently"),
                "description": (j.get("description", "") + " " + qualifications).strip(),
                "url": j.get("applyLink") or j.get("link", ""),
                "employment_type": ext.get("scheduleType", ""),
                "remote": ext.get("workFromHome", False),
                "source": "google_jobs",
            })
        return jobs

    def _parse_search_response(self, data: Dict) -> List[Dict]:
        jobs = []
        for r in data.get("organic", []):
            jobs.append({
                "title": r.get("title", ""),
                "company": self._extract_company_from_title(r.get("title", "")),
                "location": "",
                "posted_date": r.get("date", "Recently"),
                "description": r.get("snippet", ""),
                "url": r.get("link", ""),
                "source": "ats_search",
            })
        return jobs

    def _extract_company_from_title(self, title: str) -> str:
        # "Senior ML Engineer at Acme Health" -> "Acme Health"
        for sep in [" at ", " - ", " | "]:
            if sep in title:
                parts = title.split(sep)
                if len(parts) >= 2:
                    return parts[-1].strip()
        return ""

    def _deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        seen: set = set()
        unique = []
        for j in jobs:
            key = j.get("url") or f"{j.get('title', '')}-{j.get('company', '')}"
            key = key.lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(j)
        return unique
