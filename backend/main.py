import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from scraper import JobSearcher
from classifier import JobClassifier

app = FastAPI(title="JobBot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchPreferences(BaseModel):
    location: str = "United States"
    seniority: List[str] = ["mid-level", "senior"]
    remote_preference: str = "any"

searcher = JobSearcher()
classifier = JobClassifier()

_cached_jobs: List[dict] = []


@app.post("/api/search")
async def search_jobs(prefs: SearchPreferences):
    global _cached_jobs

    if not os.getenv("SERPER_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Missing API keys. Add SERPER_API_KEY and ANTHROPIC_API_KEY to your .env file."
        )

    raw = await searcher.search(prefs)
    classified = await classifier.filter_and_classify(raw)
    _cached_jobs = classified
    return {"jobs": classified, "total": len(classified)}


@app.get("/api/jobs")
async def get_cached_jobs():
    return {"jobs": _cached_jobs, "total": len(_cached_jobs)}


@app.get("/api/status")
async def status():
    return {
        "serper_key": bool(os.getenv("SERPER_API_KEY")),
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
    }


frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(frontend_dir / "index.html"))


if __name__ == "__main__":
    print("JobBot starting at http://localhost:8000")
    missing = []
    if not os.getenv("SERPER_API_KEY"):
        missing.append("SERPER_API_KEY")
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print(f"WARNING: Missing env vars: {', '.join(missing)}")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
