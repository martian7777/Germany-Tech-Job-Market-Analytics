"""FastAPI application entry point for DeTech Jobs Analytics."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import SessionLocal, init_db
from app.models import JobPosting
from app.routes import analytics, jobs, recommender
from app.scraper import ScraperConfig, run_scrape


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure schema exists; auto-seed on first run so the app works out of the box.
    init_db()
    session = SessionLocal()
    try:
        if session.query(JobPosting).count() == 0:
            from app.seed import seed

            seed()
    finally:
        session.close()
    yield


app = FastAPI(
    title="DeTech Jobs Analytics API",
    description="German tech job market analytics, skill-gap recommender and BI exports.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(analytics.router)
app.include_router(recommender.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "detech-jobs-analytics"}


@app.post("/api/scrape", tags=["scraper"])
def trigger_scrape(use_fixture: bool = True):
    """Run the BeautifulSoup scraper. Defaults to the offline demo fixture."""
    result = run_scrape(ScraperConfig(use_fixture=use_fixture))
    return {"ok": True, **result}
