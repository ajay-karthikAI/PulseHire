import os
import json
import asyncio
from typing import List, Dict
import anthropic


class JobClassifier:
    BATCH_SIZE = 12

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def filter_and_classify(self, jobs: List[Dict]) -> List[Dict]:
        if not jobs:
            return []

        results: List[Dict] = []
        loop = asyncio.get_event_loop()

        for i in range(0, len(jobs), self.BATCH_SIZE):
            batch = jobs[i : i + self.BATCH_SIZE]
            classified = await loop.run_in_executor(None, self._classify_batch, batch)
            results.extend(classified)

        # Sort: most recent first (keep original order as proxy)
        return results

    def _classify_batch(self, jobs: List[Dict]) -> List[Dict]:
        payload = [
            {
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "location": j.get("location", ""),
                "posted_date": j.get("posted_date", ""),
                "description": (j.get("description", "") or "")[:600],
                "url": j.get("url", ""),
            }
            for j in jobs
        ]

        prompt = f"""You are a job board filter for AI roles at healthcare startups.

INCLUDE a job only if ALL three conditions are met:
1. AI/ML role — involves ML, LLMs, generative AI, agentic AI, NLP, deep learning, computer vision, AI engineering, or data science with ML
2. Healthcare domain — healthcare, health tech, clinical, pharma, biotech, medical, patient care, digital health
3. Startup / scale-up — NOT a large corporation (exclude Google, Amazon, AWS, Microsoft, Apple, Meta, IBM, Oracle, Salesforce, Epic, Cerner, UnitedHealth as a standalone division)

For each job that passes, extract:
- skills: 6–10 comma-separated keywords/technologies (e.g. "PyTorch, LLMs, RAG, FHIR, clinical NLP")
- requires_phd: true if job description says PhD is required
- phd_preferred: true if PhD is preferred/plus but not required
- company_stage: "seed", "series A", "series B", "series C", "growth", or "unknown"
- remote: true if role is remote or hybrid

Return a JSON array. Each element:
{{
  "company": "string",
  "title": "string",
  "location": "string",
  "posted_date": "string",
  "skills": "Python, PyTorch, LLMs",
  "url": "string",
  "requires_phd": false,
  "phd_preferred": false,
  "company_stage": "series A",
  "remote": false,
  "include": true
}}

Set include=false for jobs that fail any of the 3 criteria above.

Jobs to analyze:
{json.dumps(payload, indent=2)}

Return ONLY the JSON array. No explanation."""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-7",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Strip markdown fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

            classified = json.loads(text)
            return [j for j in classified if j.get("include", False)]

        except json.JSONDecodeError as e:
            print(f"[classifier] JSON parse error: {e}")
            return []
        except Exception as e:
            print(f"[classifier] Error: {e}")
            return []
